from __future__ import annotations
# import sys
# from pathlib import Path

# BACKEND_ROOT = Path(__file__).resolve().parents[1]
# if str(BACKEND_ROOT) not in sys.path:
#     sys.path.insert(0, str(BACKEND_ROOT))

from simulation.config import SimulationConfig
from simulation.initial_state import generate_initial_state
from simulation.service import build_statistics_charts, compare_strategies, recommend_churn_candidate
from simulation.simulator import BitTorrentSimulator
from simulation.strategies import RandomFirstStrategy, RarestFirstStrategy
import random




def test_default_config_has_40_chunks():
    config = SimulationConfig()
    assert config.file_size_mb == 10
    assert config.chunk_size_kb == 256
    assert config.total_chunks == 40
    assert config.peer_count == 10
    assert config.seed == 1
    assert config.bandwidth_kbps == 128
    assert config.effective_upload_bandwidth_kbps == 128
    assert config.initial_chunk_probability == 0.3


def test_initial_state_is_complete_swarm_but_not_complete_peers():
    config = SimulationConfig(seed=7)
    state = generate_initial_state(config)
    all_chunks = set().union(*(set(chunks) for chunks in state))
    assert len(state) == 10
    assert all_chunks == set(range(40))
    assert all(len(chunks) > 0 for chunks in state)


def test_single_seeder_initial_state_puts_full_file_on_peer_zero():
    config = SimulationConfig(file_size_mb=1, chunk_size_kb=256, peer_count=4, initial_distribution_mode="singleSeeder")
    state = generate_initial_state(config)

    assert set(state[0]) == set(range(config.total_chunks))
    assert all(chunks == [] for chunks in state[1:])


def test_ring_topology_limits_sources_to_neighbors():
    from simulation.models import Peer

    peers = [
        Peer(id=0, owned_chunks=set(), neighbors={1}),
        Peer(id=1, owned_chunks=set(), neighbors={0}),
        Peer(id=2, owned_chunks={0}, neighbors=set()),
    ]
    strategy = RandomFirstStrategy(random.Random(5))

    assert strategy.select_source(peers[0], peers, 0) is None


def test_simulation_returns_neighbor_graph_for_frontend():
    config = SimulationConfig(file_size_mb=1, chunk_size_kb=256, peer_count=4, topology_mode="ring")
    result = BitTorrentSimulator(config=config, strategy="rarestFirst").run()

    assert result["neighborGraph"]["mode"] == "ring"
    assert {"source": 0, "target": 1} in result["neighborGraph"]["edges"]


def test_small_world_zero_rewire_builds_ring_lattice():
    from simulation.topology import build_neighbor_graph

    config = SimulationConfig(
        peer_count=8,
        topology_mode="smallWorld",
        neighbors_per_peer=4,
        topology_rewire_probability=0,
    )
    graph = build_neighbor_graph(config)

    for peer_id in range(config.peer_count):
        assert graph[peer_id] == {
            (peer_id - 2) % config.peer_count,
            (peer_id - 1) % config.peer_count,
            (peer_id + 1) % config.peer_count,
            (peer_id + 2) % config.peer_count,
        }


def test_small_world_rewire_creates_shortcuts_without_changing_edge_count():
    from simulation.topology import build_neighbor_graph

    config = SimulationConfig(
        seed=5,
        peer_count=10,
        topology_mode="smallWorld",
        neighbors_per_peer=4,
        topology_rewire_probability=1,
    )
    graph = build_neighbor_graph(config)
    edges = {
        (source, target)
        for source, neighbors in graph.items()
        for target in neighbors
        if source < target
    }
    local_edges = {
        tuple(sorted((source, (source + offset) % config.peer_count)))
        for source in range(config.peer_count)
        for offset in range(1, (config.neighbors_per_peer // 2) + 1)
    }

    assert len(edges) == config.peer_count * config.neighbors_per_peer // 2
    assert all(source != target for source, target in edges)
    assert edges - local_edges


def test_single_simulation_completes_all_peers():
    config = SimulationConfig(seed=11, bandwidth_kbps=1024, latency_ms=10)
    result = BitTorrentSimulator(config=config, strategy="rarestFirst").run()
    assert result["completed"] is True
    assert result["totalTime"] > 0
    assert all(peer["completion"] == 100.0 for peer in result["finalPeers"])
    assert any(log["event"] == "START" for log in result["logs"])
    assert any(log["event"] == "END" for log in result["logs"])


def test_compare_uses_identical_initial_state():
    config_payload = {"seed": 123, "bandwidthKbps": 1024, "latencyMs": 25}
    result = compare_strategies(config_payload)
    assert result["randomFirst"]["initialState"] == result["rarestFirst"]["initialState"]
    assert result["randomFirst"]["completed"] is True
    assert result["rarestFirst"]["completed"] is True
    assert result["winner"] in {"randomFirst", "rarestFirst", "tie"}


def test_rarest_strategy_picks_chunk_with_fewest_copies():
    from simulation.models import Peer

    peers = [
        Peer(id=0, owned_chunks={0}),
        Peer(id=1, owned_chunks={1}),
        Peer(id=2, owned_chunks={2}),
        Peer(id=3, owned_chunks={2}),
    ]
    downloader = peers[0]
    strategy = RarestFirstStrategy(random.Random(5))
    selected = strategy.select_chunk(downloader, peers, total_chunks=3)
    assert selected == 1


def test_rarest_strategy_spreads_in_flight_rare_chunks():
    from simulation.models import Peer

    peers = [
        Peer(id=0, owned_chunks={0, 1}, max_upload_slots=3, active_uploads={1: 0}),
        Peer(id=1, owned_chunks=set(), active_downloads={0: 0}),
        Peer(id=2, owned_chunks=set()),
    ]
    strategy = RarestFirstStrategy(random.Random(5))

    selected = strategy.select_chunk(peers[2], peers, total_chunks=2)

    assert selected == 1


def test_source_selection_policy_is_shared_between_strategies():
    from simulation.models import Peer

    class FakeConfig:
        chunk_size_kb = 256

    class FakeNetwork:
        config = FakeConfig()

        def effective_bandwidth(self, source, destination):
            return 1024 if source.id == 1 else 256

        def effective_latency_ms(self, source, destination):
            return 0

    peers = [
        Peer(id=0, owned_chunks=set()),
        Peer(id=1, owned_chunks={0}),
        Peer(id=2, owned_chunks={0}),
    ]
    random_strategy = RandomFirstStrategy(random.Random(5), FakeNetwork())
    rarest_strategy = RarestFirstStrategy(random.Random(5), FakeNetwork())

    assert random_strategy.select_source(peers[0], peers, 0).id == 1
    assert rarest_strategy.select_source(peers[0], peers, 0).id == 1


def test_default_upload_bandwidth_is_resolved_before_network_math():
    from simulation.models import Peer
    from simulation.network import NetworkModel

    config = SimulationConfig(bandwidth_kbps=512, upload_bandwidth_kbps=None)
    result = BitTorrentSimulator(config=config, strategy="randomFirst").run()
    bandwidth = NetworkModel(config).shared_upload_bandwidth(Peer(id=0))

    assert bandwidth == 512
    assert result["completed"] is True


def test_payload_accepts_split_bandwidth_and_slots_from_frontend():
    config = SimulationConfig.from_payload(
        {
            "download_bandwidth": 256,
            "upload_bandwidth": 64,
            "max_download_slots": 4,
            "max_upload_slots": 5,
        }
    )

    assert config.bandwidth_kbps == 256
    assert config.effective_upload_bandwidth_kbps == 64
    assert config.max_download_slots == 4
    assert config.max_upload_slots == 5

# new github 
def test_compare_respects_initial_probability_payload():
    low_density = compare_strategies({"seed": 9, "initialChunkProbability": 0.15})
    higher_density = compare_strategies({"seed": 9, "initialChunkProbability": 0.30})

    assert low_density["config"]["initial_chunk_probability"] == 0.15
    assert higher_density["config"]["initial_chunk_probability"] == 0.30
    assert low_density["initialState"] != higher_density["initialState"]
    assert higher_density["randomFirst"]["totalTime"] != higher_density["rarestFirst"]["totalTime"]


def test_network_conditions_are_deterministic_but_source_dependent():
    from simulation.models import Peer
    from simulation.network import NetworkModel

    config = SimulationConfig(seed=9, bandwidth_kbps=512, latency_ms=50)
    network = NetworkModel(config)
    source_a = Peer(id=0, owned_chunks={0})
    source_b = Peer(id=1, owned_chunks={0})
    destination = Peer(id=2)

    first_duration = network.transfer_time(config.chunk_size_kb, source_a, destination)
    second_duration = network.transfer_time(config.chunk_size_kb, source_a, destination)
    other_source_duration = network.transfer_time(config.chunk_size_kb, source_b, destination)

    assert first_duration == second_duration
    assert first_duration != other_source_duration


def test_churn_offline_peer_removes_its_chunks_from_swarm():
    config = SimulationConfig(file_size_mb=1, chunk_size_kb=256, peer_count=3, max_virtual_time=5)
    initial_state = [[0], [1, 2, 3], [1, 2, 3]]
    result = BitTorrentSimulator(
        config=config,
        strategy="rarestFirst",
        initial_state=initial_state,
        churn_events=[{"time": 0, "peerId": 0, "online": False}],
    ).run()

    assert result["completed"] is False
    assert result["chunkAvailability"][0] == 0
    assert any(log["event"] == "CHURN" and log["peerId"] == 0 and log["online"] is False for log in result["logs"])
    assert result["finalPeers"][0]["online"] is False


def test_churn_recommendation_returns_candidate_payload():
    result = recommend_churn_candidate(
        {
            "seed": 9,
            "initialChunkProbability": 0.15,
            "downloadBandwidthKbps": 512,
            "uploadBandwidthKbps": 512,
            "time": 1.0,
        }
    )

    assert result["recommendation"]["event"]["online"] is False
    assert 0 <= result["recommendation"]["peerId"] < result["config"]["peer_count"]
    assert len(result["trials"]) == 10


def test_churn_recommendation_respects_existing_churn_events():
    result = recommend_churn_candidate(
        {
            "seed": 9,
            "initialChunkProbability": 0.15,
            "downloadBandwidthKbps": 512,
            "uploadBandwidthKbps": 512,
            "time": 1.0,
            "churnEvents": [{"time": 0.0, "peerId": 0, "online": False}],
        }
    )

    trial_peer_ids = {trial["peerId"] for trial in result["trials"]}
    assert 0 not in trial_peer_ids
    assert len(result["trials"]) == 9


def test_statistics_charts_returns_three_chart_payloads():
    result = build_statistics_charts(
        {
            "fileSizeMb": 1,
            "chunkSizeKb": 256,
            "peerCount": 4,
            "seedStart": 1,
            "seedEnd": 2,
            "downloadBandwidthKbps": 512,
            "uploadBandwidthKbps": 512,
            "neighborsPerPeer": 2,
        }
    )

    assert len(result["charts"]["seedComparison"]) == 2
    assert {item["topology"] for item in result["charts"]["topologyComparison"]} == {
        "fullMesh",
        "randomK",
        "ring",
        "star",
        "smallWorld",
    }
    assert len(result["charts"]["rareChunkProgress"]) == 4
    assert all(series["points"][0]["completion"] == 0 for series in result["charts"]["rareChunkProgress"])
