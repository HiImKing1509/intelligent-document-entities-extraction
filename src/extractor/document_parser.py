import io
import os
import fitz  # PyMuPDF
import pickle
import requests
from typing import Union
from loguru import logger
from src.services.landing_ai import LandingAIClient
from landingai_ade.types.parse_response import ParseResponse

from src.models.services import ServiceType


class DocumentParser:

    def __init__(
            self,
            document: bytes = None,
            service: ServiceType = ServiceType.LANDING_AI,
    ) -> None:

        self.service = service
        self.document = document

    def parse(self, plot: bool = False) -> Union[ParseResponse, dict]:
        """Parse the document and return structured data."""

        if self.service == ServiceType.LANDING_AI:
            client = LandingAIClient()
        else:
            client = None

        if isinstance(self.document, str):
            mock_response_pkl_path = self.document.replace(
                ".pdf", ".pkl").replace("Files", "LandingAIParsedMocks")
            if os.path.exists(mock_response_pkl_path):
                with open(mock_response_pkl_path, "rb") as file:
                    parsed_response = pickle.load(file)
                logger.info(
                    f"Mock parsed response loaded from {mock_response_pkl_path}.")
            else:
                parsed_response = client.parse(document=self.document)
        else:
            parsed_response = client.parse(document=self.document)

        if plot:
            if not isinstance(self.document, str) or not self.document.lower().endswith(".pdf"):
                logger.warning(
                    "Plotting is only supported for PDF files specified by path.")
                return parsed_response

            try:
                doc = fitz.open("pdf", self.document)

                CHUNK_TYPE_COLORS = {
                    "text": (0, 1, 0),        # Green
                    "marginalia": (1, 0, 0),  # Red
                    "scan_code": (1, 0.5, 1),  # Purple
                    "default": (1, 1, 0),     # Yellow for other types
                }

                for chunk in parsed_response.chunks:
                    chunk_type = chunk.type
                    chunk_grounding = chunk.grounding
                    if not chunk_grounding:
                        continue

                    color = CHUNK_TYPE_COLORS.get(
                        chunk_type, CHUNK_TYPE_COLORS["default"])
                    chunk_grounding_box = chunk_grounding.box
                    page_num = chunk_grounding.page

                    if 0 <= page_num < len(doc):
                        page = doc[page_num]

                        page_width = page.rect.width
                        page_height = page.rect.height

                        x0 = chunk_grounding_box.left * page_width
                        y0 = chunk_grounding_box.top * page_height
                        x1 = chunk_grounding_box.right * page_width
                        y1 = chunk_grounding_box.bottom * page_height

                        rect = fitz.Rect(x0, y0, x1, y1)
                        page.draw_rect(rect, color=color, width=1.0)

                        # Insert chunk type text at the top-left corner of the bounding box
                        text_insertion_point = fitz.Point(x0, y0 - 2)
                        page.insert_text(
                            text_insertion_point,
                            chunk_type,
                            fontsize=8,
                            color=color,
                        )

                output_path = "visualized_chunk_output.pdf"
                doc.save(output_path, garbage=4, deflate=True)
                logger.info(f"Saved visualized PDF to {output_path}")
                doc.close()

            except Exception as e:
                logger.error(f"Failed to plot bounding boxes: {e}")

        # breakpoint()
        return parsed_response
