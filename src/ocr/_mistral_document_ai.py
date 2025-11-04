from __future__ import annotations

from base64 import b64encode
from typing import Optional

import fitz  # PyMuPDF
from loguru import logger

from src.services.mistral_document_ai import MistralDocumentAIClient
from src.services.mistral_document_ai.params import (
    MistralDAChatCompletionMessageParam,
    MistralDADocumentParam,
)
from src.ocr import DocumentParser
from src.ocr.mocks._mistral_document_ai import MistralDocumentAIParserMock


class MistralDocumentAIParser(DocumentParser):
    """Document parser that delegates parsing to Mistral Document AI."""

    def __init__(
        self,
        document: bytes,
        document_parser_mock: Optional[str] = None,
        client: Optional[MistralDocumentAIClient] = None,
    ) -> None:
        super().__init__(document)
        self._client = client or MistralDocumentAIClient()
        self._mock_handler: Optional[MistralDocumentAIParserMock] = (
            MistralDocumentAIParserMock(document_parser_mock)
            if document_parser_mock
            else None
        )

    def parse(self, plot: bool = False) -> None:
        parsed_response = self._parse_document()
        if plot:
            self._plot_chunks(parsed_response)
        return parsed_response

    def _parse_document(self) -> None:
        if self._mock_handler and self._mock_handler.exists():
            logger.info(
                f"Mock parsed response loaded from {self._mock_handler.path}.")
            return self._mock_handler.load()

        parsed_params = self._build_params()
        parsed_response = self._client.analyze_document(parsed_params)

        if self._mock_handler:
            try:
                self._mock_handler.save(parsed_response)
                logger.info(
                    f"Mock parsed response saved to {self._mock_handler.path}.")
            except Exception as error:  # pragma: no cover - defensive logging
                logger.warning(
                    f"Failed to persist Mistral Document AI mock response: {error}")

        return parsed_response

    def _plot_chunks(self, parsed_response) -> None:
        pass

    def _build_params(self) -> MistralDAChatCompletionMessageParam:
        """
        Convert the provided document bytes into the payload expected by the Mistral client.
        """
        if not isinstance(self.document, (bytes, bytearray, memoryview)):
            raise TypeError(
                "MistralDocumentAIParser expects the document input to be bytes-like."
            )

        document_bytes = bytes(self.document)
        base64_value = b64encode(document_bytes).decode("ascii")

        document_param = MistralDADocumentParam(base64_data=base64_value)
        return MistralDAChatCompletionMessageParam(document=document_param)
