from utils.log import logger
from core.chunker import Chunker

logger.i("Hello world")

chunker = Chunker()

chunker.create_metadata("D:\\PTIT\\ptorrent\\DEBAI.pdf", "https://nth.io.vn/announce.php", saved_metadata_path="D:\\PTIT\\ptorrent\\DEMO_META.ptorrent")