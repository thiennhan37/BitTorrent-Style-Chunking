from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil
from typing import Any, Mapping


@dataclass(slots=True)
class SimulationConfig:


    file_size_mb: int = 10
    chunk_size_kb: int = 256
    peer_count: int = 10
    seed: int = 1
    initial_chunk_probability: float = 0.3
    bandwidth_kbps: float = 128.0
    upload_bandwidth_kbps: float | None = 128.0
    latency_ms: float = 50.0
    max_download_slots: int = 2
    max_upload_slots: int = 3
    # Do lon moi buoc mo phong khi truyen chunk.
    # Moi tick se tinh lai bandwidth theo so transfer dang active, nen transfer
    # moi/transfer ket thuc se anh huong den cac transfer con lai o tick ke tiep.
    transfer_tick_duration: float = 0.1
    # Giu lai de tuong thich payload/cu phan UI; scheduler moi khong dung polling lien tuc.
    polling_interval: float = 0.02
    max_virtual_time: float = 20_000.0

    @property
    def file_size_kb(self) -> int:
        return self.file_size_mb * 1024

    @property
    def total_chunks(self) -> int:
        return ceil(self.file_size_kb / self.chunk_size_kb)

    @property
    def effective_upload_bandwidth_kbps(self) -> float:
        return self.bandwidth_kbps if self.upload_bandwidth_kbps is None else self.upload_bandwidth_kbps