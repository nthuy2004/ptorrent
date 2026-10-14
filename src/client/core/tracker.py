from client.core.chunker import Metadata
import requests
from client.utils.log import logger
from typing import Optional
from typing import Any
from client.core.bus import bus
class Tracker:
    def __init__(self, base_url: str):
        self.base_url = base_url
        pass

    def register(self, metadata: Metadata):
        url = f"{self.base_url}/register.php"
        payload = {
            "file_id": metadata.file_id,
            "file_name": metadata.file_name,
            "file_size": metadata.file_size,
            "piece_size": metadata.piece_size,
            "total_pieces": metadata.total_pieces,
            "file_hash": metadata.file_hash
        }
        try:
            resp = requests.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("status") == "success"
        except Exception as e:
            logger.e(f"cannot register your file {e}")
            return False
        pass

    def announce(
        self,
        file_id: str,
        peer_id: str,
        port: int,
        uploaded: int,
        downloaded: int,
        bytes_left: int,
        event: str = "",
        bitfield: Optional[list[int]] = None,
        ip: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Gửi báo cáo trạng thái lên Tracker và nhận về danh sách các Peer trong Swarm.
        Sự kiện hỗ trợ: 'started', 'completed', 'stopped', '' (heartbeat).
        """
        url = f"{self.base_url}/announce.php"
        payload = {
            "file_id": file_id,
            "peer_id": peer_id,
            "port": port,
            "uploaded": uploaded,
            "downloaded": downloaded,
            "bytes_left": bytes_left,
            "event": event,
            "bitfield": bitfield
        }
        if ip:
            payload["ip"] = ip

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            result = resp.json()

            print(f"resp: {resp.text}")

            if event != "stopped":
                bus.publish("tracker.announced", {
                    "file_id": file_id,
                    "event": event,
                    "complete": result.get("complete", 0),
                    "incomplete": result.get("incomplete", 0),
                    "peers_count": len(result.get("peers", []))
                })
            return result
        except Exception as e:
            logger.e(f"annoucne error {e}")
            return {"interval": 15, "complete": 0, "incomplete": 0, "peers": []}
