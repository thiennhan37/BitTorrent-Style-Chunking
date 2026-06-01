from __future__ import annotations

import json
import random
from collections.abc import Iterable, Mapping
from typing import Any

from .config import SimulationConfig


NeighborGraph = dict[int, set[int]]


def _empty_graph(peer_count: int) -> NeighborGraph:
    return {peer_id: set() for peer_id in range(peer_count)}


def _add_edge(graph: NeighborGraph, source: int, target: int) -> None:
    if source == target:
        return
    if source not in graph or target not in graph:
        raise ValueError(f"topology edge contains invalid peer id: {source}-{target}")
    graph[source].add(target)
    graph[target].add(source)


def _remove_edge(graph: NeighborGraph, source: int, target: int) -> None:
    graph[source].discard(target)
    graph[target].discard(source)


def _parse_peer_id(value: Any) -> int:
    return int(str(value).strip().removeprefix("P").removeprefix("p"))

# chuyển custom dạng string thành adjecency list hoặc edge list
def _parse_custom_text(value: str) -> Any:
    text = value.strip()
    if not text:
        return {}
    if text.startswith("{") or text.startswith("["):
        return json.loads(text)

    adjacency: dict[int, list[int]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if ":" in line:
            peer_text, neighbor_text = line.split(":", 1)
        elif "->" in line:
            peer_text, neighbor_text = line.split("->", 1)
        else:
            # chuẩn hóa dạng đồ thị cạnh kề
            parts = line.replace(",", " ").split()
            if len(parts) != 2:
                raise ValueError("custom topology lines must be 'peer: n1,n2' or 'source target'")
            peer_id, neighbor_id = map(_parse_peer_id, parts)
            # nếu key chưa có thì append
            adjacency.setdefault(peer_id, []).append(neighbor_id)
            continue 

        peer_id = _parse_peer_id(peer_text)
        neighbors = [item for item in neighbor_text.replace(",", " ").split() if item]
        adjacency.setdefault(peer_id, []).extend(_parse_peer_id(item) for item in neighbors)
    return adjacency 


def normalize_custom_graph(raw_graph: Any, peer_count: int) -> NeighborGraph:
    if isinstance(raw_graph, str):
        raw_graph = _parse_custom_text(raw_graph)

    graph = _empty_graph(peer_count)
    if raw_graph in (None, "", {}):
        return graph

    # hỗ trợ dạng json với các key "adjacency" hoặc "edges"
    if isinstance(raw_graph, Mapping):
        if "adjacency" in raw_graph:
            raw_graph = raw_graph["adjacency"]
        elif "edges" in raw_graph:
            raw_graph = raw_graph["edges"]

    if isinstance(raw_graph, Mapping):
        for peer_id, neighbors in raw_graph.items():
            source = _parse_peer_id(peer_id)
            if isinstance(neighbors, str):
                neighbors = [item for item in neighbors.replace(",", " ").split() if item]
            for target_value in neighbors:
                _add_edge(graph, source, _parse_peer_id(target_value))
        return graph

    if isinstance(raw_graph, Iterable):
        for item in raw_graph:
            if isinstance(item, Mapping):
                source = _parse_peer_id(item.get("source", item.get("from")))
                target = _parse_peer_id(item.get("target", item.get("to")))
            else:
                source, target = item
                source = _parse_peer_id(source)
                target = _parse_peer_id(target)
            _add_edge(graph, source, target)
        return graph

    raise ValueError("custom topology must be an adjacency map or an edge list")


def _build_small_world_graph(config: SimulationConfig, rng: random.Random) -> NeighborGraph:
    peer_count = config.peer_count
    degree = config.neighbors_per_peer
    if degree % 2 != 0:
        raise ValueError("smallWorld topology requires an even neighbors_per_peer value")
    if degree >= peer_count:
        raise ValueError("smallWorld topology requires neighbors_per_peer to be less than peer_count")

    graph = _empty_graph(peer_count)
    local_edges: list[tuple[int, int]] = []
    half_degree = degree // 2

    for source in range(peer_count):
        for offset in range(1, half_degree + 1):
            target = (source + offset) % peer_count
            _add_edge(graph, source, target)
            local_edges.append((source, target))

    for source, old_target in local_edges:
        if rng.random() >= config.topology_rewire_probability:
            continue

        candidates = [
            candidate
            for candidate in range(peer_count)
            if candidate != source and candidate != old_target and candidate not in graph[source]
        ]
        if not candidates:
            continue

        _remove_edge(graph, source, old_target)
        _add_edge(graph, source, rng.choice(candidates))

    return graph


def build_neighbor_graph(config: SimulationConfig, custom_graph: Any | None = None) -> NeighborGraph:
    peer_count = config.peer_count
    graph = _empty_graph(peer_count)

    if config.topology_mode == "custom":
        custom = normalize_custom_graph(custom_graph, peer_count)
        if not any(custom.values()):
            raise ValueError("custom topology requires at least one edge")
        return custom

    if config.topology_mode == "fullMesh":
        for source in range(peer_count):
            for target in range(source + 1, peer_count):
                _add_edge(graph, source, target)
        return graph

    if config.topology_mode == "ring":
        for peer_id in range(peer_count):
            _add_edge(graph, peer_id, (peer_id + 1) % peer_count)
        return graph

    if config.topology_mode == "star":
        for peer_id in range(1, peer_count):
            _add_edge(graph, 0, peer_id)
        return graph

    # tạo seed mới tách biệt với seed hệ thống thống kê
    rng = random.Random(config.seed + 97)

    if config.topology_mode == "smallWorld":
        return _build_small_world_graph(config, rng)

    target_degree = min(config.neighbors_per_peer, peer_count - 1)
    for peer_id in range(peer_count):
        candidates = [candidate for candidate in range(peer_count) if candidate != peer_id]
        rng.shuffle(candidates)
        for candidate in candidates:
            if len(graph[peer_id]) >= target_degree:
                break
            _add_edge(graph, peer_id, candidate)

    return graph


def graph_to_dict(graph: NeighborGraph, mode: str, neighbors_per_peer: int) -> dict[str, Any]:
    edges = [
        {"source": source, "target": target}
        for source, neighbors in graph.items()
        for target in sorted(neighbors)
        if source < target
    ]
    return {
        "mode": mode,
        "neighborsPerPeer": neighbors_per_peer,
        "adjacency": {str(peer_id): sorted(neighbors) for peer_id, neighbors in graph.items()},
        "edges": edges,
    }
