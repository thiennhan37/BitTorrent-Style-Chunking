# Phân phối ngẫu nhiên chunk cho các peer
# Đảm bảo mọi chunk tồn tại ít nhất 1 lần trong hệ thống

import numpy as np

def generate_initial_chunks(peer_count, total_chunks, probability, seed=42):
    # probability: xác suất peer sở hữu chunk
    rng = np.random.default_rng(seed)

    peer_chunks = [set() for _ in range(peer_count)]

    for peer_id in range(peer_count):
        for chunk_id in range(total_chunks):
            if rng.random() <= probability:
                peer_chunks[peer_id].add(chunk_id)

    # Đảm bảo mỗi chunk tồn tại ít nhất 1 lần trong hệ thống
    # Nếu chunk nào không được sở hữu bởi bất kỳ peer nào, sẽ gán ngẫu nhiên cho một peer.
    for chunk_id in range(total_chunks):
        holders = [
            peer_id
            for peer_id in range(peer_count)
            if chunk_id in peer_chunks[peer_id]
        ]

        if not holders:
            selected_peer = rng.integers(0, peer_count)
            peer_chunks[selected_peer].add(chunk_id)

    return peer_chunks