import threading
from typing import Callable, Any, Dict, Tuple
from pubsub import pub


class EventBus:
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super(EventBus, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._lock = threading.RLock()
        self._wrappers: Dict[Tuple[str, Callable], Callable] = {}
        self._initialized = True

    def subscribe(self, topic: str, callback: Callable[[Any], None]) -> None:
        with self._lock:
            key = (topic, callback)
            if key in self._wrappers:
                return

            def _pypubsub_listener(data=None):
                callback(data)

            self._wrappers[key] = _pypubsub_listener
            pub.subscribe(_pypubsub_listener, topic)

    def unsubscribe(self, topic: str, callback: Callable[[Any], None]) -> None:
        with self._lock:
            key = (topic, callback)
            wrapper = self._wrappers.pop(key, None)
            if wrapper is not None:
                pub.unsubscribe(wrapper, topic)

    def publish(self, topic: str, data: Any = None) -> None:
        with self._lock:
            pub.sendMessage(topic, data=data)

bus = EventBus()