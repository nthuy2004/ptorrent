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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.core.protocol import Protocol
from client.utils.log import logger
from client.core.peer_server import PeerServer

def main():
    logger.d("begin main")
    p = PeerServer("PEER_A")
    p.start()
    logger.i("server started")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()