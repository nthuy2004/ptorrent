"""
Unit Test: Kiểm tra hoạt động của Module Chunker & Hasher
Thực hiện:
  1. Tạo file nhị phân giả lập (1MB)
  2. Tạo metadata và băm SHA-256
  3. Đọc từng chunk ngẫu nhiên bằng seek() và verify hash
  4. Giả lập chunk bị hỏng và kiểm tra xem có phát hiện được không
  5. Ghép lại file và so khớp với file gốc 100%
"""

import os
import sys
import tempfile

# Đảm bảo console Windows in được tiếng Việt UTF-8
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Thêm đường dẫn src vào PYTHONPATH để import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.core.chunker import Chunker


def test_chunker_lifecycle():
    print("=" * 60)
    print("BẮT ĐẦU KIỂM THỬ MODULE CHUNKER & HASHER")
    print("=" * 60)

    # 1. Tạo file dữ liệu mẫu
    temp_dir = tempfile.mkdtemp()
    sample_file = os.path.join(temp_dir, "sample_document.bin")
    file_size = 1024 * 1024 + 12345  # ~1.01 MB (kích thước lẻ để test chunk cuối cùng)
    sample_data = os.urandom(file_size)

    with open(sample_file, "wb") as f:
        f.write(sample_data)

    print(f"[OK] Đã tạo file mẫu kích thước: {file_size} bytes ({file_size / 1024:.2f} KB)")

    # 2. Tạo metadata
    piece_size = 256 * 1024  # 256 KB
    meta_path = os.path.join(temp_dir, "sample.meta.json")
    tracker_url = "http://127.0.0.1:8080/announce.php"

    meta = Chunker.create_metadata(sample_file, tracker_url, piece_size, meta_path)
    total_pieces = meta["total_pieces"]

    print(f"[OK] Metadata được sinh thành công:")
    print(f"     - File ID: {meta['file_id']}")
    print(f"     - Tổng số chunks: {total_pieces}")
    print(f"     - Kích thước mỗi chunk: {piece_size} bytes")

    # 3. Đọc từng chunk và verify hash
    collected_pieces = {}
    for idx in range(total_pieces):
        piece_bytes = Chunker.read_piece_by_index(sample_file, idx, piece_size)
        expected_hash = meta["piece_hashes"][idx]
        is_valid = Chunker.verify_piece(piece_bytes, expected_hash)
        assert is_valid, f"Chunk {idx} bị sai mã hash!"
        collected_pieces[idx] = piece_bytes
        print(f"     -> Chunk #{idx}: {len(piece_bytes)} bytes | Hash: {expected_hash[:16]}... [XÁC THỰC HỢP LỆ]")

    # 4. Kiểm tra khả năng phát hiện chunk bị hỏng
    corrupted_data = bytearray(collected_pieces[0])
    corrupted_data[0] = (corrupted_data[0] + 1) % 256  # Thay đổi cố tình 1 byte
    is_corrupt_detected = not Chunker.verify_piece(bytes(corrupted_data), meta["piece_hashes"][0])
    assert is_corrupt_detected, "Lỗi: Không phát hiện được chunk bị hỏng!"
    print("[OK] Kiểm tra phát hiện lỗi: Đã phát hiện và từ chối chunk bị sửa 1 byte thành công!")

    # 5. Ghép lại file và kiểm tra toàn vẹn
    reconstructed_file = os.path.join(temp_dir, "reconstructed_document.bin")
    merge_success = Chunker.merge_pieces(collected_pieces, reconstructed_file, meta["file_hash"])
    assert merge_success, "Ghép file thất bại!"

    # So sánh bit-by-bit với file gốc
    with open(sample_file, "rb") as f1, open(reconstructed_file, "rb") as f2:
        assert f1.read() == f2.read(), "Dữ liệu sau khi ghép không khớp 100% với dữ liệu gốc!"

    print(f"[OK] Ghép file thành công: {reconstructed_file}")
    print("[SUCCESS] File sau khi ghép trùng khớp 100% với file gốc! TEST PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_chunker_lifecycle()
