# strategies/random_first_strategy.py

import random
from typing import Iterable, Optional

from models import Chunk, Peer
from strategies.chunk_selection_strategy import ChunkSelectionStrategy


class RandomFirstStrategy(ChunkSelectionStrategy):
    """
    Thuật toán Random First.

    Ý tưởng:
        - Lấy danh sách chunk còn thiếu
        - Chỉ giữ lại những chunk đang có peer khác upload được
        - Chọn ngẫu nhiên một chunk
    """

    name = "Random First"

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

        candidate_chunk_ids: list[int] = []

        for chunk_id in downloader.missing_chunk_ids(all_chunks):
            if not downloader.can_start_download(chunk_id):
                continue

            if self.require_available_source:
                has_available_source = any(
                    source_peer.can_upload_to(
                        downloader=downloader,
                        chunk_id=chunk_id,
                    )
                    for source_peer in peers
                )

                if not has_available_source:
                    continue

            candidate_chunk_ids.append(chunk_id)

        if not candidate_chunk_ids:
            return None

        return random.choice(candidate_chunk_ids)