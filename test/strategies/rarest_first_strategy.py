# strategies/rarest_first_strategy.py

import random
from typing import Iterable, Optional

from models import Chunk, Peer
from strategies.chunk_selection_strategy import ChunkSelectionStrategy


class RarestFirstStrategy(ChunkSelectionStrategy):
    """
    Thuật toán Rarest First.

    Ý tưởng:
        - Xét các chunk mà downloader còn thiếu
        - Đếm mỗi chunk đang xuất hiện ở bao nhiêu peer khác
        - Chọn chunk có số lượng bản sao ít nhất
        - Nếu nhiều chunk cùng hiếm như nhau thì chọn ngẫu nhiên
    """

    name = "Rarest First"

    def __init__(self, require_available_source: bool = True) -> None:
        self.require_available_source = require_available_source

    def select_chunk(
        self,
        downloader: Peer,
        all_chunks: Iterable[Chunk],
        peers: Iterable[Peer],
    ) -> Optional[int]:
        all_chunks = list(all_chunks)
        peers = list(peers)

        if not downloader.has_free_download_slot():
            return None

        availability: dict[int, int] = {}

        for chunk_id in downloader.missing_chunk_ids(all_chunks):
            if not downloader.can_start_download(chunk_id):
                continue

            source_count = 0

            for source_peer in peers:
                if source_peer.id == downloader.id:
                    continue

                if not source_peer.has_chunk(chunk_id):
                    continue

                if self.require_available_source:
                    if not source_peer.can_upload_to(
                        downloader=downloader,
                        chunk_id=chunk_id,
                    ):
                        continue

                source_count += 1

            if source_count > 0:
                availability[chunk_id] = source_count

        if not availability:
            return None

        minimum_count = min(availability.values())

        rarest_chunk_ids = [
            chunk_id
            for chunk_id, count in availability.items()
            if count == minimum_count
        ]

        return random.choice(rarest_chunk_ids)