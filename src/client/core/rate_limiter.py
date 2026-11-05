from __future__ import annotations

import threading
import time


class TokenBucketRateLimiter:
    """Thread-safe Token Bucket Rate Limiter in KiB/s.

    A limit <= 0 means unlimited bandwidth (acquire returns immediately).
    """

    def __init__(self, limit_kib_s: int = 0):
        self.limit_bytes_s = max(0, int(limit_kib_s)) * 1024
        self.capacity = float(self.limit_bytes_s)
        self.tokens = self.capacity
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def set_limit(self, limit_kib_s: int) -> None:
        with self._lock:
            self.limit_bytes_s = max(0, int(limit_kib_s)) * 1024
            self.capacity = float(self.limit_bytes_s)
            self.tokens = self.capacity
            self.last_refill = time.monotonic()

    def acquire(self, num_bytes: int) -> None:
        """Blocks until num_bytes can be transmitted under the configured rate limit."""
        if self.limit_bytes_s <= 0 or num_bytes <= 0:
            return

        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.last_refill = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.limit_bytes_s)

                if self.tokens >= num_bytes:
                    self.tokens -= num_bytes
                    return

                needed = num_bytes - self.tokens
                sleep_time = needed / self.limit_bytes_s

            # Sleep in short increments to remain responsive
            time.sleep(min(sleep_time, 0.05))
