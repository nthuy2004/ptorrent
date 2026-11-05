import os
import socket
import struct
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.core.protocol import Protocol, MAX_BUF_LEN


def test_protocol_handshake():
    s1, s2 = socket.socketpair()
    try:
        Protocol.send_handshake(s1, "file123", "peer456", is_ack=False)
        msg_type, payload = Protocol.recv(s2)
        assert msg_type == Protocol.MSG_HANDSHAKE
        data = Protocol.parse_handshake(payload)
        assert data["file_id"] == "file123"
        assert data["peer_id"] == "peer456"

        Protocol.send_handshake(s2, "file123", "peer789", is_ack=True)
        msg_type, payload = Protocol.recv(s1)
        assert msg_type == Protocol.MSG_HANDSHAKE_OK
        data = Protocol.parse_handshake(payload)
        assert data["peer_id"] == "peer789"
    finally:
        s1.close()
        s2.close()


def test_protocol_bitfield():
    s1, s2 = socket.socketpair()
    try:
        bitfield = [1, 0, 1, 1, 0]
        Protocol.send_bitfield(s1, bitfield)
        msg_type, payload = Protocol.recv(s2)
        assert msg_type == Protocol.MSG_BITFIELD
        assert Protocol.parse_bitfield(payload) == bitfield
    finally:
        s1.close()
        s2.close()


def test_protocol_have():
    s1, s2 = socket.socketpair()
    try:
        Protocol.send_have(s1, 42)
        msg_type, payload = Protocol.recv(s2)
        assert msg_type == Protocol.MSG_HAVE
        assert Protocol.parse_have(payload) == 42
    finally:
        s1.close()
        s2.close()


def test_protocol_request():
    s1, s2 = socket.socketpair()
    try:
        Protocol.send_request(s1, 7)
        msg_type, payload = Protocol.recv(s2)
        assert msg_type == Protocol.MSG_REQUEST
        assert Protocol.parse_request(payload) == 7
    finally:
        s1.close()
        s2.close()


def test_protocol_piece():
    s1, s2 = socket.socketpair()
    try:
        sample_data = b"hello piece data 123456"
        Protocol.send_piece(s1, 3, sample_data)
        msg_type, payload = Protocol.recv(s2)
        assert msg_type == Protocol.MSG_PIECE
        idx, data = Protocol.parse_piece(payload)
        assert idx == 3
        assert data == sample_data
    finally:
        s1.close()
        s2.close()


def test_protocol_error():
    s1, s2 = socket.socketpair()
    try:
        Protocol.send_error(s1, "custom error occurred")
        msg_type, payload = Protocol.recv(s2)
        assert msg_type == Protocol.MSG_ERROR
        assert payload.decode("utf-8") == "custom error occurred"
    finally:
        s1.close()
        s2.close()


def test_protocol_invalid_length():
    s1, s2 = socket.socketpair()
    try:
        invalid_len = MAX_BUF_LEN + 100
        s1.sendall(struct.pack(">I", invalid_len))
        with pytest.raises(ValueError, match="invalid buffer length"):
            Protocol.recv(s2)
    finally:
        s1.close()
        s2.close()


def test_protocol_connection_closed():
    s1, s2 = socket.socketpair()
    s1.close()
    with pytest.raises(ConnectionError):
        Protocol.recv(s2)
    s2.close()
