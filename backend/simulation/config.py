from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil
from typing import Any, Mapping

#  thêm các options cho neighbor graph
# thêm các chuẩn hóa 
@dataclass(slots=True)
class SimulationConfig:


    file_size_mb: int = 10 
    chunk_size_kb: int = 256
    peer_count: int = 10
    seed: int = 1
    initial_chunk_probability: float = 0.3
    initial_distribution_mode: str = "balancedRandom"
    topology_mode: str = "fullMesh"
    neighbors_per_peer: int = 4
    topology_rewire_probability: float = 0.15
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

    def validate(self) -> None:
        if self.file_size_mb <= 0:
            raise ValueError("file_size_mb must be > 0")
        if self.chunk_size_kb <= 0:
            raise ValueError("chunk_size_kb must be > 0")
        if self.peer_count <= 1:
            raise ValueError("peer_count must be > 1")
        if not 0 < self.initial_chunk_probability < 1:
            raise ValueError("initial_chunk_probability must be between 0 and 1")
        if self.initial_distribution_mode not in {"balancedRandom", "singleSeeder"}:
            raise ValueError("initial_distribution_mode must be one of: balancedRandom, singleSeeder")
        if self.topology_mode not in {"fullMesh", "randomK", "ring", "smallWorld", "star", "custom"}:
            raise ValueError("topology_mode must be one of: fullMesh, randomK, ring, smallWorld, star, custom")
        if self.neighbors_per_peer <= 0:
            raise ValueError("neighbors_per_peer must be > 0")
        if not 0 <= self.topology_rewire_probability <= 1:
            raise ValueError("topology_rewire_probability must be between 0 and 1")
        if self.bandwidth_kbps <= 0:
            raise ValueError("bandwidth_kbps must be > 0")
        if self.effective_upload_bandwidth_kbps <= 0:
            raise ValueError("upload_bandwidth_kbps must be > 0")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")
        if self.max_download_slots <= 0:
            raise ValueError("max_download_slots must be > 0")
        if self.max_upload_slots <= 0:
            raise ValueError("max_upload_slots must be > 0")
        if self.transfer_tick_duration <= 0:
            raise ValueError("transfer_tick_duration must be > 0")
        if self.polling_interval <= 0:
            raise ValueError("polling_interval must be > 0")
        if self.max_virtual_time <= 0:
            raise ValueError("max_virtual_time must be > 0")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "fileSizeKb": self.file_size_kb,
                "totalChunks": self.total_chunks,
                "downloadBandwidthKbps": self.bandwidth_kbps,
                "uploadBandwidthKbps": self.effective_upload_bandwidth_kbps,
                "download_bandwidth": self.bandwidth_kbps,
                "upload_bandwidth": self.effective_upload_bandwidth_kbps,
                "initialDistributionMode": self.initial_distribution_mode,
                "topologyMode": self.topology_mode,
                "neighborsPerPeer": self.neighbors_per_peer,
                "topologyRewireProbability": self.topology_rewire_probability,
                "effectiveUploadBandwidthKbps": self.effective_upload_bandwidth_kbps,
                "bandwidthUnit": "KB/s",
                "timeUnit": "seconds",
            }
        )
        return data

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "SimulationConfig":
        payload = dict(payload or {})
        defaults = cls()

        def pick(*names: str, default: Any = None) -> Any:
            for name in names:
                if name in payload and payload[name] is not None:
                    return payload[name]
            return default

        def normalize_initial_distribution_mode(value: Any) -> str:
            normalized = str(value or "").replace("-", "").replace("_", "").lower()
            mapping = {
                "balanced": "balancedRandom",
                "balancedrandom": "balancedRandom",
                "random": "balancedRandom",
                "randompeer": "balancedRandom",
                "single": "singleSeeder",
                "singleseeder": "singleSeeder",
                "seeder": "singleSeeder",
                "seedpeer": "singleSeeder",
                "peer0": "singleSeeder",
                "peer0seeder": "singleSeeder",
            }
            if normalized not in mapping:
                raise ValueError("initialDistributionMode must be one of: balancedRandom, singleSeeder")
            return mapping[normalized]

        def normalize_topology_mode(value: Any) -> str:
            normalized = str(value or "").replace("-", "").replace("_", "").lower()
            mapping = {
                "full": "fullMesh",
                "fullmesh": "fullMesh",
                "mesh": "fullMesh",
                "random": "randomK",
                "randomk": "randomK",
                "ring": "ring",
                "smallworld": "smallWorld",
                "wattsstrogatz": "smallWorld",
                "star": "star",
                "hub": "star",
                "hubspoke": "star",
                "custom": "custom",
            }
            if normalized not in mapping:
                raise ValueError("topologyMode must be one of: fullMesh, randomK, ring, smallWorld, star, custom")
            return mapping[normalized]

        config = cls(
            file_size_mb=int(pick("fileSizeMb", "file_size_mb", default=defaults.file_size_mb)),
            chunk_size_kb=int(pick("chunkSizeKb", "chunk_size_kb", default=defaults.chunk_size_kb)),
            peer_count=int(pick("peerCount", "peer_count", default=defaults.peer_count)),
            seed=int(pick("seed", default=defaults.seed)),
            initial_chunk_probability=float(
                pick(
                    "initialChunkProbability",
                    "initial_chunk_probability",
                    default=defaults.initial_chunk_probability,
                )
            ),
            initial_distribution_mode=normalize_initial_distribution_mode(
                pick(
                    "initialDistributionMode",
                    "initial_distribution_mode",
                    default=defaults.initial_distribution_mode,
                )
            ),
            topology_mode=normalize_topology_mode(
                pick("topologyMode", "topology_mode", default=defaults.topology_mode)
            ),
            neighbors_per_peer=int(
                pick("neighborsPerPeer", "neighbors_per_peer", default=defaults.neighbors_per_peer)
            ),
            topology_rewire_probability=float(
                pick(
                    "topologyRewireProbability",
                    "topology_rewire_probability",
                    default=defaults.topology_rewire_probability,
                )
            ),
            bandwidth_kbps=float(
                pick(
                    "downloadBandwidth",
                    "downloadBandwidthKbps",
                    "download_bandwidth",
                    "download_bandwidth_kbps",
                    "dowloadBandwidth",
                    "dowload_bandwidth",
                    "bandwidth",
                    "bandwidthKbps",
                    "bandwidth_kbps",
                    default=defaults.bandwidth_kbps,
                )
            ),
            upload_bandwidth_kbps=(
                None
                if pick(
                    "uploadBandwidth",
                    "uploadBandwidthKbps",
                    "upload_bandwidth",
                    "upload_bandwidth_kbps",
                    default=None,
                )
                is None
                else float(
                    pick(
                        "uploadBandwidth",
                        "uploadBandwidthKbps",
                        "upload_bandwidth",
                        "upload_bandwidth_kbps",
                        default=defaults.effective_upload_bandwidth_kbps,
                    )
                )
            ),
            latency_ms=float(pick("latency", "latencyMs", "latency_ms", default=defaults.latency_ms)),
            max_download_slots=int(
                pick("maxDownloadSlots", "max_download_slots", default=defaults.max_download_slots)
            ),
            max_upload_slots=int(pick("maxUploadSlots", "max_upload_slots", default=defaults.max_upload_slots)),
            transfer_tick_duration=float(
                pick(
                    "transferTickDuration",
                    "tickDuration",
                    "transfer_tick_duration",
                    default=defaults.transfer_tick_duration,
                )
            ),
            polling_interval=float(pick("pollingInterval", "polling_interval", default=defaults.polling_interval)),
            max_virtual_time=float(pick("maxVirtualTime", "max_virtual_time", default=defaults.max_virtual_time)),
        )
        config.validate()
        return config
