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


def _strip_batch_only_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    excluded = {
        "seedStart",
        "seedEnd",
        "seedStep",
        "chartSeedStart",
        "chartSeedEnd",
        "chartSeedStep",
        "rareThreshold",
        "completionStep",
    }
    return {key: value for key, value in payload.items() if key not in excluded}


def _seed_range_from_payload(payload: Mapping[str, Any], default_seed: int) -> list[int]:
    seed_start = int(payload.get("seedStart", payload.get("chartSeedStart", default_seed)))
    seed_end = int(payload.get("seedEnd", payload.get("chartSeedEnd", default_seed + 9)))
    seed_step = max(1, int(payload.get("seedStep", payload.get("chartSeedStep", 1))))
    if seed_end < seed_start:
        seed_start, seed_end = seed_end, seed_start

    seeds = list(range(seed_start, seed_end + 1, seed_step))
    if len(seeds) > 50:
        raise ValueError("seed range is limited to 50 runs per chart")
    return seeds


def _safe_small_world_degree(config: SimulationConfig) -> int:
    degree = min(max(2, config.neighbors_per_peer), config.peer_count - 1)
    if degree % 2 != 0:
        degree -= 1
    return max(2, degree)


def _topology_payload(base_payload: Mapping[str, Any], topology_mode: str, config: SimulationConfig) -> dict[str, Any]:
    payload = {**base_payload, "topologyMode": topology_mode}
    if topology_mode == "smallWorld":
        payload["neighborsPerPeer"] = _safe_small_world_degree(config)
    elif topology_mode == "randomK":
        payload["neighborsPerPeer"] = min(max(1, config.neighbors_per_peer), config.peer_count - 1)
    return payload


def _system_completion_percent(snapshot: Mapping[str, Any], total_chunks: int, peer_count: int) -> float:
    owned_count = sum(len(peer.get("ownedChunks", [])) for peer in snapshot.get("peers", []))
    return round((owned_count / max(total_chunks * peer_count, 1)) * 100, 6)


def _rare_chunk_count(snapshot: Mapping[str, Any], total_chunks: int, threshold: int) -> int:
    availability = {chunk_id: 0 for chunk_id in range(total_chunks)}
    for peer in snapshot.get("peers", []):
        if not peer.get("online", True):
            continue
        for chunk_id in peer.get("ownedChunks", []):
            chunk_id = int(chunk_id)
            if chunk_id in availability:
                availability[chunk_id] += 1
    return sum(1 for count in availability.values() if count <= threshold)


def _rare_chunk_series(result: Mapping[str, Any], threshold: int, completion_step: int) -> list[dict[str, Any]]:
    config = result.get("config", {})
    total_chunks = int(config.get("totalChunks") or config.get("total_chunks") or 0)
    peer_count = int(config.get("peer_count") or config.get("peerCount") or 0)
    timeline = result.get("progressTimeline", [])
    if not total_chunks or not peer_count or not timeline:
        return []

    snapshots = [
        {
            "completion": _system_completion_percent(snapshot, total_chunks, peer_count),
            "rareChunks": _rare_chunk_count(snapshot, total_chunks, threshold),
            "time": snapshot.get("time", 0),
        }
        for snapshot in timeline
    ]

    points: list[dict[str, Any]] = []
    index = 0
    for target in range(0, 101, completion_step):
        while index + 1 < len(snapshots) and snapshots[index]["completion"] < target:
            index += 1
        snapshot = snapshots[index]
        points.append(
            {
                "completion": target,
                "actualCompletion": round(snapshot["completion"], 3),
                "rareChunks": snapshot["rareChunks"],
                "time": snapshot["time"],
            }
        )
    return points


def build_statistics_charts(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    base_payload = _strip_batch_only_payload(payload)
    config = SimulationConfig.from_payload(base_payload)
    seeds = _seed_range_from_payload(payload, config.seed)
    rare_threshold = max(0, int(payload.get("rareThreshold", 3)))
    completion_step = max(1, min(25, int(payload.get("completionStep", 5))))

    seed_series: list[dict[str, Any]] = []
    for seed in seeds:
        result = compare_strategies({**base_payload, "seed": seed})
        seed_series.append(
            {
                "seed": seed,
                "randomFirst": {
                    "time": result["randomFirst"]["totalTime"],
                    "completed": result["randomFirst"]["completed"],
                },
                "rarestFirst": {
                    "time": result["rarestFirst"]["totalTime"],
                    "completed": result["rarestFirst"]["completed"],
                },
                "winner": result["winner"],
            }
        )

    topology_modes = ["fullMesh", "randomK", "ring", "star", "smallWorld"]
    topology_labels = {
        "fullMesh": "Full mesh",
        "randomK": "Random k",
        "ring": "Ring",
        "star": "Hub",
        "smallWorld": "Small world",
    }
    topology_bars: list[dict[str, Any]] = []
    for topology_mode in topology_modes:
        result = compare_strategies(_topology_payload(base_payload, topology_mode, config))
        topology_bars.append(
            {
                "topology": topology_mode,
                "label": topology_labels[topology_mode],
                "randomFirst": {
                    "time": result["randomFirst"]["totalTime"],
                    "completed": result["randomFirst"]["completed"],
                },
                "rarestFirst": {
                    "time": result["rarestFirst"]["totalTime"],
                    "completed": result["rarestFirst"]["completed"],
                },
            }
        )

    distribution_modes = [
        ("balancedRandom", "Random peer"),
        ("singleSeeder", "Peer 0"),
    ]
    rare_series: list[dict[str, Any]] = []
    for distribution_mode, distribution_label in distribution_modes:
        result = compare_strategies({**base_payload, "initialDistributionMode": distribution_mode})
        for strategy_key in ("randomFirst", "rarestFirst"):
            rare_series.append(
                {
                    "strategy": strategy_key,
                    "distributionMode": distribution_mode,
                    "label": f"{result[strategy_key]['strategyName']} - {distribution_label}",
                    "points": _rare_chunk_series(result[strategy_key], rare_threshold, completion_step),
                }
            )

    return {
        "seedRange": {"start": seeds[0], "end": seeds[-1], "step": seeds[1] - seeds[0] if len(seeds) > 1 else 1},
        "rareThreshold": rare_threshold,
        "completionStep": completion_step,
        "config": config.to_dict(),
        "charts": {
            "seedComparison": seed_series,
            "topologyComparison": topology_bars,
            "rareChunkProgress": rare_series,
        },
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
