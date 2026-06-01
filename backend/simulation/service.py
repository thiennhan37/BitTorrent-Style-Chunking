from __future__ import annotations

from typing import Any, Mapping

from .config import SimulationConfig
from .initial_state import clone_initial_state, generate_initial_state
from .simulator import BitTorrentSimulator


def _custom_neighbor_graph_from_payload(payload: Mapping[str, Any]) -> Any | None:
    return (
        payload.get("topologyAdjacency")
        or payload.get("topology_adjacency")
        or payload.get("adjacencyList")
        or payload.get("adjacency")
        or payload.get("topologyEdges")
        or payload.get("neighborGraph")
        or payload.get("neighbor_graph")
    )


def run_single_simulation(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    strategy = payload.get("strategy", "randomFirst")
    config = SimulationConfig.from_payload(payload)
    initial_state = payload.get("initialState") or generate_initial_state(config)
    neighbor_graph = _custom_neighbor_graph_from_payload(payload)
    simulator = BitTorrentSimulator(
        config=config,
        strategy=strategy,
        initial_state=initial_state,
        churn_events=payload.get("churnEvents") or payload.get("churn_events") or [],
        neighbor_graph=neighbor_graph,
    )
    return simulator.run()


def compare_strategies(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    config = SimulationConfig.from_payload(payload)
    initial_state = clone_initial_state(payload.get("initialState") or generate_initial_state(config))
    churn_events = payload.get("churnEvents") or payload.get("churn_events") or []
    neighbor_graph = _custom_neighbor_graph_from_payload(payload)

    random_first = BitTorrentSimulator(
        config=config,
        strategy="randomFirst",
        initial_state=clone_initial_state(initial_state),
        churn_events=churn_events,
        neighbor_graph=neighbor_graph,
    ).run()
    rarest_first = BitTorrentSimulator(
        config=config,
        strategy="rarestFirst",
        initial_state=clone_initial_state(initial_state),
        churn_events=churn_events,
        neighbor_graph=neighbor_graph,
    ).run()

    if not random_first["completed"] and not rarest_first["completed"]:
        winner = "none"
    elif random_first["completed"] and not rarest_first["completed"]:
        winner = "randomFirst"
    elif rarest_first["completed"] and not random_first["completed"]:
        winner = "rarestFirst"
    elif random_first["totalTime"] < rarest_first["totalTime"]:
        winner = "randomFirst"
    elif rarest_first["totalTime"] < random_first["totalTime"]:
        winner = "rarestFirst"
    else:
        winner = "tie"

    difference = round(abs(random_first["totalTime"] - rarest_first["totalTime"]), 6)
    return {
        "randomFirst": random_first,
        "rarestFirst": rarest_first,
        "winner": winner,
        "difference": difference,
        "initialState": initial_state,
        "neighborGraph": random_first["neighborGraph"],
        "churnEvents": churn_events,
        "config": config.to_dict(),
    }


def _snapshot_at_or_before(timeline: list[dict[str, Any]], time_value: float) -> dict[str, Any] | None:
    snapshot = None
    for item in timeline:
        if float(item.get("time", 0.0)) <= time_value:
            snapshot = item
        else:
            break
    return snapshot or (timeline[0] if timeline else None)


def _availability_from_snapshot(snapshot: dict[str, Any] | None, total_chunks: int) -> dict[int, list[int]]:
    availability: dict[int, list[int]] = {chunk_id: [] for chunk_id in range(total_chunks)}
    if not snapshot:
        return availability

    for peer in snapshot.get("peers", []):
        if not peer.get("online", True):
            continue
        for chunk_id in peer.get("ownedChunks", []):
            availability[int(chunk_id)].append(int(peer["peerId"]))
    return availability


def recommend_churn_candidate(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    config = SimulationConfig.from_payload(payload)
    initial_state = clone_initial_state(payload.get("initialState") or generate_initial_state(config))
    churn_time = max(float(payload.get("time", payload.get("churnTime", 0.0))), 0.0)

    existing_events = payload.get("churnEvents") or payload.get("churn_events") or []
    baseline = compare_strategies({**payload, "initialState": initial_state, "churnEvents": existing_events})
    random_snapshot = _snapshot_at_or_before(baseline["randomFirst"]["progressTimeline"], churn_time)
    rarest_snapshot = _snapshot_at_or_before(baseline["rarestFirst"]["progressTimeline"], churn_time)
    random_availability = _availability_from_snapshot(random_snapshot, config.total_chunks)
    rarest_availability = _availability_from_snapshot(rarest_snapshot, config.total_chunks)
    random_online_at_time = {int(peer["peerId"]) for peer in (random_snapshot or {}).get("peers", []) if peer.get("online", True)}
    rarest_online_at_time = {int(peer["peerId"]) for peer in (rarest_snapshot or {}).get("peers", []) if peer.get("online", True)}

    trials: list[dict[str, Any]] = []
    for peer_id in range(config.peer_count):
        # Peer da offline o timeline hien tai thi khong phai candidate "drop" hop le.
        if peer_id not in random_online_at_time and peer_id not in rarest_online_at_time:
            continue
        event = {"time": churn_time, "peerId": peer_id, "online": False}
        result = compare_strategies({**payload, "initialState": initial_state, "churnEvents": [*existing_events, event]})
        random_result = result["randomFirst"]
        rarest_result = result["rarestFirst"]
        rare_chunks = [
            chunk_id
            for chunk_id, owners in random_availability.items()
            if owners == [peer_id] and len(rarest_availability.get(chunk_id, [])) > 1
        ]
        random_missing = [
            chunk_id
            for chunk_id, count in random_result.get("chunkAvailability", {}).items()
            if int(count) == 0
        ]
        desired = not random_result["completed"] and rarest_result["completed"]
        trials.append(
            {
                "peerId": peer_id,
                "event": event,
                "desired": desired,
                "rareChunks": rare_chunks,
                "randomCompleted": random_result["completed"],
                "rarestCompleted": rarest_result["completed"],
                "randomTotalTime": random_result["totalTime"],
                "rarestTotalTime": rarest_result["totalTime"],
                "randomMissingChunks": [int(chunk_id) for chunk_id in random_missing],
                "score": (
                    1000 if desired else 0,
                    len(rare_chunks),
                    1 if rarest_result["completed"] else 0,
                    -random_result["totalTransfers"],
                ),
            }
        )

    recommendation = max(trials, key=lambda item: item["score"], default=None)
    if recommendation:
        recommendation = {key: value for key, value in recommendation.items() if key != "score"}
        if recommendation["desired"]:
            recommendation["message"] = (
                f"Turn off Peer {recommendation['peerId']} at t={round(churn_time, 3)}s: "
                "Random-First cannot finish, while Rarest-First still completes."
            )
        else:
            recommendation["message"] = (
                f"Peer {recommendation['peerId']} is the strongest churn candidate at t={round(churn_time, 3)}s, "
                "but this seed/time does not produce the full Random-fails/Rarest-completes contrast."
            )

    public_trials = [{key: value for key, value in trial.items() if key != "score"} for trial in trials]
    return {
        "time": round(churn_time, 6),
        "recommendation": recommendation,
        "trials": public_trials,
        "initialState": initial_state,
        "config": config.to_dict(),
    }
