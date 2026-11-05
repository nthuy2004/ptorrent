import os
import sys

src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from client.gui.app import main


if __name__ == "__main__":
    raise SystemExit(main())
