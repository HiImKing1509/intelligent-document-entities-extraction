from __future__ import annotations

import pickle
from contextlib import contextmanager
from typing import Generator

from landingai_ade import LandingAIADE
from landingai_ade.types.parse_response import ParseResponse
from unittest.mock import patch

from src.ocr.mocks.base import DocumentParserMock


class LandingAIDocumentParserMock(DocumentParserMock[ParseResponse]):
    """Persist LandingAI parse responses in pickle form for lightweight replay."""

    def load(self) -> ParseResponse:
        with open(self.path, "rb") as mock_file:
            return pickle.load(mock_file)

    def save(self, payload: ParseResponse) -> None:
        self._prepare_directory()
        with open(self.path, "wb") as mock_file:
            pickle.dump(payload, mock_file)

    @contextmanager
    def patch_parse(self) -> Generator[None, None, None]:
        """Patch LandingAIADE.parse to replay or capture parse responses.

        When the mock exists, it is reused. Otherwise the real API call runs once,
        the response is cached, and then returned.
        """

        mock_handler = self
        original_parse = LandingAIADE.parse

        def _mock_parse(  # type: ignore[override]
            client: LandingAIADE,
            *args,
            **kwargs,
        ) -> ParseResponse:
            if mock_handler.exists():
                return mock_handler.load()

            response = original_parse(client, *args, **kwargs)
            mock_handler.save(response)
            return response

        with patch.object(LandingAIADE, "parse", _mock_parse):
            yield
