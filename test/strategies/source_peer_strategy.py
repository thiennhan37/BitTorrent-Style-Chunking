# strategies/source_peer_strategy.py

import random
from typing import Iterable, Optional

from models import Peer


class RandomAvailableSourcePeerStrategy:
    """
    Chiến lược chọn peer nguồn.

    Sau khi đã chọn được chunk cần tải, strategy này chọn ngẫu nhiên
    một peer đang:
        - có chunk đó
        - còn upload slot
        - có thể upload cho downloader
    """

    name = "Random Available Source Peer"

    def select_source_peer(
        self,
        downloader: Peer,
        chunk_id: int,
        peers: Iterable[Peer],
    ) -> Optional[Peer]:
        if not downloader.can_start_download(chunk_id):
            return None

        candidates: list[Peer] = []

        for source_peer in peers:
            if source_peer.id == downloader.id:
                continue

            if source_peer.can_upload_to(
                downloader=downloader,
                chunk_id=chunk_id,
            ):
                candidates.append(source_peer)

        if not candidates:
            return None

        return random.choice(candidates)