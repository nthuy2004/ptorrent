import os
from enum import Enum
from typing import Optional
from client.core.chunker import Metadata, Chunker
import threading
from client.core.bus import bus
class PieceStatus(Enum):
    PENDING = 0
    DOWNLOADING = 1
    COMPLETED = 2
    CORRUPTED = 3

class PieceManager:
    def __init__(self, metadata: Metadata, storage_root: str, original_file_path: Optional[str] = None):
        self.metadata = metadata
        self.file_id = metadata.file_id
        self.file_name = metadata.file_name
        self.file_size = metadata.file_size
        self.piece_size = metadata.piece_size
        self.total_pieces = metadata.total_pieces
        self.piece_hashes = metadata.piece_hashes
        self.file_hash = metadata.file_hash
        self.storage_root = os.path.abspath(storage_root)
        self.original_file_path = os.path.abspath(original_file_path) if original_file_path else None
        #
        self.storage_root = os.path.abspath(storage_root)
        self.chunks_dir = os.path.join(self.storage_root, "chunks", self.file_id)
        self.completed_dir = os.path.join(self.storage_root, "completed")
        self.completed_file_path = os.path.join(self.completed_dir, self.file_name)

        os.makedirs(self.chunks_dir, exist_ok=True)
        os.makedirs(self.completed_dir, exist_ok=True)

        self.bitfield: list[int] = [0] * self.total_pieces
        self.piece_states: list[PieceStatus] = [PieceStatus.PENDING] * self.total_pieces
        self.uploaded_bytes = 0
        self.is_merged = False

        self._lock = threading.Lock()

        self.scan()

    def scan(self):
        for path in [self.original_file_path, self.completed_file_path]:
            if path and os.path.exists(path):
                if os.path.getsize(path) == self.file_size:
                    fhash = Chunker.calculate_file_sha256(path)
                    if fhash.lower() == self.file_hash.lower():
                        self.original_file_path = path
                        self.bitfield = [1] * self.total_pieces
                        self.piece_states = [PieceStatus.COMPLETED] * self.total_pieces
                        self.is_merged = True
                        return

        # khong tim thay file or k co du pieece

        for idx in range(self.total_pieces):
            chunk_path = self.get_chunk_file_path(idx)
            if os.path.exists(chunk_path):
                try:
                    with open(chunk_path, "rb") as f:
                        data = f.read()
                    if Chunker.verify_piece(data, self.piece_hashes[idx]):
                        self.bitfield[idx] = 1
                        self.piece_states[idx] = PieceStatus.COMPLETED
                    else:
                        #trash chunk
                        os.remove(chunk_path)
                except Exception:
                    pass

    def get_chunk_file_path(self, index: int):
        return os.path.join(self.chunks_dir, f"chunk_{index}.dat")

    def get_bitfield(self):
        with self._lock:
            return list(self.bitfield)

    def is_complete(self):
        with self._lock:
            return all(b == 1 for b in self.bitfield)

    def get_downloaded_bytes(self):
        with self._lock:
            total = 0
            for idx, has_piece in enumerate(self.bitfield):
                if has_piece:
                    if idx == self.total_pieces - 1:
                        rem = self.file_size % self.piece_size
                        total += rem if rem != 0 else self.piece_size
                    else:
                        total += self.piece_size
            return min(total, self.file_size)

    def get_bytes_left(self):
        return max(0, self.file_size - self.get_downloaded_bytes())

    def select_next_piece_to_download(self, remote_bitfield: list[int]) -> Optional[int]:
        with self._lock:
            for idx in range(self.total_pieces):
                if (
                    self.bitfield[idx] == 0
                    and self.piece_states[idx] in (PieceStatus.PENDING, PieceStatus.CORRUPTED)
                    and idx < len(remote_bitfield)
                    and remote_bitfield[idx] == 1
                ):
                    self.piece_states[idx] = PieceStatus.DOWNLOADING
                    return idx
            return None

    def switch_piece_to_pending(self, index: int):
        with self._lock:
            if self.bitfield[index] == 0:
                self.piece_states[index] = PieceStatus.PENDING

    def get_piece_data(self, index: int) -> Optional[bytes]:
        with self._lock:
            if index < 0 or index >= self.total_pieces or self.bitfield[index] == 0:
                return None
            filee = self.original_file_path if (self.original_file_path and os.path.exists(self.original_file_path)) else None

        if filee:
            return Chunker.read_piece_by_index(filee, index, self.piece_size)

        chunk_path = self.get_chunk_file_path(index)
        if os.path.exists(chunk_path):
            with open(chunk_path, "rb") as f:
                return f.read()
        return None

    def record_uploaded(self, num_bytes: int):
        with self._lock:
            self.uploaded_bytes += num_bytes

    def save_and_verify_piece(self, index: int, data: bytes, from_peer: str = ""):
        expected_hash = self.piece_hashes[index]
        if not Chunker.verify_piece(data, expected_hash):
            with self._lock:
                self.piece_states[index] = PieceStatus.CORRUPTED
            bus.publish("chunk.corrupted", {
                "file_id": self.file_id,
                "index": index,
                "peer": from_peer
            })
            with self._lock:
                self.piece_states[index] = PieceStatus.PENDING
            return False

        # sace chunk chunk_{index}.dat
        chunk_path = self.get_chunk_file_path(index)
        with open(chunk_path, "wb") as f:
            f.write(data)

        with self._lock:
            self.bitfield[index] = 1
            self.piece_states[index] = PieceStatus.COMPLETED
            current_bitfield = list(self.bitfield)
            all_done = all(b == 1 for b in self.bitfield)
            should_merge = all_done and not self.is_merged
            if should_merge:
                self.is_merged = True

        bus.publish("chunk.completed", {
            "file_id": self.file_id,
            "index": index,
            "size": len(data),
            "peer": from_peer,
            "bitfield": current_bitfield
        })

        if should_merge:
            self.merge_all_chunks()

        return True

    def merge_all_chunks(self):
        pieces_dict: dict[int, bytes] = {}
        for idx in range(self.total_pieces):
            data = self.get_piece_data(idx)
            if data is None:
                return False
            pieces_dict[idx] = data

        ok = Chunker.merge_pieces(pieces_dict, self.completed_file_path, self.file_hash)
        if ok:
            with self._lock:
                self.original_file_path = self.completed_file_path
            bus.publish("file.completed", {
                "file_id": self.file_id,
                "file_name": self.file_name,
                "output_path": self.completed_file_path
            })
        return ok