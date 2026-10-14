import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client.utils.log import logger
from client.core.chunker import Chunker

logger.i("Hello world")

chunker = Chunker()

chunker.create_metadata("D:\\PTIT\\ptorrent\\DEBAI.pdf", "https://nth.io.vn/announce.php", saved_metadata_path="D:\\PTIT\\ptorrent\\DEMO_META.ptorrent")