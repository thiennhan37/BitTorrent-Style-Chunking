# scheduler/random_first.py

import random
from scheduler.base_scheduler import BaseScheduler

class RandomFirstScheduler(BaseScheduler):
    def select_chunk(self, requester, neighbors, all_peers):
        candidates = []

        missing = requester.missing_chunks(self.total_chunks)

        for neighbor in neighbors:
            if not neighbor.online:
                continue

            available = missing.intersection(neighbor.chunks)

            for chunk_id in available:
                candidates.append((chunk_id, neighbor))

        if not candidates:
            return None, None

        return random.choice(candidates)