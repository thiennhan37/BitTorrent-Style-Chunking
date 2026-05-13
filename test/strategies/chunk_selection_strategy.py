# strategies/chunk_selection_strategy.py

from abc import ABC, abstractmethod
from typing import Iterable, Optional

from models import Chunk, Peer


class ChunkSelectionStrategy(ABC):
    """
    Interface chung cho các thuật toán chọn chunk.

    Ví dụ:
        - Random First
        - Rarest First
        - Sequential
        - Priority-based
    """

    name: str

    @abstractmethod
    def select_chunk(
        self,
        downloader: Peer,
        all_chunks: Iterable[Chunk],
        peers: Iterable[Peer],
    ) -> Optional[int]:
        """
        Chọn chunk_id mà downloader nên tải tiếp theo.

        Trả về:
            - chunk_id nếu chọn được
            - None nếu không có chunk nào phù hợp
        """
        pass