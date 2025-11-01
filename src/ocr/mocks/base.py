from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class DocumentParserMock(ABC, Generic[T]):
    """Base helper for document parser mocks that cache expensive responses.

    Subclasses are responsible for serializing/deserializing the mocked payload.
    """

    def __init__(self, mock_path: str) -> None:
        if not mock_path:
            raise ValueError(
                "mock_path must be provided for DocumentParserMock.")
        self._mock_path = mock_path

    @property
    def path(self) -> str:
        """Absolute or relative path where the mock payload is stored."""
        return self._mock_path

    def exists(self) -> bool:
        """Return True when a persisted mock payload is available."""
        return os.path.exists(self._mock_path)

    def _prepare_directory(self) -> None:
        directory = os.path.dirname(self._mock_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    @abstractmethod
    def load(self) -> T:
        """Load the persisted payload."""

    @abstractmethod
    def save(self, payload: T) -> None:
        """Persist a payload for future test runs."""
