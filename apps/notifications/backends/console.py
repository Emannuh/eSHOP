"""Console SMS backend — prints messages to stdout (dev / test use)."""
import logging

from .base import BaseSmsBackend

logger = logging.getLogger(__name__)


class ConsoleSmsBackend(BaseSmsBackend):
    """SMS backend that logs messages to the console instead of sending them."""

    def send(self, to: str, message: str) -> bool:
        logger.info("[SMS → %s] %s", to, message)
        print(f"[SMS → {to}] {message}")  # noqa: T201
        return True
