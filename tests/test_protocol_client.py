import socket
import os
import sys
import time
import shutil
import tempfile
import time

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../src")))

from client.core.peer_server import PeerServer
from client.utils.log import logger
from client.core.protocol import Protocol

import struct

HOST = '127.0.0.1'
PORT = 6767

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = (HOST, PORT)
print('connecting to %s port ' + str(server_address))
s.connect(server_address)

try:
    p = Protocol()
    my_payload = p.send_handshake(s, "12345678", "1234546")

    msg_type, payload = Protocol.recv(s)

    a = Protocol.parse_piece(payload)

    print(a)
finally:
    s.close()
