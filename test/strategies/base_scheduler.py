from abc import ABC, abstractmethod

# abc: = Abstract Base Class Dùng để tạo: lớp trừu tượng -> phương thức bắt buộc subclass phải implement
class BaseScheduler(ABC):
    def __init__(self, total_chunks):
        self.total_chunks = total_chunks

    @abstractmethod
    def select_chunk(self, requester, neighbors, all_peers):
        pass