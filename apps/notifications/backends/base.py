"""Base SMS backend interface."""
from abc import ABC, abstractmethod


class BaseSmsBackend(ABC):
    """Interface all SMS backends must implement."""

    @abstractmethod
    def send(self, to: str, message: str) -> bool:
        """Send an SMS.

        Args:
            to: Recipient phone number in international format (e.g. +254700000000).
            message: SMS body text.

        Returns:
            True if accepted by the underlying service, False otherwise.
        """
        ...
