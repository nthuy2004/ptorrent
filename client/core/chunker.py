import os
import math
import json
import hashlib
from typing import List, Dict, Optional

from utils.log import logger

DEFAULT_PIECE_SIZE = 256 * 1024


class CreateMetadataParameter:
    def __init__(self, file_path, tracker_url, piece_size=DEFAULT_PIECE_SIZE):
        self.file_path = file_path
        self.tracker_url = tracker_url
        self.piece_size = piece_size
        pass


class Chunker:
    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        hasher = hashlib.sha256()
        hasher.update(data)
        return hasher.hexdigest()

    @staticmethod
    def calculate_file_sha256(file_path: str, buffer_size: int = 64 * 1024) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(buffer_size):
                hasher.update(chunk)
        return hasher.hexdigest()

    def create_metadata(self, file_path: str, tracker_url: str, piece_size: int = DEFAULT_PIECE_SIZE, saved_metadata_path: Optional[str] = None):
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)

        total_pieces = math.ceil(
            file_size / piece_size) if file_size > 0 else 1

        piece_hashes: List[str] = []

        with open(file_path, "rb") as f:
            for _ in range(total_pieces):
                piece_data = f.read(piece_size)
                piece_hashes.append(self.calculate_sha256(piece_data))

        file_hash = self.calculate_file_sha256(file_path)

        metadata = {
            "file_id": file_hash,
            "file_name": file_name,
            "file_size": file_size,
            "piece_size": piece_size,
            "total_pieces": total_pieces,
            "file_hash": file_hash,
            "piece_hashes": piece_hashes,
            "tracker_url": tracker_url
        }

        if saved_metadata_path:
            os.makedirs(os.path.dirname(
                os.path.abspath(saved_metadata_path)), exist_ok=True)
            with open(saved_metadata_path, "w", encoding="utf-8") as out:
                json.dump(metadata, out, indent=2, ensure_ascii=False)

        return metadata

    def read_piece_by_index(self, file_path: str, piece_index: int, piece_size: int) -> bytes:
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")

        offset = piece_index * piece_size
        with open(file_path, "rb") as f:
            f.seek(offset)
            return f.read(piece_size)

    @classmethod
    def verify_piece(self, piece_data: bytes, expected_hash: str) -> bool:
        actual_hash = self.calculate_sha256(piece_data)
        return actual_hash.lower() == expected_hash.lower()

    @classmethod
    def merge_pieces(
        self,
        pieces_dict: Dict[int, bytes],
        output_file_path: str,
        expected_file_hash: Optional[str] = None
    ) -> bool:
        os.makedirs(os.path.dirname(
            os.path.abspath(output_file_path)), exist_ok=True)
        sorted_indices = sorted(pieces_dict.keys())

        with open(output_file_path, "wb") as out:
            for idx in sorted_indices:
                out.write(pieces_dict[idx])

        if expected_file_hash:
            actual_final_hash = self.calculate_file_sha256(output_file_path)
            if actual_final_hash.lower() != expected_file_hash.lower():
                logger.e(
                    f"Hash mismatched! Expected: {expected_file_hash}, Got: {actual_final_hash}")
                return False

        return True
