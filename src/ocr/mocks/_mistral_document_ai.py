from __future__ import annotations

import pickle
from contextlib import contextmanager
from typing import Generator

from unittest.mock import patch

from src.ocr.mocks.base import DocumentParserMock


class MistralDocumentAIParserMock(DocumentParserMock):
    """Persist Mistral Document AI parse responses in pickle form for lightweight replay."""

    def load(self) -> None:
        with open(self.path, "rb") as mock_file:
            return pickle.load(mock_file)

    def save(self, payload) -> None:
        self._prepare_directory()
        with open(self.path, "wb") as mock_file:
            pickle.dump(payload, mock_file)

    @contextmanager
    def patch_parse(self) -> Generator[None, None, None]:
        pass
