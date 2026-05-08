# scheduler/rarest_first.py

# Mục tiêu: Ưu tiên tải các chunk hiếm nhất trước
# Tránh: Chunk bị biến mất khỏi hệ thống
import random
from collections import defaultdict
from scheduler.base_scheduler import BaseScheduler

class RarestFirstScheduler(BaseScheduler):
    def select_chunk(self, requester, neighbors, all_peers):
        missing = requester.missing_chunks(self.total_chunks)

        # chunk_sources: Lưu trữ các neighbor có chunk_id
        # rarity_count: Đếm số lượng neighbor có chunk_id
        chunk_sources = defaultdict(list)
        rarity_count = defaultdict(int)

        for neighbor in neighbors:
            if not neighbor.online:
                continue

            for chunk_id in neighbor.chunks:
                if chunk_id in missing:
                    chunk_sources[chunk_id].append(neighbor)
                    rarity_count[chunk_id] += 1

        if not chunk_sources:
            return None, None

        min_rarity = min(rarity_count.values())

        rarest_chunks = [
            chunk_id
            for chunk_id, count in rarity_count.items()
            if count == min_rarity
        ]

        selected_chunk = random.choice(rarest_chunks)
        selected_source = random.choice(chunk_sources[selected_chunk])

        return selected_chunk, selected_source