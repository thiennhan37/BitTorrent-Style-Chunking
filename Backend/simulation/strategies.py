from __future__ import annotations

import random
from abc import ABC, abstractmethod

from .models import Peer


class ChunkSelectionStrategy(ABC):
    key = "base"
    display_name = "Base Strategy"

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def eligible_sources(self, downloader: Peer, peers: list[Peer], chunk_id: int) -> list[Peer]:
        return [peer for peer in peers if peer.can_upload_to(downloader, chunk_id)]

    def select_source(self, downloader: Peer, peers: list[Peer], chunk_id: int) -> Peer | None:
        sources = self.eligible_sources(downloader, peers, chunk_id)
        if not sources:
            return None
        return self.rng.choice(sources)

    @abstractmethod
    def select_chunk(self, downloader: Peer, peers: list[Peer], total_chunks: int) -> int | None:
        raise NotImplementedError


class RandomFirstStrategy(ChunkSelectionStrategy):
    key = "randomFirst"
    display_name = "Random-First"

    def select_chunk(self, downloader: Peer, peers: list[Peer], total_chunks: int) -> int | None:
        # kiểm tra peer có rảnh để tải không
        if not downloader.has_free_download_slot():
            return None

        # Lấy danh sách các chunk mà peer chưa có và có thể bắt đầu tải
        candidates = [
            chunk_id
            for chunk_id in downloader.missing_chunks(total_chunks)
            if downloader.can_start_download(chunk_id) 
                and self.eligible_sources(downloader, peers, chunk_id)
        ]
        if not candidates:
            return None
        return self.rng.choice(candidates)


class RarestFirstStrategy(ChunkSelectionStrategy):
    key = "rarestFirst"
    display_name = "Rarest-First"

    def select_chunk(self, downloader: Peer, peers: list[Peer], total_chunks: int) -> int | None:
        if not downloader.has_free_download_slot():
            return None

        availability: dict[int, int] = {}
        for chunk_id in downloader.missing_chunks(total_chunks):
            if not downloader.can_start_download(chunk_id):
                continue
            if not self.eligible_sources(downloader, peers, chunk_id):
                continue
            copies = sum(1 for peer in peers if peer.id != downloader.id
                         and peer.can_upload_to(downloader, chunk_id) and peer.has_chunk(chunk_id))
            if copies > 0:
                availability[chunk_id] = copies

        if not availability:
            return None

        rarest_count = min(availability.values())
        rarest_chunks = [chunk_id for chunk_id, count in availability.items() if count == rarest_count]
        return self.rng.choice(rarest_chunks)


def normalize_strategy_key(strategy: str) -> str:
    normalized = (strategy or "").replace("-", "").replace("_", "").lower()
    mapping = {
        "random": "randomFirst",
        "randomfirst": "randomFirst",
        "randomfirststrategy": "randomFirst",
        "rarest": "rarestFirst",
        "rarestfirst": "rarestFirst",
        "rarestfirststrategy": "rarestFirst",
    }
    if normalized not in mapping:
        raise ValueError("strategy must be one of: randomFirst, rarestFirst")
    return mapping[normalized]


def build_strategy(strategy: str, rng: random.Random) -> ChunkSelectionStrategy:
    key = normalize_strategy_key(strategy)
    if key == RandomFirstStrategy.key:
        return RandomFirstStrategy(rng)
    if key == RarestFirstStrategy.key:
        return RarestFirstStrategy(rng)
    raise ValueError(f"Unsupported strategy: {strategy}")
