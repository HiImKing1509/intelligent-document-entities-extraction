from __future__ import annotations

from typing import Optional, Union

import fitz  # PyMuPDF
from landingai_ade.types.parse_response import ParseResponse
from loguru import logger

from src.services.landing_ai import LandingAIClient
from src.ocr import DocumentParser
from src.ocr.mocks.landingai import LandingAIDocumentParserMock


class LandingAIDocumentParser(DocumentParser):
    """Document parser that delegates parsing to LandingAI."""

    def __init__(
        self,
        document: bytes,
        document_parser_mock: Optional[str] = None,
        client: Optional[LandingAIClient] = None,
    ) -> None:
        super().__init__(document)
        self._client = client or LandingAIClient()
        self._mock_handler: Optional[LandingAIDocumentParserMock] = (
            LandingAIDocumentParserMock(document_parser_mock)
            if document_parser_mock
            else None
        )

    def parse(self, plot: bool = False) -> ParseResponse:
        parsed_response = self._parse_document()
        if plot:
            self._plot_chunks(parsed_response)
        return parsed_response

    def _parse_document(self) -> ParseResponse:
        if self._mock_handler and self._mock_handler.exists():
            logger.info(
                f"Mock parsed response loaded from {self._mock_handler.path}.")
            return self._mock_handler.load()

        parsed_response = self._client.parse(document=self.document)

        if self._mock_handler:
            try:
                self._mock_handler.save(parsed_response)
                logger.info(
                    f"Mock parsed response saved to {self._mock_handler.path}.")
            except Exception as error:  # pragma: no cover - defensive logging
                logger.warning(
                    f"Failed to persist LandingAI mock response: {error}")

        return parsed_response

    def _plot_chunks(self, parsed_response: ParseResponse) -> None:
        if not isinstance(parsed_response, ParseResponse):
            logger.warning(
                "Unable to plot LandingAI chunks: unexpected response type.")
            return

        try:
            doc = fitz.open(stream=self.document, filetype="pdf")
        except Exception as error:  # pragma: no cover - defensive logging
            logger.error(f"Failed to open PDF for plotting: {error}")
            return

        chunk_type_colors = {
            "text": (0, 0.5, 0),
            "marginalia": (1, 0, 0),
            "scan_code": (1, 0.5, 1),
            "table": (0, 0, 1),
            "attestation": (1, 0, 0.5),
            "default": (1, 1, 0),
        }

        try:
            for chunk in parsed_response.chunks:
                chunk_grounding = chunk.grounding
                if not chunk_grounding:
                    continue

                page_num = chunk_grounding.page
                if page_num < 0 or page_num >= len(doc):
                    continue

                page = doc[page_num]
                page_width = page.rect.width
                page_height = page.rect.height

                chunk_box = chunk_grounding.box
                x0 = chunk_box.left * page_width
                y0 = chunk_box.top * page_height
                x1 = chunk_box.right * page_width
                y1 = chunk_box.bottom * page_height

                color = chunk_type_colors.get(
                    chunk.type, chunk_type_colors["default"])
                rect = fitz.Rect(x0, y0, x1, y1)
                page.draw_rect(rect, color=color, width=1.0)

                text_point = fitz.Point(x0, max(y0 - 2, 0))
                page.insert_text(text_point, chunk.type,
                                 fontsize=8, color=color)

            output_path = "visualized_chunk_output.pdf"
            doc.save(output_path, garbage=4, deflate=True)
            logger.info(f"Saved visualized PDF to {output_path}")
        except Exception as error:  # pragma: no cover - defensive logging
            logger.error(f"Failed to plot bounding boxes: {error}")
        finally:
            doc.close()
