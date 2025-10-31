from __future__ import annotations

import os
import pickle
from typing import Optional, Union

import fitz  # PyMuPDF
from landingai_ade.types.parse_response import ParseResponse
from loguru import logger

from src.services.landing_ai import LandingAIClient

from src.ocr import DocumentParser


class LandingAIDocumentParser(DocumentParser):
    """Document parser that delegates parsing to LandingAI."""

    def __init__(
        self,
        document: bytes,
        client: Optional[LandingAIClient] = None,
    ) -> None:
        super().__init__(document)
        self._client = client or LandingAIClient()

    def parse(self, plot: bool = False) -> ParseResponse:
        parsed_response = self._parse_document()
        if plot:
            self._plot_chunks(parsed_response)
        return parsed_response

    def _parse_document(self) -> ParseResponse:
        if isinstance(self.document, str):
            mock_response_path = self._mock_response_path(self.document)
            if mock_response_path and os.path.exists(mock_response_path):
                with open(mock_response_path, "rb") as mock_file:
                    parsed_response = pickle.load(mock_file)
                logger.info(
                    f"Mock parsed response loaded from {mock_response_path}.")
                return parsed_response

        return self._client.parse(document=self.document)

    def _mock_response_path(self, document_path: str) -> Optional[str]:
        if not document_path.lower().endswith(".pdf"):
            return None

        return document_path.replace(".pdf", ".pkl").replace("Files", "LandingAIParsedMocks")

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
