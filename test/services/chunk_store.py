# services/chunk_store.py

from __future__ import annotations

import random


def generate_initial_chunks(
    peer_count: int,
    total_chunks: int,
    probability: float,
    seed: int | None = 42,
) -> list[set[int]]:
    """
    Sinh danh sách chunk ban đầu cho từng peer.

    Trả về list có độ dài peer_count, mỗi phần tử là set chunk_id mà peer đó sở hữu.
    Hàm bảo đảm mỗi chunk xuất hiện ở ít nhất một peer để swarm không bị thiếu dữ liệu.
    """

    if peer_count <= 0:
        raise ValueError("peer_count must be greater than 0")

    if total_chunks <= 0:
        raise ValueError("total_chunks must be greater than 0")

    if probability < 0 or probability > 1:
        raise ValueError("probability must be between 0 and 1")

    rng = random.Random(seed)
    peer_chunks: list[set[int]] = [set() for _ in range(peer_count)]

    for peer_id in range(peer_count):
        for chunk_id in range(total_chunks):
            if rng.random() < probability:
                peer_chunks[peer_id].add(chunk_id)

    for chunk_id in range(total_chunks):
        holders = [
            peer_id
            for peer_id in range(peer_count)
            if chunk_id in peer_chunks[peer_id]
        ]

        if not holders:
            selected_peer = rng.randrange(peer_count)
            peer_chunks[selected_peer].add(chunk_id)

    return peer_chunks
