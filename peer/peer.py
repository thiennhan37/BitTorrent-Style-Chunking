# models/peer.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional
import random

from models.chunk import Chunk


@dataclass(slots=True)
class Peer:
    id: int
    download_bandwidth_kbps: float = 512.0
    upload_bandwidth_kbps: float = 512.0
    latency_ms: float = 50.0

    max_download_slots: int = 1
    max_upload_slots: int = 3

    owned_chunks: dict[int, Chunk] = field(default_factory=dict)

    active_downloads: dict[int, int] = field(default_factory=dict)
    active_uploads: dict[int, int] = field(default_factory=dict)
    is_online: bool = True

    def __post_init__(self) -> None:
        if self.id < 0:
            raise ValueError("Peer id must be greater than or equal to 0")

        if self.download_bandwidth_kbps <= 0:
            raise ValueError("Download bandwidth must be greater than 0")

        if self.upload_bandwidth_kbps <= 0:
            raise ValueError("Upload bandwidth must be greater than 0")

        if self.latency_ms < 0:
            raise ValueError("Latency must be greater than or equal to 0")

        if self.max_download_slots <= 0:
            raise ValueError("Max download slots must be greater than 0")

        if self.max_upload_slots <= 0:
            raise ValueError("Max upload slots must be greater than 0")

    @classmethod
    def with_chunks(
        cls,
        id: int,
        chunks: Iterable[Chunk],
        download_bandwidth_kbps: float = 512.0,
        upload_bandwidth_kbps: float = 512.0,
        latency_ms: float = 50.0,
        max_download_slots: int = 1,
        max_upload_slots: int = 3,
    ) -> "Peer":

        peer = cls(
            id=id,
            download_bandwidth_kbps=download_bandwidth_kbps,
            upload_bandwidth_kbps=upload_bandwidth_kbps,
            latency_ms=latency_ms,
            max_download_slots=max_download_slots,
            max_upload_slots=max_upload_slots,
        )

        for chunk in chunks:
            peer.receive_chunk(chunk)

        return peer

    @property
    def chunk_ids(self) -> set[int]:
        return set(self.owned_chunks.keys())

    @property
    def current_download_count(self) -> int:
        return len(self.active_downloads)

    @property
    def current_upload_count(self) -> int:
        return len(self.active_uploads)

    @property
    def free_download_slots(self) -> int:
        return self.max_download_slots - self.current_download_count

    @property
    def free_upload_slots(self) -> int:
        return self.max_upload_slots - self.current_upload_count

    def has_free_download_slot(self) -> bool:
        return self.current_download_count < self.max_download_slots

    def has_free_upload_slot(self) -> bool:
        return self.current_upload_count < self.max_upload_slots

    def has_chunk(self, chunk_id: int) -> bool:
        return chunk_id in self.owned_chunks

    def get_chunk(self, chunk_id: int) -> Optional[Chunk]:
        return self.owned_chunks.get(chunk_id)

    def receive_chunk(self, chunk: Chunk) -> None:
        self.owned_chunks[chunk.id] = chunk

    def remove_chunk(self, chunk_id: int) -> None:
        self.owned_chunks.pop(chunk_id, None)

    def missing_chunk_ids(self, all_chunks: Iterable[Chunk]) -> set[int]:
        all_chunk_ids = {chunk.id for chunk in all_chunks}
        return all_chunk_ids - self.chunk_ids

    def completion_percentage(self, all_chunks: Iterable[Chunk]) -> float:
        all_chunk_ids = {chunk.id for chunk in all_chunks}

        if not all_chunk_ids:
            return 0.0

        owned_valid_chunks = self.chunk_ids & all_chunk_ids
        percentage = len(owned_valid_chunks) / len(all_chunk_ids) * 100

        return round(percentage, 2)

    def is_complete(self, all_chunks: Iterable[Chunk]) -> bool:
        return len(self.missing_chunk_ids(all_chunks)) == 0

    def can_start_download(self, chunk_id: int) -> bool:

        if not self.is_online:
            return False

        if self.has_chunk(chunk_id):
            return False

        if chunk_id in self.active_downloads:
            return False

        if not self.has_free_download_slot():
            return False

        return True

    def can_upload_to(self, downloader: "Peer", chunk_id: int) -> bool:
        """
        Kiểm tra peer hiện tại có thể upload chunk cho downloader hay không.

        Điều kiện:
            - Peer hiện tại đang online
            - Downloader đang online
            - Không upload cho chính mình
            - Peer hiện tại có chunk cần upload
            - Peer hiện tại còn upload slot
            - Peer hiện tại chưa đang upload cho downloader đó
        """

        if not self.is_online or not downloader.is_online:
            return False

        if self.id == downloader.id:
            return False

        if not self.has_chunk(chunk_id):
            return False

        if not self.has_free_upload_slot():
            return False

        if downloader.id in self.active_uploads:
            return False

        return True

    def can_download_from(self, source_peer: "Peer", chunk_id: int) -> bool:
        """
        Kiểm tra peer hiện tại có thể tải chunk từ source_peer hay không.

        Cần đồng thời thỏa:
            - Downloader còn download slot
            - Uploader còn upload slot
            - Uploader có chunk
        """

        return (
            self.can_start_download(chunk_id)
            and source_peer.can_upload_to(self, chunk_id)
        )

    def start_download_from(
        self,
        source_peer: "Peer",
        chunk_id: int,
    ) -> None:
        """
        Bắt đầu một phiên download.

        Hàm này chỉ đăng ký trạng thái:
            - self đang download chunk_id từ source_peer
            - source_peer đang upload chunk_id cho self

        Chưa thêm chunk vào self ở bước này.
        Chunk chỉ được thêm khi gọi finish_download_from().
        """

        if not self.can_download_from(source_peer, chunk_id):
            raise RuntimeError(
                f"Peer {self.id} cannot download chunk {chunk_id} "
                f"from Peer {source_peer.id}. "
                f"Downloader slots: {self.current_download_count}/{self.max_download_slots}, "
                f"Uploader slots: {source_peer.current_upload_count}/{source_peer.max_upload_slots}"
            )

        self.active_downloads[chunk_id] = source_peer.id
        source_peer.active_uploads[self.id] = chunk_id

    def finish_download_from(
        self,
        source_peer: "Peer",
        chunk_id: int,
        success: bool = True,
    ) -> None:
        """
        Kết thúc một phiên download.

        Nếu success = True:
            - Peer nhận chunk từ source_peer

        Dù thành công hay thất bại:
            - Giải phóng download slot của peer hiện tại
            - Giải phóng upload slot của source_peer
        """

        actual_source_id = self.active_downloads.get(chunk_id)

        if actual_source_id != source_peer.id:
            raise RuntimeError(
                f"Peer {self.id} is not downloading chunk {chunk_id} "
                f"from Peer {source_peer.id}"
            )

        uploaded_chunk_id = source_peer.active_uploads.get(self.id)

        if uploaded_chunk_id != chunk_id:
            raise RuntimeError(
                f"Peer {source_peer.id} is not uploading chunk {chunk_id} "
                f"to Peer {self.id}"
            )

        try:
            if success:
                chunk = source_peer.get_chunk(chunk_id)

                if chunk is None:
                    raise RuntimeError(
                        f"Source Peer {source_peer.id} no longer has chunk {chunk_id}"
                    )

                self.receive_chunk(chunk)

        finally:
            self.active_downloads.pop(chunk_id, None)
            source_peer.active_uploads.pop(self.id, None)

    def cancel_download_from(
        self,
        source_peer: "Peer",
        chunk_id: int,
    ) -> None:
        """
        Hủy phiên download đang chạy.
        Dùng khi mô phỏng lỗi mạng, peer offline, timeout.
        """
        self.finish_download_from(
            source_peer=source_peer,
            chunk_id=chunk_id,
            success=False,
        )

    def estimate_download_time(
        self,
        source_peer: "Peer",
        chunk: Chunk,
    ) -> float:
        """
        Ước lượng thời gian tải chunk.

        Công thức:
            effective_bandwidth = min(download_bandwidth của downloader,
                                      upload_bandwidth của uploader)

            transfer_time = chunk_size / effective_bandwidth

            total_time = transfer_time + latency

        Đơn vị trả về: giây
        """

        effective_bandwidth = min(
            self.download_bandwidth_kbps,
            source_peer.upload_bandwidth_kbps,
        )

        if effective_bandwidth <= 0:
            raise ValueError("Effective bandwidth must be greater than 0")

        transfer_time_seconds = chunk.size_kb / effective_bandwidth
        latency_seconds = max(self.latency_ms, source_peer.latency_ms) / 1000

        return transfer_time_seconds + latency_seconds

    def download_chunk_from(
        self,
        source_peer: "Peer",
        chunk_id: int,
    ) -> float:
        """
        Download đồng bộ một chunk từ source_peer.

        Hàm này phù hợp để test nhanh.

        Trong mô phỏng SimPy sau này, nên dùng 3 bước:
            1. start_download_from()
            2. env.timeout(download_time)
            3. finish_download_from()
        """

        chunk = source_peer.get_chunk(chunk_id)

        if chunk is None:
            raise RuntimeError(
                f"Source Peer {source_peer.id} does not have chunk {chunk_id}"
            )

        download_time = self.estimate_download_time(
            source_peer=source_peer,
            chunk=chunk,
        )

        self.start_download_from(
            source_peer=source_peer,
            chunk_id=chunk_id,
        )

        self.finish_download_from(
            source_peer=source_peer,
            chunk_id=chunk_id,
            success=True,
        )

        return download_time

    def choose_random_missing_chunk(
        self,
        all_chunks: Iterable[Chunk],
    ) -> Optional[int]:
        """
        Chiến lược Random First:
        chọn ngẫu nhiên một chunk còn thiếu.
        """

        missing_chunks = list(self.missing_chunk_ids(all_chunks))

        if not missing_chunks:
            return None

        return random.choice(missing_chunks)

    def choose_rarest_missing_chunk(
        self,
        all_chunks: Iterable[Chunk],
        peers: Iterable["Peer"],
        require_available_source: bool = True,
    ) -> Optional[int]:
        """
        Chiến lược Rarest First:
        chọn chunk hiếm nhất trong các chunk peer hiện tại còn thiếu.

        Nếu require_available_source = True:
            - Chỉ tính những source peer còn upload slot.
            - Nghĩa là chunk được chọn phải đang có thể tải được ngay.

        Nếu require_available_source = False:
            - Tính theo toàn mạng, không quan tâm peer nguồn đang bận hay rảnh.
        """

        peer_list = list(peers)

        if require_available_source and not self.has_free_download_slot():
            return None

        missing_chunks = self.missing_chunk_ids(all_chunks)

        if not missing_chunks:
            return None

        availability: dict[int, int] = {}

        for chunk_id in missing_chunks:
            count = 0

            for peer in peer_list:
                if peer.id == self.id:
                    continue

                if not peer.has_chunk(chunk_id):
                    continue

                if require_available_source and not peer.has_free_upload_slot():
                    continue

                count += 1

            if count > 0:
                availability[chunk_id] = count

        if not availability:
            return None

        minimum_count = min(availability.values())

        rarest_chunks = [
            chunk_id
            for chunk_id, count in availability.items()
            if count == minimum_count
        ]

        return random.choice(rarest_chunks)

    def find_source_peer(
        self,
        peers: Iterable["Peer"],
        chunk_id: int,
        require_free_upload_slot: bool = True,
    ) -> Optional["Peer"]:
        """
        Tìm một peer khác có thể cung cấp chunk_id.

        Nếu require_free_upload_slot = True:
            - Chỉ chọn peer đang còn upload slot.
            - Đây là lựa chọn nên dùng trong mô phỏng thực tế.
        """

        if not self.can_start_download(chunk_id):
            return None

        candidates: list[Peer] = []

        for peer in peers:
            if peer.id == self.id:
                continue

            if not peer.has_chunk(chunk_id):
                continue

            if require_free_upload_slot and not peer.can_upload_to(self, chunk_id):
                continue

            candidates.append(peer)

        if not candidates:
            return None

        return random.choice(candidates)

    def to_dict(self, all_chunks: Iterable[Chunk]) -> dict:
        """
        Chuyển Peer thành dictionary để debug hoặc trả API.
        """

        all_chunks = list(all_chunks)

        return {
            "id": self.id,
            "is_online": self.is_online,

            "chunk_ids": sorted(self.chunk_ids),
            "chunk_count": len(self.owned_chunks),
            "completion_percentage": self.completion_percentage(all_chunks),
            "is_complete": self.is_complete(all_chunks),

            "download_bandwidth_kbps": self.download_bandwidth_kbps,
            "upload_bandwidth_kbps": self.upload_bandwidth_kbps,
            "latency_ms": self.latency_ms,

            "download_slots": {
                "used": self.current_download_count,
                "max": self.max_download_slots,
                "free": self.free_download_slots,
            },

            "upload_slots": {
                "used": self.current_upload_count,
                "max": self.max_upload_slots,
                "free": self.free_upload_slots,
            },

            "active_downloads": dict(self.active_downloads),
            "active_uploads": dict(self.active_uploads),
        }