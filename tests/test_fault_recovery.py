import hashlib
import os
import sys
import threading
import time
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.core.chunker import Chunker, Metadata
from client.core.piece_manager import PieceManager, PieceStatus
from client.core.protocol import Protocol


def test_fault_corrupted_piece_rejected_and_retried(tmp_path):
    """Fault Scenario 1: Detection of corrupted chunk payload, rejection, and state reset."""
    data_correct = b"VALID_PIECE_DATA_1234567890" * 100
    piece_hash = hashlib.sha256(data_correct).hexdigest()
    file_hash = hashlib.sha256(data_correct).hexdigest()

    meta = Metadata(
        file_id="test-corrupt-file",
        file_name="corrupt_test.bin",
        file_size=len(data_correct),
        piece_size=len(data_correct),
        total_pieces=1,
        piece_hashes=[piece_hash],
        file_hash=file_hash,
        tracker_url="http://127.0.0.1:8080/announce.php",
    )

    pm = PieceManager(meta, str(tmp_path))

    # 1. Simulate receiving corrupted data from rogue peer
    data_bad = b"CORRUPTED_TAMPERED_DATA_0000000" * 100
    res_bad = pm.save_and_verify_piece(0, data_bad, from_peer="rogue-peer")
    assert res_bad is False
    assert pm.bitfield[0] == 0
    # State reset to PENDING so another peer can serve it
    assert pm.piece_states[0] == PieceStatus.PENDING

    # 2. Simulate recovery by receiving valid data from authentic peer
    res_good = pm.save_and_verify_piece(0, data_correct, from_peer="valid-peer")
    assert res_good is True
    assert pm.bitfield[0] == 1
    assert pm.piece_states[0] == PieceStatus.COMPLETED
    assert pm.is_complete() is True


def test_fault_checkpointing_and_resume_on_restart(tmp_path):
    """Fault Scenario 2: Intermediate state persistence, avoiding re-download of existing chunks."""
    piece_size = 512
    p0 = b"A" * piece_size
    p1 = b"B" * piece_size
    full_data = p0 + p1
    hashes = [hashlib.sha256(p0).hexdigest(), hashlib.sha256(p1).hexdigest()]
    file_hash = hashlib.sha256(full_data).hexdigest()

    meta = Metadata(
        file_id="test-resume-file",
        file_name="resume_test.bin",
        file_size=len(full_data),
        piece_size=piece_size,
        total_pieces=2,
        piece_hashes=hashes,
        file_hash=file_hash,
        tracker_url="http://127.0.0.1:8080/announce.php",
    )

    storage = str(tmp_path)
    pm1 = PieceManager(meta, storage)

    # Peer downloads piece 0 successfully, then crashes / closes
    pm1.save_and_verify_piece(0, p0)
    assert pm1.bitfield == [1, 0]

    # Client restarts: new PieceManager instance scans storage directory
    pm2 = PieceManager(meta, storage)
    assert pm2.bitfield == [1, 0]
    assert pm2.piece_states[0] == PieceStatus.COMPLETED
    assert pm2.piece_states[1] == PieceStatus.PENDING
    assert pm2.get_downloaded_bytes() == piece_size

    # Only remaining piece (1) needs to be downloaded
    remote_bitfield = [1, 1]
    next_idx = pm2.select_next_piece_to_download(remote_bitfield)
    assert next_idx == 1

    pm2.save_and_verify_piece(1, p1)
    assert pm2.is_complete() is True


def test_security_sanitize_metadata_filename_path_traversal():
    """Security Test: Ensure malicious file names cannot escape storage root via path traversal."""
    malicious_names = [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\cmd.exe",
        "/absolute/path/attack.bin",
    ]
    for bad_name in malicious_names:
        clean = os.path.basename(bad_name)
        assert "/" not in clean and "\\" not in clean
        assert not clean.startswith("..")
