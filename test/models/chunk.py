# models/chunk.py

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True, slots=True)
class Chunk:
    """
    Model đại diện cho một mảnh dữ liệu của file.
    """

    id: int
    size_kb: int

    def __post_init__(self) -> None:
        if self.id < 0:
            raise ValueError("Chunk id must be greater than or equal to 0")

        if self.size_kb <= 0:
            raise ValueError("Chunk size must be greater than 0")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "size_kb": self.size_kb,
        }

    @staticmethod
    def split_file(file_size_kb: int, chunk_size_kb: int) -> list["Chunk"]:
        """
        Chia file thành danh sách chunk.
        """

        if file_size_kb <= 0:
            raise ValueError("File size must be greater than 0")

        if chunk_size_kb <= 0:
            raise ValueError("Chunk size must be greater than 0")

        total_chunks = ceil(file_size_kb / chunk_size_kb)
        chunks: list[Chunk] = []

        for chunk_id in range(total_chunks):
            remaining_size = file_size_kb - chunk_id * chunk_size_kb
            current_size = min(chunk_size_kb, remaining_size)

            chunks.append(
                Chunk(
                    id=chunk_id,
                    size_kb=current_size,
                )
            )

        return chunks