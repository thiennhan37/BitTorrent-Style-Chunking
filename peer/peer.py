
# upload_bandwidth, download_bandwidth: Mô phỏng tốc độ mạng
# active_uploads, active_downloads: Theo dõi số phiên truyền đang hoạt động.(truyền/nhận cho bao nhiêu peer khác)


class Peer:
    def __init__(self, peer_id, initial_chunks, upload_bandwidth, download_bandwidth):
        self.peer_id = peer_id
        self.chunks = set(initial_chunks)

        self.upload_bandwidth = upload_bandwidth
        self.download_bandwidth = download_bandwidth

        self.online = True
        self.active_uploads = 0
        self.active_downloads = 0

        self.completed_at = None
        self.bytes_uploaded = 0
        self.bytes_downloaded = 0

    def has_chunk(self, chunk_id):
        return chunk_id in self.chunks

    def missing_chunks(self, total_chunks):
        return set(range(total_chunks)) - self.chunks

    def add_chunk(self, chunk_id):
        self.chunks.add(chunk_id)

    # Tính phần trăm hoàn thành file.
    def completion_ratio(self, total_chunks):
        return len(self.chunks) / total_chunks

    def is_complete(self, total_chunks):
        return len(self.chunks) == total_chunks

    # BitTorrent thật giới hạn số kết nối upload để:
    # tránh nghẽn mạng + đảm bảo fairness + tránh quá tải node
    def can_upload(self, max_uploads):
        return self.online and self.active_uploads < max_uploads

    def can_download(self, max_downloads):
        return self.online and self.active_downloads < max_downloads