# metrics/metrics_collector.py

from collections import defaultdict

class MetricsCollector:
    def __init__(self, total_chunks):
        self.total_chunks = total_chunks

        # self.samples: Lưu trữ thông tin tại các mốc thời gian
        # self.transfer_log: Lưu trữ thông tin chi tiết về các lần truyền chunk
        self.samples = []
        self.transfer_log = []

        # self.total_bytes_transferred: Tổng dung lượng đã truyền
        # self.chunk_transfer_count: Số lần chunk được truyền
        self.total_bytes_transferred = 0
        self.chunk_transfer_count = defaultdict(int)

    def record_transfer(self, time, source, target, chunk_id, bytes_count):
        self.total_bytes_transferred += bytes_count
        self.chunk_transfer_count[chunk_id] += 1

        self.transfer_log.append({
            "time": time,
            "source": source,
            "target": target,
            "chunk_id": chunk_id,
            "bytes": bytes_count
        })

    def sample(self, time, peers):
        # replication: Phân phối số lượng bản sao của từng chunk
        # completion: Tỷ lệ hoàn thành của từng peer
        replication = self.compute_replication_distribution(peers)
        completion = [peer.completion_ratio(self.total_chunks) for peer in peers]

        sample = {
            "time": time,
            "avg_completion": sum(completion) / len(completion),
            "min_completion": min(completion),
            "max_completion": max(completion),
            "replication": replication,
            "avg_replication": sum(replication.values()) / self.total_chunks,
            "available_chunks": sum(1 for count in replication.values() if count > 0),
            "online_peers": sum(1 for peer in peers if peer.online),
            "total_bytes": self.total_bytes_transferred
        }

        self.samples.append(sample)

    def compute_replication_distribution(self, peers):
        # Đếm số lượng bản sao của từng chunk trong hệ thống
        replication = {chunk_id: 0 for chunk_id in range(self.total_chunks)}

        for peer in peers:
            if not peer.online:
                continue

            for chunk_id in peer.chunks:
                replication[chunk_id] += 1

        return replication

    # bottleneck_chunks: Xác định các chunk có tỷ lệ thiếu hụt cao nhất (missing_count / replica_count)
    def bottleneck_chunks(self, peers, top_k=5):
    
        replication = self.compute_replication_distribution(peers)

        scores = []

        for chunk_id in range(self.total_chunks):
            replica_count = replication[chunk_id]
            missing_count = sum(
                1 for peer in peers
                if chunk_id not in peer.chunks
            )

            score = missing_count / max(1, replica_count)

            scores.append((chunk_id, score, replica_count, missing_count))

        scores.sort(key=lambda item: item[1], reverse=True)

        return scores[:top_k]