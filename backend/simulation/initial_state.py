from __future__ import annotations

import random

from .config import SimulationConfig

# đọc lại phần generate initial chunk
# Khởi tạo trạng thái sở hữu chunk của peer một cách ngẫu nhiên nhưng có thể tái tạo được dựa trên seed.
def generate_initial_state(config: SimulationConfig) -> list[list[int]]:

    config.validate()
    rng = random.Random(config.seed)
    total_chunks = config.total_chunks
    peer_chunks: list[set[int]] = [set() for _ in range(config.peer_count)]

    # if config.initial_distribution_mode == "singleSeeder":
    #     peer_chunks[0].update(range(total_chunks))
    #     return [list(chunks) for chunks in peer_chunks]

    # First pass: random Bernoulli ownership, producing diverse peer states.
    for peer_id in range(config.peer_count):
        for chunk_id in range(total_chunks):
            if rng.random() <= config.initial_chunk_probability:
                peer_chunks[peer_id].add(chunk_id)

    # Ensure every chunk has at least one owner.
    for chunk_id in range(total_chunks):
        if not any(chunk_id in chunks for chunks in peer_chunks):
            if config.initial_distribution_mode == "singleSeeder":
                peer_chunks[0].add(chunk_id)
            else:
                peer_chunks[rng.randrange(config.peer_count)].add(chunk_id)

    return [list(chunks) for chunks in peer_chunks] 


def clone_initial_state(initial_state: list[list[int]] | list[set[int]]) -> list[list[int]]:
    return [list(chunks) for chunks in initial_state]
