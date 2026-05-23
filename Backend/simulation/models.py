from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Peer:
    id: int
    owned_chunks: set[int] = field(default_factory=set)
    online: bool = True
    download_bandwidth_kbps: float = 512.0
    upload_bandwidth_kbps: float = 512.0
    latency_ms: float = 50.0
    max_download_slots: int = 1
    max_upload_slots: int = 3
    # can unique chunk_id cho moi transfer, de tranh tinh huong 
    # 2 transfer cung chunk tu 2 source khac nhau  
    active_downloads: dict[int, int] = field(default_factory=dict)  # chunk_id -> source_peer_id
    
    # can unique chunk_id cho moi transfer, de tranh tinh huong
    # cung upload 1 luc nhieu chunk cung 1 destination
    active_uploads: dict[int, int] = field(default_factory=dict)  # destination_peer_id -> chunk_id

    def has_chunk(self, chunk_id: int) -> bool:
        return chunk_id in self.owned_chunks

    def receive_chunk(self, chunk_id: int) -> None:
        self.owned_chunks.add(chunk_id)

    def missing_chunks(self, total_chunks: int) -> list[int]:
        return [chunk_id for chunk_id in range(total_chunks) if chunk_id not in self.owned_chunks]

    def completion_percentage(self, total_chunks: int) -> float:
        if total_chunks == 0:
            return 0.0
        return round(len(self.owned_chunks) * 100 / total_chunks, 2)

    def is_complete(self, total_chunks: int) -> bool:
        return len(self.owned_chunks) >= total_chunks

    def has_free_download_slot(self) -> bool:
        return self.active_download_count < self.max_download_slots

    def has_free_upload_slot(self) -> bool:
        return self.active_upload_count < self.max_upload_slots

    @property
    def active_download_count(self) -> int:
        return len(self.active_downloads)

    @property
    def active_upload_count(self) -> int:
        return len(self.active_uploads)

    def can_start_download(self, chunk_id: int) -> bool:
        return (
            self.online
            and self.has_free_download_slot()
            and not self.has_chunk(chunk_id)
            and chunk_id not in self.active_downloads
        )

    def can_upload_to(self, downloader: "Peer", chunk_id: int) -> bool:
        return (
            self.online
            and downloader.online
            and self.id != downloader.id
            and self.has_chunk(chunk_id)
            and self.has_free_upload_slot()
            and downloader.id not in self.active_uploads
        )

    def start_transfer_from(self, source: "Peer", chunk_id: int) -> None:
        """Reserve download/upload slot truoc khi coroutine transfer bat dau chay."""

        if not self.can_start_download(chunk_id):
            raise RuntimeError(f"Peer {self.id} cannot start download for chunk {chunk_id}")
        if not source.can_upload_to(self, chunk_id):
            raise RuntimeError(f"Peer {source.id} cannot upload chunk {chunk_id} to peer {self.id}")
        self.active_downloads[chunk_id] = source.id
        source.active_uploads[self.id] = chunk_id

    def finish_transfer_from(self, source: "Peer", chunk_id: int, success: bool = True) -> None:
        """Release slot va chi add chunk sau khi transfer hoan tat thanh cong."""

        actual_source_id = self.active_downloads.get(chunk_id)
        actual_chunk_id = source.active_uploads.get(self.id)
        if actual_source_id != source.id or actual_chunk_id != chunk_id:
            raise RuntimeError(
                f"Invalid transfer finish: source={source.id}, destination={self.id}, chunk={chunk_id}"
            )
        try:
            if success:
                self.receive_chunk(chunk_id)
        finally:
            self.active_downloads.pop(chunk_id, None)
            source.active_uploads.pop(self.id, None)

    def to_dict(self, total_chunks: int) -> dict[str, Any]:
        return {
            "peerId": self.id,
            "online": self.online,
            "ownedChunks": sorted(self.owned_chunks),
            "ownedChunkCount": len(self.owned_chunks),
            "missingChunkCount": max(total_chunks - len(self.owned_chunks), 0),
            "completion": self.completion_percentage(total_chunks),
            "activeDownloads": dict(self.active_downloads),
            "activeUploads": dict(self.active_uploads),
        }