# services/bittorrent_service.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from models import Chunk, Peer
from strategies import (
    ChunkSelectionStrategy,
    RandomAvailableSourcePeerStrategy,
    RarestFirstStrategy,
)
from services.chunk_store import generate_initial_chunks


@dataclass(frozen=True, slots=True)
class TransferSession:
    """
    Đại diện cho một phiên tải chunk đang hoặc đã được service xử lý.
    """

    step: int
    downloader_id: int
    source_peer_id: int
    chunk_id: int
    estimated_seconds: float

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "downloader_id": self.downloader_id,
            "source_peer_id": self.source_peer_id,
            "chunk_id": self.chunk_id,
            "estimated_seconds": round(self.estimated_seconds, 4),
        }


@dataclass(frozen=True, slots=True)
class TransferEvent:
    """
    Log sự kiện để dễ debug, in báo cáo hoặc kiểm thử mô phỏng.
    """

    step: int
    event_type: str
    downloader_id: Optional[int] = None
    source_peer_id: Optional[int] = None
    chunk_id: Optional[int] = None
    estimated_seconds: Optional[float] = None
    success: Optional[bool] = None
    message: str = ""

    def to_dict(self) -> dict:
        data = {
            "step": self.step,
            "event_type": self.event_type,
            "downloader_id": self.downloader_id,
            "source_peer_id": self.source_peer_id,
            "chunk_id": self.chunk_id,
            "estimated_seconds": (
                round(self.estimated_seconds, 4)
                if self.estimated_seconds is not None
                else None
            ),
            "success": self.success,
            "message": self.message,
        }

        return {key: value for key, value in data.items() if value is not None and value != ""}


class BitTorrentService:
    """
    Service điều phối mạng BitTorrent mini.

    Trách nhiệm chính:
        - Quản lý file, chunk và danh sách peer.
        - Chọn chunk cần tải bằng ChunkSelectionStrategy.
        - Chọn peer nguồn bằng RandomAvailableSourcePeerStrategy.
        - Khóa/mở download slot và upload slot thông qua model Peer.
        - Chạy mô phỏng theo từng round cho đến khi hoàn tất hoặc bị kẹt.
    """

    def __init__(
        self,
        file_size_kb: int,
        chunk_size_kb: int,
        chunk_strategy: Optional[ChunkSelectionStrategy] = None,
        source_peer_strategy: Optional[RandomAvailableSourcePeerStrategy] = None,
    ) -> None:
        self.file_size_kb = file_size_kb
        self.chunk_size_kb = chunk_size_kb
        self.chunks: list[Chunk] = Chunk.split_file(
            file_size_kb=file_size_kb,
            chunk_size_kb=chunk_size_kb,
        )
        self._chunk_by_id: dict[int, Chunk] = {chunk.id: chunk for chunk in self.chunks}
        self.peers: dict[int, Peer] = {}

        self.chunk_strategy = chunk_strategy or RarestFirstStrategy()
        self.source_peer_strategy = source_peer_strategy or RandomAvailableSourcePeerStrategy()

        self.current_step = 0
        self.active_sessions: dict[tuple[int, int], TransferSession] = {}
        self.events: list[TransferEvent] = []

    @classmethod
    def create_swarm(
        cls,
        file_size_kb: int,
        chunk_size_kb: int,
        peer_count: int,
        initial_chunk_probability: float = 0.25,
        seed: int | None = 42,
        include_seeder: bool = True,
        chunk_strategy: Optional[ChunkSelectionStrategy] = None,
    ) -> "BitTorrentService":
        """
        Factory tạo sẵn swarm.

        Nếu include_seeder=True:
            - Peer 0 là seeder có đủ toàn bộ chunk.
            - Các peer còn lại được phát chunk ngẫu nhiên theo probability.

        Nếu include_seeder=False:
            - Tất cả peer được phát chunk ngẫu nhiên.
            - Vẫn bảo đảm mỗi chunk có ít nhất một peer giữ.
        """

        if peer_count <= 0:
            raise ValueError("peer_count must be greater than 0")

        service = cls(
            file_size_kb=file_size_kb,
            chunk_size_kb=chunk_size_kb,
            chunk_strategy=chunk_strategy,
        )

        if include_seeder:
            service.add_peer_with_chunks(peer_id=0, chunk_ids=service.all_chunk_ids)
            leecher_count = peer_count - 1
            start_peer_id = 1
        else:
            leecher_count = peer_count
            start_peer_id = 0

        if leecher_count > 0:
            initial_chunks = generate_initial_chunks(
                peer_count=leecher_count,
                total_chunks=service.total_chunks,
                probability=initial_chunk_probability,
                seed=seed,
            )

            for offset, chunk_ids in enumerate(initial_chunks):
                service.add_peer_with_chunks(
                    peer_id=start_peer_id + offset,
                    chunk_ids=chunk_ids,
                )

        return service

    @property
    def total_chunks(self) -> int:
        return len(self.chunks)

    @property
    def all_chunk_ids(self) -> set[int]:
        return set(self._chunk_by_id.keys())

    def _require_chunk(self, chunk_id: int) -> Chunk:
        try:
            return self._chunk_by_id[chunk_id]
        except KeyError as exc:
            raise KeyError(f"Chunk {chunk_id} does not exist") from exc

    def _require_peer(self, peer_id: int) -> Peer:
        try:
            return self.peers[peer_id]
        except KeyError as exc:
            raise KeyError(f"Peer {peer_id} does not exist") from exc

    def _validate_chunk_ids(self, chunk_ids: Iterable[int]) -> list[int]:
        valid_chunk_ids: list[int] = []

        for chunk_id in chunk_ids:
            self._require_chunk(chunk_id)
            valid_chunk_ids.append(chunk_id)

        return valid_chunk_ids

    def add_peer(self, peer: Peer) -> Peer:
        """Thêm một Peer đã tạo sẵn vào swarm."""

        if peer.id in self.peers:
            raise ValueError(f"Peer {peer.id} already exists")

        invalid_chunks = peer.chunk_ids - self.all_chunk_ids
        if invalid_chunks:
            raise ValueError(f"Peer {peer.id} has invalid chunks: {sorted(invalid_chunks)}")

        self.peers[peer.id] = peer
        return peer

    def add_peer_with_chunks(
        self,
        peer_id: int,
        chunk_ids: Iterable[int] = (),
        download_bandwidth_kbps: float = 512.0,
        upload_bandwidth_kbps: float = 512.0,
        latency_ms: float = 50.0,
        max_download_slots: int = 1,
        max_upload_slots: int = 3,
    ) -> Peer:
        """Tạo peer mới và gán danh sách chunk ban đầu."""

        valid_chunk_ids = self._validate_chunk_ids(chunk_ids)
        chunks = [self._chunk_by_id[chunk_id] for chunk_id in valid_chunk_ids]

        peer = Peer.with_chunks(
            id=peer_id,
            chunks=chunks,
            download_bandwidth_kbps=download_bandwidth_kbps,
            upload_bandwidth_kbps=upload_bandwidth_kbps,
            latency_ms=latency_ms,
            max_download_slots=max_download_slots,
            max_upload_slots=max_upload_slots,
        )

        return self.add_peer(peer)

    def add_seeder(self, peer_id: int, **peer_options) -> Peer:
        """Tạo peer có đầy đủ toàn bộ chunk."""

        return self.add_peer_with_chunks(
            peer_id=peer_id,
            chunk_ids=self.all_chunk_ids,
            **peer_options,
        )

    def add_leecher(self, peer_id: int, initial_chunk_ids: Iterable[int] = (), **peer_options) -> Peer:
        """Tạo peer tải xuống, ban đầu có thể chưa có chunk nào hoặc có một phần chunk."""

        return self.add_peer_with_chunks(
            peer_id=peer_id,
            chunk_ids=initial_chunk_ids,
            **peer_options,
        )

    def remove_peer(self, peer_id: int) -> Peer:
        """
        Xóa peer khỏi swarm.

        Chỉ cho phép xóa peer khi peer không có phiên upload/download đang chạy.
        """

        peer = self._require_peer(peer_id)

        if peer.active_downloads or peer.active_uploads:
            raise RuntimeError(f"Peer {peer_id} still has active transfers")

        return self.peers.pop(peer_id)

    def set_peer_online(self, peer_id: int, is_online: bool) -> None:
        peer = self._require_peer(peer_id)
        peer.is_online = is_online

    def get_peer(self, peer_id: int) -> Peer:
        return self._require_peer(peer_id)

    def get_peers(self) -> list[Peer]:
        return [self.peers[peer_id] for peer_id in sorted(self.peers)]

    def get_chunk_availability(self) -> dict[int, list[int]]:
        """Trả về chunk_id -> danh sách peer_id đang giữ chunk đó."""

        availability: dict[int, list[int]] = {chunk.id: [] for chunk in self.chunks}

        for peer in self.get_peers():
            for chunk_id in peer.chunk_ids:
                if chunk_id in availability:
                    availability[chunk_id].append(peer.id)

        for peer_ids in availability.values():
            peer_ids.sort()

        return availability

    def get_chunk_replication_count(self) -> dict[int, int]:
        return {
            chunk_id: len(peer_ids)
            for chunk_id, peer_ids in self.get_chunk_availability().items()
        }

    def find_source_peers(self, downloader_id: int, chunk_id: int) -> list[Peer]:
        downloader = self._require_peer(downloader_id)
        self._require_chunk(chunk_id)

        return [
            peer
            for peer in self.get_peers()
            if peer.can_upload_to(downloader=downloader, chunk_id=chunk_id)
        ]

    def select_next_download(self, downloader_id: int) -> tuple[Optional[int], Optional[Peer]]:
        """
        Chọn chunk tiếp theo và peer nguồn cho downloader.

        Trả về (None, None) nếu không tìm được phiên tải hợp lệ.
        """

        downloader = self._require_peer(downloader_id)

        chunk_id = self.chunk_strategy.select_chunk(
            downloader=downloader,
            all_chunks=self.chunks,
            peers=self.get_peers(),
        )

        if chunk_id is None:
            return None, None

        source_peer = self.source_peer_strategy.select_source_peer(
            downloader=downloader,
            chunk_id=chunk_id,
            peers=self.get_peers(),
        )

        if source_peer is None:
            return None, None

        return chunk_id, source_peer

    def start_next_download(self, downloader_id: int) -> Optional[TransferSession]:
        """
        Bắt đầu một phiên download cho peer nếu có thể.

        Hàm chỉ bắt đầu và khóa slot. Muốn nhận chunk thật sự cần gọi finish_download().
        """

        downloader = self._require_peer(downloader_id)
        chunk_id, source_peer = self.select_next_download(downloader_id)

        if chunk_id is None or source_peer is None:
            return None

        chunk = self._require_chunk(chunk_id)
        downloader.start_download_from(source_peer=source_peer, chunk_id=chunk_id)

        session = TransferSession(
            step=self.current_step,
            downloader_id=downloader.id,
            source_peer_id=source_peer.id,
            chunk_id=chunk_id,
            estimated_seconds=downloader.estimate_download_time(source_peer, chunk),
        )

        self.active_sessions[(downloader.id, chunk_id)] = session
        self.events.append(
            TransferEvent(
                step=self.current_step,
                event_type="download_started",
                downloader_id=downloader.id,
                source_peer_id=source_peer.id,
                chunk_id=chunk_id,
                estimated_seconds=session.estimated_seconds,
            )
        )

        return session

    def start_downloads_for_peer(self, downloader_id: int) -> list[TransferSession]:
        """Bắt đầu nhiều phiên tải cho một peer cho đến khi hết download slot hoặc không còn nguồn."""

        downloader = self._require_peer(downloader_id)
        sessions: list[TransferSession] = []

        while downloader.has_free_download_slot():
            session = self.start_next_download(downloader_id)
            if session is None:
                break
            sessions.append(session)

        return sessions

    def start_round(self) -> list[TransferSession]:
        """
        Tạo một round scheduling.

        Mỗi peer online, chưa hoàn tất file, sẽ được thử cấp download slot.
        """

        self.current_step += 1
        sessions: list[TransferSession] = []

        for peer in self.get_peers():
            if not peer.is_online:
                continue

            if peer.is_complete(self.chunks):
                continue

            sessions.extend(self.start_downloads_for_peer(peer.id))

        if not sessions:
            self.events.append(
                TransferEvent(
                    step=self.current_step,
                    event_type="round_stalled",
                    message="No valid download session can be started",
                )
            )

        return sessions

    def finish_download(
        self,
        downloader_id: int,
        chunk_id: int,
        success: bool = True,
    ) -> TransferSession:
        """
        Kết thúc một phiên download đang chạy.

        Nếu success=True, downloader nhận chunk từ source peer.
        Nếu success=False, chỉ giải phóng slot.
        """

        downloader = self._require_peer(downloader_id)
        self._require_chunk(chunk_id)

        session_key = (downloader_id, chunk_id)
        session = self.active_sessions.get(session_key)

        if session is None:
            raise RuntimeError(f"No active download for peer {downloader_id}, chunk {chunk_id}")

        source_peer = self._require_peer(session.source_peer_id)
        downloader.finish_download_from(
            source_peer=source_peer,
            chunk_id=chunk_id,
            success=success,
        )

        self.active_sessions.pop(session_key, None)
        self.events.append(
            TransferEvent(
                step=self.current_step,
                event_type="download_finished" if success else "download_failed",
                downloader_id=downloader_id,
                source_peer_id=source_peer.id,
                chunk_id=chunk_id,
                estimated_seconds=session.estimated_seconds,
                success=success,
            )
        )

        return session

    def finish_all_active_downloads(self, success: bool = True) -> list[TransferSession]:
        sessions = list(self.active_sessions.values())
        finished_sessions: list[TransferSession] = []

        for session in sessions:
            finished_sessions.append(
                self.finish_download(
                    downloader_id=session.downloader_id,
                    chunk_id=session.chunk_id,
                    success=success,
                )
            )

        return finished_sessions

    def download_one_chunk(self, downloader_id: int) -> Optional[TransferSession]:
        """Helper đồng bộ: start rồi finish ngay một chunk."""

        session = self.start_next_download(downloader_id)
        if session is None:
            return None

        self.finish_download(
            downloader_id=session.downloader_id,
            chunk_id=session.chunk_id,
            success=True,
        )

        return session

    def run_round(self, finish_immediately: bool = True) -> dict:
        """Chạy một round. Mặc định hoàn tất ngay các phiên để mô phỏng đơn giản."""

        before_completed_chunks = self.total_owned_valid_chunks()
        started = self.start_round()
        finished: list[TransferSession] = []

        if finish_immediately:
            finished = self.finish_all_active_downloads(success=True)

        after_completed_chunks = self.total_owned_valid_chunks()

        return {
            "step": self.current_step,
            "started": [session.to_dict() for session in started],
            "finished": [session.to_dict() for session in finished],
            "new_chunks": after_completed_chunks - before_completed_chunks,
            "is_complete": self.is_complete(),
        }

    def simulate_until_complete(
        self,
        max_rounds: int = 100,
        finish_immediately: bool = True,
    ) -> dict:
        """
        Chạy mô phỏng cho đến khi tất cả peer có đủ chunk, bị kẹt, hoặc hết max_rounds.
        """

        if max_rounds <= 0:
            raise ValueError("max_rounds must be greater than 0")

        rounds: list[dict] = []
        status = "max_rounds_reached"

        for _ in range(max_rounds):
            if self.is_complete():
                status = "completed"
                break

            round_result = self.run_round(finish_immediately=finish_immediately)
            rounds.append(round_result)

            if self.is_complete():
                status = "completed"
                break

            if round_result["new_chunks"] == 0 and not self.active_sessions:
                status = "stalled"
                break

        if self.is_complete():
            status = "completed"

        return {
            "status": status,
            "round_count": len(rounds),
            "current_step": self.current_step,
            "is_complete": self.is_complete(),
            "rounds": rounds,
            "summary": self.get_summary(),
        }

    def total_owned_valid_chunks(self) -> int:
        """Tổng số chunk hợp lệ mà tất cả peer đang giữ, dùng để đo tiến triển."""

        return sum(len(peer.chunk_ids & self.all_chunk_ids) for peer in self.get_peers())

    def is_complete(self, peer_ids: Optional[Iterable[int]] = None) -> bool:
        """Kiểm tra các peer chỉ định, hoặc toàn bộ swarm, đã đủ file chưa."""

        if peer_ids is None:
            peers = self.get_peers()
        else:
            peers = [self._require_peer(peer_id) for peer_id in peer_ids]

        if not peers:
            return False

        return all(peer.is_complete(self.chunks) for peer in peers)

    def get_summary(self) -> dict:
        completion_values = [
            peer.completion_percentage(self.chunks)
            for peer in self.get_peers()
        ]

        average_completion = (
            round(sum(completion_values) / len(completion_values), 2)
            if completion_values
            else 0.0
        )

        return {
            "file_size_kb": self.file_size_kb,
            "chunk_size_kb": self.chunk_size_kb,
            "total_chunks": self.total_chunks,
            "peer_count": len(self.peers),
            "completed_peer_count": sum(
                1 for peer in self.get_peers() if peer.is_complete(self.chunks)
            ),
            "average_completion_percentage": average_completion,
            "active_download_count": len(self.active_sessions),
            "strategy": {
                "chunk_selection": self.chunk_strategy.name,
                "source_peer_selection": self.source_peer_strategy.name,
            },
        }

    def get_status(self) -> dict:
        """Trả về toàn bộ trạng thái swarm ở dạng dict, thuận tiện cho API/CLI/UI."""

        return {
            "summary": self.get_summary(),
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "chunk_availability": self.get_chunk_availability(),
            "chunk_replication_count": self.get_chunk_replication_count(),
            "peers": [peer.to_dict(self.chunks) for peer in self.get_peers()],
            "active_sessions": [
                session.to_dict()
                for session in self.active_sessions.values()
            ],
            "events": [event.to_dict() for event in self.events],
        }
