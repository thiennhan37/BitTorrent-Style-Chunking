from __future__ import annotations

from dataclasses import dataclass

from .config import SimulationConfig
from .models import Peer


@dataclass(slots=True)
class NetworkModel:
    config: SimulationConfig

    def _link_unit(self, source: Peer, destination: Peer, salt: int) -> float:

        # nhân với các số prime để giảm xung đột 
        # kĩ thuật hash giữ lại 32 bit cuối
        value = (
            (self.config.seed + 1) * 1_000_003
            + (source.id + 1) * 91_193
            + (destination.id + 1) * 35_017
            + salt * 7_919
        ) & 0xFFFFFFFF
        value ^= value >> 16
        value = (value * 0x7FEB352D) & 0xFFFFFFFF
        value ^= value >> 15
        value = (value * 0x846CA68B) & 0xFFFFFFFF
        value ^= value >> 16
        return value / 0xFFFFFFFF

    # điều chỉnh 75-100% cho khả năng thực tế của băng thông
    def link_bandwidth_factor(self, source: Peer, destination: Peer) -> float:
        # Directed peer links vary between 75% and 100% of the shared peer capacity.
        # Keeping the factor <= 1 preserves the per-peer bandwidth budget while still
        # making source choice deterministic and network-dependent.
        return 0.75 + self._link_unit(source, destination, salt=1) * 0.25

    # điều chỉnh 100-175% cho độ trễ thực tế
    def effective_latency_ms(self, source: Peer, destination: Peer) -> float:
        base_latency_ms = max(self.config.latency_ms, source.latency_ms, destination.latency_ms)
        return base_latency_ms * self.link_latency_factor(source, destination)
    
    def link_latency_factor(self, source: Peer, destination: Peer) -> float:
        # Directed peer links vary between 100% and 175% of the configured base.
        return 1 + self._link_unit(source, destination, salt=2)

    def shared_upload_bandwidth(self, source: Peer) -> float:
        # Upload cua mot peer duoc chia deu cho tat ca upload dang active.
        # max(..., 1) giup ham van an toan khi duoc goi de uoc luong truoc luc reserve.
        active_uploads = max(source.active_upload_count, 1)
        return source.upload_bandwidth_kbps / active_uploads

    def shared_download_bandwidth(self, destination: Peer) -> float:
        # Download cua mot peer cung duoc chia deu cho cac download dang active.
        # Khi transfer moi bat dau/ket thuc, count nay thay doi va tick ke tiep se thay bandwidth moi.
        active_downloads = max(destination.active_download_count, 1)
        return destination.download_bandwidth_kbps / active_downloads

    def effective_bandwidth(self, source: Peer, destination: Peer) -> float:
        # Bandwidth thuc te cua link bi gioi han boi ca uploader va downloader.
        # link_bandwidth_factor tao khac biet deterministic giua cac cap peer,
        # giup source choice co anh huong nhung van cong bang giua hai strategy.
        shared_bandwidth = min(
            self.shared_upload_bandwidth(source),
            self.shared_download_bandwidth(destination),
        )
        return shared_bandwidth * self.link_bandwidth_factor(source, destination)

    def transfer_time(self, chunk_size_kb: int, source: Peer, destination: Peer) -> tuple[float, float, float]:
        """Return a static estimate for compatibility and tests.

        The simulator no longer relies on this for active transfers. Real transfers
        recalculate ``effective_bandwidth`` every simulation tick.
        """
        bandwidth = self.effective_bandwidth(source, destination)
        latency_ms = self.effective_latency_ms(source, destination)
        duration = latency_ms / 1000.0 + chunk_size_kb / bandwidth
        return duration, bandwidth, latency_ms
