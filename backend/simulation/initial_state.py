from __future__ import annotations

import random

from .config import SimulationConfig


# Khởi tạo trạng thái sở hữu chunk của peer một cách ngẫu nhiên nhưng có thể tái tạo được dựa trên seed.
def generate_initial_state(config: SimulationConfig) -> list[list[int]]:

    config.validate()
    rng = random.Random(config.seed)
    total_chunks = config.total_chunks
    peer_chunks: list[set[int]] = [set() for _ in range(config.peer_count)]

    # First pass: random Bernoulli ownership, producing diverse peer states.
    for peer_id in range(config.peer_count):
        for chunk_id in range(total_chunks):
            if rng.random() <= config.initial_chunk_probability:
                peer_chunks[peer_id].add(chunk_id)

    # Ensure every chunk has at least one owner.
    for chunk_id in range(total_chunks):
        if not any(chunk_id in chunks for chunks in peer_chunks):
            # peer_chunks[rng.randrange(config.peer_count)].add(chunk_id)
            peer_chunks[0].add(chunk_id)

    # Ensure every peer has at least one chunk.

    for peer_id, chunks in enumerate(peer_chunks):
        if not chunks:
            chunks.add(rng.randrange(total_chunks))

    # Avoid peers that start complete, keeping ownership coverage intact.

    for peer_id, chunks in enumerate(peer_chunks):
        if len(chunks) == total_chunks and total_chunks > 1:
            removable = [
                chunk_id
                for chunk_id in sorted(chunks)
                if sum(1 for owner in peer_chunks if chunk_id in owner) > 1
            ]
            if removable:
                chunks.remove(rng.choice(removable))

    return [list(chunks) for chunks in peer_chunks]


def clone_initial_state(initial_state: list[list[int]] | list[set[int]]) -> list[list[int]]:
    return [list(chunks) for chunks in initial_state]
