from __future__ import annotations

import random
from collections.abc import Generator
from typing import Any

from .config import SimulationConfig
from .initial_state import clone_initial_state, generate_initial_state
from .models import Peer, TransferRecord
from .network import NetworkModel
from .simpy_compat import Environment
from .strategies import build_strategy


class BitTorrentSimulator:
    """Event-based virtual-time simulator for BitTorrent-style chunk exchange.

    Each peer is a SimPy process that sleeps on a global swarm event. Transfers
    reserve upload/download slots immediately, then move data in short ticks so
    bandwidth is recalculated from the current active upload/download counts.
    """

    def __init__(
        self,
        config: SimulationConfig | None = None,
        strategy: str = "randomFirst",
        initial_state: list[list[int]] | list[set[int]] | None = None,
        churn_events: list[dict[str, Any]] | None = None,
    ) -> None:
        self.config = config or SimulationConfig()
        self.config.validate()
        self.strategy_key = strategy
        self.rng = random.Random(self.config.seed)
        self.initial_state = clone_initial_state(initial_state) if initial_state is not None else generate_initial_state(self.config)
        self.env = Environment()
        self.network = NetworkModel(self.config)
        self.strategy = build_strategy(strategy, self.rng, self.network)
        self.churn_events = self._normalize_churn_events(churn_events or [])
        # Global event dung de danh thuc tat ca peer khi swarm co thay doi quan trong:
        # chunk moi xuat hien hoac slot/bandwidth duoc giai phong sau khi transfer ket thuc.
        self.swarm_event = self.env.event()

        self.peers = self._build_peers(self.initial_state)
        self.logs: list[dict[str, Any]] = []
        self.transfer_records: list[TransferRecord] = []
        self.active_transfers: dict[int, tuple[Peer, Peer, int, float, float]] = {}
        self.cancelled_transfers: set[int] = set()
        self.progress_timeline: list[dict[str, Any]] = []
        self.transfer_counter = 0
        self.completed = False
        self.total_completion_time: float | None = None

    def _build_peers(self, initial_state: list[list[int]]) -> list[Peer]:
        peers: list[Peer] = []
        for peer_id in range(self.config.peer_count):
            chunks = set(initial_state[peer_id]) if peer_id < len(initial_state) else set()
            peers.append(
                Peer(
                    id=peer_id,
                    online=True,
                    owned_chunks=chunks,
                    download_bandwidth_kbps=self.config.bandwidth_kbps,
                    upload_bandwidth_kbps=self.config.effective_upload_bandwidth_kbps,
                    latency_ms=self.config.latency_ms,
                    max_download_slots=self.config.max_download_slots,
                    max_upload_slots=self.config.max_upload_slots,
                )
            )
        return peers

    def _normalize_churn_events(self, churn_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for event in churn_events:
            peer_id = int(event.get("peerId", event.get("peer_id", -1)))
            if peer_id < 0 or peer_id >= self.config.peer_count:
                raise ValueError(f"churn peerId must be between 0 and {self.config.peer_count - 1}")

            raw_online = event.get("online")
            if raw_online is None:
                action = str(event.get("action", "offline")).lower()
                online = action in {"online", "on", "join", "up", "true"}
            else:
                online = bool(raw_online)

            normalized.append(
                {
                    "time": max(float(event.get("time", 0.0)), 0.0),
                    "peerId": peer_id,
                    "online": online,
                }
            )
        return sorted(normalized, key=lambda item: (item["time"], item["peerId"], item["online"]))

    def all_complete(self) -> bool:
        online_peers = [peer for peer in self.peers if peer.online]
        return bool(online_peers) and all(peer.is_complete(self.config.total_chunks) for peer in online_peers)

    def chunk_availability(self) -> dict[int, int]:
        return {
            chunk_id: sum(1 for peer in self.peers if peer.online and peer.has_chunk(chunk_id))
            for chunk_id in range(self.config.total_chunks)
        }

    # tạo ra các snapshot để hiển thị tiến trình
    def _progress_snapshot(self) -> dict[str, Any]:
        peer_snapshots = [peer.to_dict(self.config.total_chunks) for peer in self.peers]
        average = round(sum(peer["completion"] for peer in peer_snapshots) / len(peer_snapshots), 2)
        return {
            "time": round(float(self.env.now), 6),
            "averageCompletion": average,
            "completedPeers": sum(1 for peer in self.peers if peer.online and peer.is_complete(self.config.total_chunks)),
            "onlinePeers": sum(1 for peer in self.peers if peer.online),
            "peers": peer_snapshots, 
        }
  
    def _record_progress(self) -> None:  
        snapshot = self._progress_snapshot()
        # kiểm tra timeline đang rỗng hoặc không duplicate với timeline cuối thì thêm vào lịch sử.
        if not self.progress_timeline or self.progress_timeline[-1] != snapshot:
            self.progress_timeline.append(snapshot)

    # flush event khi hệ thống có thay đổi, đánh thức các peer đang ngủ hoạt động lấy chunk tiếp.
    def _wake_swarm(self) -> None:

        # đẩm bảo các event chưa được đánh dấu trigger(chưa được kích hoạt)
        # nếu đã triggered mà đánh dấu succeed lần nữa sẽ lỗi 
        if not self.swarm_event.triggered: 
            # SimPy Event chi succeed mot lan, nen sau khi flush phai tao event moi
            # de cac peer co the tiep tuc ngu cho lan thay doi tiep theo.
            self.swarm_event.succeed()
        self.swarm_event = self.env.event()

    def _log_event(
        self,
        *,
        event: str,
        transfer_id: int,
        source: Peer,
        destination: Peer,
        chunk_id: int,
        start_time: float,
        duration: float,
        bandwidth: float,
        latency_ms: float,
    ) -> None:
        current_time = float(self.env.now)
        self.logs.append(
            {
                "transferId": transfer_id,
                "event": event,
                "time": round(current_time, 6),
                "timestamp": round(current_time, 6),
                "sourcePeer": source.id,
                "destinationPeer": destination.id,
                "chunkId": chunk_id,
                "startTime": round(start_time, 6),
                "endTime": round(start_time + duration, 6) if event == "START" else round(current_time, 6),
                "duration": round(duration, 6),
                "bandwidthKbps": round(bandwidth, 6),
                "latencyMs": round(latency_ms, 6),
            }
        )

    # log ra sự kiện churn
    def _log_churn_event(self, peer: Peer, online: bool) -> None:
        current_time = float(self.env.now)
        self.logs.append(
            {
                "transferId": None,
                "event": "CHURN",
                "time": round(current_time, 6),
                "timestamp": round(current_time, 6),
                "sourcePeer": None,
                "destinationPeer": peer.id,
                "chunkId": None,
                "startTime": round(current_time, 6),
                "endTime": round(current_time, 6),
                "duration": 0.0,
                "bandwidthKbps": 0.0,
                "latencyMs": 0.0,
                "peerId": peer.id,
                "online": online,
                "action": "ONLINE" if online else "OFFLINE",
            }
        )

    def _cancel_transfer(self, transfer_id: int, reason: str) -> None:
        transfer = self.active_transfers.pop(transfer_id, None)
        if transfer is None:
            return

        source, destination, chunk_id, start_time, latency_ms = transfer
        self.cancelled_transfers.add(transfer_id)
        if chunk_id in destination.active_downloads and destination.id in source.active_uploads:
            destination.finish_transfer_from(source, chunk_id, success=False)

        self._log_event(
            event="CANCEL",
            transfer_id=transfer_id,
            source=source,
            destination=destination,
            chunk_id=chunk_id,
            start_time=start_time,
            duration=float(self.env.now) - start_time,
            bandwidth=0.0,
            latency_ms=latency_ms,
        )
        self.logs[-1]["reason"] = reason

    # Hủy các transfer hiện đang upload/download bởi peer bị offline
    def _cancel_peer_transfers(self, peer: Peer) -> None:
        transfer_ids = [
            transfer_id
            for transfer_id, (source, destination, _, _, _) in self.active_transfers.items()
            if source.id == peer.id or destination.id == peer.id
        ]
        for transfer_id in transfer_ids:
            self._cancel_transfer(transfer_id, "peer_offline")

    def _apply_churn_event(self, event: dict[str, Any]) -> None:
        peer = self.peers[event["peerId"]]
        online = event["online"]
        # tránh update trùng trạng thái cũ
        if peer.online != online:
            peer.online = online
            if not online:
                self._cancel_peer_transfers(peer)

        self._log_churn_event(peer, online)
        self._record_progress()
        # kiểm tra các peer online đều đã hoàn thành thì xác nhận completed
        if self.all_complete() and not self.completed:
            self.completed = True
            self.total_completion_time = float(self.env.now)
        self._wake_swarm()

    # đăng kí các churn event theo thứ tự thời gian 
    def _churn_process(self) -> Generator[Any, Any, None]:
        for event in self.churn_events:
            delay = event["time"] - float(self.env.now)
            if delay > 0:
                yield self.env.timeout(delay)
            if self.completed:
                break
            self._apply_churn_event(event)

    def _start_transfer(self, destination: Peer, source: Peer, chunk_id: int) -> bool:

        if not destination.can_start_download(chunk_id) or not source.can_upload_to(destination, chunk_id):
            return False

        # Reserve slot ngay lập tức. Vi SimPy xu ly event tuan tu trong cung simulation time,
        # peer tiep theo se thay slot nay da bi chiem va khong schedule trung.
        destination.start_transfer_from(source, chunk_id)
        start_time = float(self.env.now)
        # START log dung bandwidth hien tai de hien thi/uoc luong ban dau.
        # END log se ghi average bandwidth thuc te sau khi tick-based transfer hoan tat.
        bandwidth = self.network.effective_bandwidth(source, destination)
        latency_ms = self.network.effective_latency_ms(source, destination)
        estimated_duration = latency_ms / 1000.0 + self.config.chunk_size_kb / bandwidth
        transfer_id = self.transfer_counter
        self.transfer_counter += 1
        self.active_transfers[transfer_id] = (source, destination, chunk_id, start_time, latency_ms)

        self._log_event(
            event="START",
            transfer_id=transfer_id,
            source=source,
            destination=destination,
            chunk_id=chunk_id,
            start_time=start_time,
            duration=estimated_duration,
            bandwidth=bandwidth,
            latency_ms=latency_ms,
        )

        self.env.process(
            self._transfer_lifecycle(
                transfer_id=transfer_id,
                destination=destination,
                source=source,
                chunk_id=chunk_id,
                start_time=start_time,
                latency_ms=latency_ms,
            )
        )
        return True

    def _transfer_lifecycle(
        self,
        *,
        transfer_id: int,
        destination: Peer,
        source: Peer,
        chunk_id: int,
        start_time: float,
        latency_ms: float,
    ) -> Generator[Any, Any, None]:
        latency_seconds = latency_ms / 1000.0
        if latency_seconds > 0:
            # Latency cố định trước khi payload bắt đầu đi qua link.
            yield self.env.timeout(latency_seconds)
            if transfer_id in self.cancelled_transfers or not source.online or not destination.online:
                return

        remaining_kb = float(self.config.chunk_size_kb)
        payload_time = 0.0
        tick_duration = self.config.transfer_tick_duration

        while remaining_kb > 1e-9:
            if transfer_id in self.cancelled_transfers or not source.online or not destination.online:
                self._cancel_transfer(transfer_id, "peer_offline")
                return
            # Mỗi tick đọc lại active_upload_count/active_download_count nên các transfer
            # mới hoặc vừa kết thúc sẽ làm bandwidth giảm/tăng ngay ở tick kế tiếp.
            bandwidth = self.network.effective_bandwidth(source, destination)
            if bandwidth <= 0:
                raise RuntimeError(
                    f"Non-positive bandwidth during transfer {transfer_id}: "
                    f"{source.id}->{destination.id}, chunk {chunk_id}"
                )

            current_tick = min(tick_duration, remaining_kb / bandwidth)
            # pause process này, các process khác vẫn chạy bình thường.
            yield self.env.timeout(current_tick)
            if transfer_id in self.cancelled_transfers or not source.online or not destination.online:
                return
            # Sau khi simulation time tiến lên current_tick, trừ dung lượng payload vừa truyền.
            remaining_kb = max(0.0, remaining_kb - bandwidth * current_tick)
            payload_time += current_tick

        # Hoan tat transfer: add chunk, release slot, ghi log, roi wake swarm de scheduler
        # tim them co hoi transfer moi voi chunk/slot vua duoc giai phong.
        destination.finish_transfer_from(source, chunk_id, success=True)
        self.active_transfers.pop(transfer_id, None)
        end_time = float(self.env.now)
        duration = end_time - start_time
        average_bandwidth = (
            self.config.chunk_size_kb / payload_time
            if payload_time > 0
            else self.network.effective_bandwidth(source, destination)
        )
        record = TransferRecord(
            transfer_id=transfer_id,
            source_peer=source.id,
            destination_peer=destination.id,
            chunk_id=chunk_id,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            bandwidth_kbps=average_bandwidth,
            latency_ms=latency_ms,
        )
        self.transfer_records.append(record)
        self._log_event(
            event="END",
            transfer_id=transfer_id,
            source=source,
            destination=destination,
            chunk_id=chunk_id,
            start_time=start_time,
            duration=duration,
            bandwidth=average_bandwidth,
            latency_ms=latency_ms,
        )
        self._record_progress()

        if self.all_complete() and not self.completed:
            self.completed = True
            self.total_completion_time = end_time
        self._wake_swarm()

    def _schedule_peer_downloads(self, peer: Peer) -> int:
        scheduled = 0
        # Moi lan peer thuc day, no co gang lap day tat ca download slot dang ranh.
        # Vong lap nay khong polling theo thoi gian; no chi chay khi process duoc wake.
        # Lấp đầy toàn bộ download slot của peer trong một lần thức dậy.
        while (
            not self.completed
            and peer.online
            and not peer.is_complete(self.config.total_chunks)
            and peer.has_free_download_slot()
        ):
            chunk_id = self.strategy.select_chunk(peer, self.peers, self.config.total_chunks)
            if chunk_id is None:
                break

            source = self.strategy.select_source(peer, self.peers, chunk_id)
            if source is None:
                break

            if not self._start_transfer(peer, source, chunk_id):
                break
            scheduled += 1
        return scheduled

    # tiến trình sống lâu dài của mỗi peer
    def _peer_process(self, peer: Peer) -> Generator[Any, Any, None]:
        while not self.completed:
            if peer.online and not peer.is_complete(self.config.total_chunks):
                self._schedule_peer_downloads(peer)

            if self.completed:
                break
            # Peer ngu tai day cho den khi _wake_swarm() flush global event.
            # Khong co busy waiting/thread that, nen ket qua deterministic theo thu tu event SimPy.
            yield self.swarm_event

    def run(self) -> dict[str, Any]:
        self._record_progress()
        if self.all_complete():
            self.completed = True
            self.total_completion_time = 0.0
            return self.to_result()

        if self.churn_events:
            self.env.process(self._churn_process())
        for peer in self.peers:
            self.env.process(self._peer_process(peer))

        self.env.run(until=self.config.max_virtual_time)
        if self.completed and self.total_completion_time is not None:
            # Keep env.now out of the main metric because some fallback environments may
            # drain already scheduled polling events after completion.
            pass
        elif self.all_complete():
            self.completed = True
            self.total_completion_time = float(self.env.now)

        return self.to_result()

    def to_result(self) -> dict[str, Any]:
        total_time = self.total_completion_time if self.total_completion_time is not None else float(self.env.now)
        final_peers = [peer.to_dict(self.config.total_chunks) for peer in self.peers]
        return {
            "strategy": self.strategy.key,
            "strategyName": self.strategy.display_name,
            "status": "completed" if self.completed else "incomplete",
            "completed": self.completed,
            "totalTime": round(total_time, 6),
            "totalTransfers": len(self.transfer_records),
            "logs": self.logs,
            "transfers": [record.to_dict() for record in self.transfer_records],
            "progressTimeline": self.progress_timeline,
            "initialState": clone_initial_state(self.initial_state),
            "finalPeers": final_peers,
            "chunkAvailability": self.chunk_availability(),
            "config": self.config.to_dict(),
            "churnEvents": self.churn_events,
        }
