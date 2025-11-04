from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Dict, Generator

from unittest.mock import patch

from src.ocr.mocks.base import DocumentParserMock
from src.services.mistral_document_ai.client import MistralDocumentAIClient


class MistralDocumentAIParserMock(DocumentParserMock[Dict[str, Any]]):
    """Persist Mistral Document AI parse responses in JSON form for lightweight replay."""

    def load(self) -> Dict[str, Any]:
        with open(self.path, "r", encoding="utf-8") as mock_file:
            return json.load(mock_file)

    def save(self, payload: Dict[str, Any]) -> None:
        self._prepare_directory()
        with open(self.path, "w", encoding="utf-8") as mock_file:
            json.dump(payload, mock_file, ensure_ascii=True, indent=2)

    @contextmanager
    def patch_parse(self) -> Generator[None, None, None]:
        """Patch MistralDocumentAIClient.analyze_document with cached responses."""

        mock_handler = self
        original_analyze = MistralDocumentAIClient.analyze_document

        def _mock_analyze_document(  # type: ignore[override]
            client: MistralDocumentAIClient,
            params,
        ) -> Dict[str, Any]:
            if mock_handler.exists():
                return mock_handler.load()

            response = original_analyze(client, params)
            mock_handler.save(response)
            return response

        with patch.object(MistralDocumentAIClient, "analyze_document", _mock_analyze_document):
            yield
