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
    my_payload = struct.pack(">IB", 4, 1)

    hi = my_payload + ("Hel").encode("utf-8")

    s.sendall(hi)

    data = s.recv(1024)
    print('Server: ', len(data), data.decode("utf8"))
finally:
    s.close()
