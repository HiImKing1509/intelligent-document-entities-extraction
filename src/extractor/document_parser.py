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
            document: Union[str, bytes] = None,
            service: ServiceType = ServiceType.LANDING_AI,
    ) -> None:

        self.service = service
        self.document = document

    @staticmethod
    def _convert_pdf_to_images_to_pdf(
        input_pdf: fitz.Document,
        output_path: str = None,
    ) -> fitz.Document:
        """ Converts each page of a PDF document to an image and then compiles them back into a PDF. """

        try:
            DEFAULT_DPI = 450
            output_pdf = fitz.open()

            for i, page in enumerate(input_pdf):
                pix = page.get_pixmap(dpi=DEFAULT_DPI)
                img_bytes = pix.tobytes(output="jpeg", jpg_quality=85)
                new_page = output_pdf.new_page(
                    width=page.rect.width, height=page.rect.height)
                new_page.insert_image(page.rect, stream=img_bytes)
                logger.info(f"  > Processed page {i + 1}/{len(input_pdf)}")

            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                output_pdf.save(
                    output_path,
                    garbage=4,  # remove unused objects
                    deflate=True,  # compress streams
                )
        except Exception as e:
            logger.error(f"Error during PDF conversion: {e}")
        # finally:
            # input_pdf.close()
            # output_pdf.close()

        return output_pdf

    def document_reader(self, document: Union[str, bytes]) -> bytes:
        if isinstance(document, str):
            try:
                if document.startswith("http://") or document.startswith("https://"):
                    response = requests.get(document)
                    response.raise_for_status()
                    pdf_bytes = response.content
                else:
                    with open(document, "rb") as file:
                        pdf_bytes = file.read()
                logger.info(f"PDF size: {len(pdf_bytes) / (1024*1024):.2f} MB")
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Document not found at path: {document}")
            except IOError as e:
                raise IOError(f"Failed to read document: {e}")

            if self.service == ServiceType.LANDING_AI:
                with fitz.open("pdf", pdf_bytes) as doc:
                    converted_pdf = self._convert_pdf_to_images_to_pdf(
                        input_pdf=doc,
                        output_path=None
                    )
                    pdf_bytes_io = io.BytesIO()
                    converted_pdf.save(pdf_bytes_io)
                    pdf_bytes = pdf_bytes_io.getvalue()
                    logger.info(
                        f"Converted PDF size: {len(pdf_bytes) / (1024*1024):.2f} MB")
                    return pdf_bytes
        else:
            # Document is already bytes
            logger.info(f"PDF size: {len(document) / (1024*1024):.2f} MB")
            return document

    def parse(self, plot: bool = False) -> Union[ParseResponse, dict]:
        """Parse the document and return structured data."""
        document_bytes = self.document_reader(self.document)

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
                parsed_response = client.parse(document=document_bytes)
        else:
            parsed_response = client.parse(document=document_bytes)

        if plot:
            if not isinstance(self.document, str) or not self.document.lower().endswith(".pdf"):
                logger.warning(
                    "Plotting is only supported for PDF files specified by path.")
                return parsed_response

            try:
                doc = fitz.open("pdf", document_bytes)

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
