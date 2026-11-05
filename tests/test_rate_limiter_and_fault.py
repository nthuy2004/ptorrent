import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.config import (
    DEFAULT_PORT,
    DEFAULT_UPLOAD_LIMIT,
    DEFAULT_DOWNLOAD_LIMIT,
    DEFAULT_FAULT_RATE,
)
from client.core.rate_limiter import TokenBucketRateLimiter
from client.gui.app import create_argument_parser


def test_rate_limiter_unlimited_by_default():
    limiter = TokenBucketRateLimiter(0)
    start = time.monotonic()
    limiter.acquire(1024 * 1024)  # 1 MiB
    elapsed = time.monotonic() - start
    assert elapsed < 0.05


def test_rate_limiter_throttles_transmission():
    # 50 KiB/s limit -> 5 KiB should take ~0.1s
    limiter = TokenBucketRateLimiter(50)
    # Drain initial capacity
    limiter.acquire(50 * 1024)

    start = time.monotonic()
    limiter.acquire(5 * 1024)
    elapsed = time.monotonic() - start
    assert elapsed >= 0.05


def test_cli_parser_defaults_from_config():
    parser = create_argument_parser()
    args = parser.parse_args([])

    assert args.port == DEFAULT_PORT
    assert args.upload_limit == DEFAULT_UPLOAD_LIMIT
    assert args.download_limit == DEFAULT_DOWNLOAD_LIMIT
    assert args.fault_rate == DEFAULT_FAULT_RATE


def test_cli_parser_custom_rate_and_fault_arguments():
    parser = create_argument_parser()
    args = parser.parse_args([
        "--upload-limit", "256",
        "--download-limit", "512",
        "--fault-rate", "0.25",
    ])

    assert args.upload_limit == 256
    assert args.download_limit == 512
    assert args.fault_rate == 0.25
