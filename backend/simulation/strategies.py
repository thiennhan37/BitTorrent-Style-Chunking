from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any

from .models import Peer


class ChunkSelectionStrategy(ABC):
    key = "base"
    display_name = "Base Strategy"

    def __init__(self, rng: random.Random, network: Any | None = None) -> None:
        self.rng = rng
        self.network = network

    def eligible_sources(self, downloader: Peer, peers: list[Peer], chunk_id: int) -> list[Peer]:
        # Chi tra ve list source co kha nang cung cap chunk
        return [peer for peer in peers if peer.can_upload_to(downloader, chunk_id)]

    def has_transfer_opportunity(self, downloader: Peer, peers: list[Peer], chunk_id: int) -> bool:
        # Mot chunk chi duoc chon neu downloader con slot, chua co/chua dang tai chunk do,
        # va ton tai it nhat mot uploader co the phuc vu ngay.
        return downloader.can_start_download(chunk_id) and bool(self.eligible_sources(downloader, peers, chunk_id))

    def _source_estimated_duration(self, source: Peer, downloader: Peer) -> float:
        if self.network is None:
            return source.active_upload_count / max(source.max_upload_slots, 1)

        bandwidth = self.network.effective_bandwidth(source, downloader)
        latency_ms = self.network.effective_latency_ms(source, downloader)
        if bandwidth <= 0:
            return float("inf")
        return latency_ms / 1000.0 + self.network.config.chunk_size_kb / bandwidth

    def _source_rank_key(self, source: Peer, downloader: Peer) -> tuple[float, int, float]:
        return (
            self._source_estimated_duration(source, downloader),
            source.active_upload_count,
            self.rng.random(),
        )

    def ranked_sources(self, downloader: Peer, peers: list[Peer], chunk_id: int) -> list[Peer]:
        """Eligible uploaders for chunk_id, best-first (same order as select_source)."""
        sources = self.eligible_sources(downloader, peers, chunk_id)
        if not sources:
            return []
        return sorted(sources, key=lambda source: self._source_rank_key(source, downloader))

    def select_source(self, downloader: Peer, peers: list[Peer], chunk_id: int) -> Peer | None:
        ranked = self.ranked_sources(downloader, peers, chunk_id)
        return ranked[0] if ranked else None

    @abstractmethod
    def select_chunk(self, downloader: Peer, peers: list[Peer], total_chunks: int) -> int | None:
        raise NotImplementedError


class RandomFirstStrategy(ChunkSelectionStrategy):
    key = "randomFirst"
    display_name = "Random-First"

    def select_chunk(self, downloader: Peer, peers: list[Peer], total_chunks: int) -> int | None:
        if not downloader.has_free_download_slot():
            return None

        # Random-First: trong cac chunk co the tai ngay, chon ngau nhien.
        candidates = [
            chunk_id
            for chunk_id in downloader.missing_chunks(total_chunks)
            if self.has_transfer_opportunity(downloader, peers, chunk_id)
        ]
        if not candidates:
            return None
        return self.rng.choice(candidates)


class RarestFirstStrategy(ChunkSelectionStrategy):
    key = "rarestFirst"
    display_name = "Rarest-First"

    def _active_download_count(self, peers: list[Peer], chunk_id: int) -> int:
        return sum(1 for peer in peers if peer.online and chunk_id in peer.active_downloads)

    def select_chunk(self, downloader: Peer, peers: list[Peer], total_chunks: int) -> int | None:
        if not downloader.has_free_download_slot():
            return None

        # Rarest-First cai tien: tinh ca active download nhu ban sao "sap co".
        # Cach nay tranh viec nhieu peer cung chen vao mot chunk hiem, trong khi
        # cac chunk hiem khac van chi nam o peer nguon ban dau.
        candidates: list[tuple[tuple[int, int], int]] = []
        for chunk_id in downloader.missing_chunks(total_chunks):
            sources = self.eligible_sources(downloader, peers, chunk_id)
            if not downloader.can_start_download(chunk_id) or not sources:
                continue
            copies = len(sources)
            if copies <= 0:
                continue

            in_flight = self._active_download_count(peers, chunk_id)
            projected_copies = copies + in_flight
            candidates.append(((projected_copies, copies), chunk_id))

        if not candidates:
            return None

        best_score = min(score for score, _ in candidates)
        rarest_chunks = [chunk_id for score, chunk_id in candidates if score == best_score]
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


def build_strategy(strategy: str, rng: random.Random, network: Any | None = None) -> ChunkSelectionStrategy:
    key = normalize_strategy_key(strategy)
    if key == RandomFirstStrategy.key:
        return RandomFirstStrategy(rng, network)
    if key == RarestFirstStrategy.key:
        return RarestFirstStrategy(rng, network)
    raise ValueError(f"Unsupported strategy: {strategy}")
