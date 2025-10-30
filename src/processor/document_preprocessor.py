import io
import fitz
import requests
from loguru import logger
from typing import Union
from abc import ABC, abstractmethod

from src.models.services import ServiceType
from src.processor.page_processor import PageRotator


class DocumentPreprocessor(ABC):
    def __init__(self, document: Union[str, bytes] = None):
        self.document = document

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
            return pdf_bytes
        else:
            # Document is already bytes
            logger.info(f"PDF size: {len(document) / (1024*1024):.2f} MB")
            return document

    def document_rotator(self, document_bytes: bytes) -> bytes:
        try:
            doc = fitz.open(stream=document_bytes, filetype="pdf")
        except Exception as e:
            logger.error(f"Failed to load document into fitz: {e}")
            raise

        try:
            page_rotator = PageRotator()

            for page in doc:
                page_rotator.rotate(page)

            rotated_document_bytes = doc.tobytes()
            logger.info(
                f"Converted PDF size: {len(rotated_document_bytes) / (1024*1024):.2f} MB")
            return rotated_document_bytes
        finally:
            doc.close()

    def convert_pdf_to_images_to_pdf(
        self,
        document_bytes: bytes,
        dpi: int = 450,
        jpg_quality: int = 85,
        preserve_image_only_pages: bool = True,
    ) -> bytes:
        """Render each PDF page to an image and rebuild a PDF from the rendered pages.

        If a page has no selectable text and ``preserve_image_only_pages`` is True, the original page
        is copied instead of rasterising it again. This helps keep existing scanned pages from
        ballooning in size.
        """

        if not isinstance(document_bytes, (bytes, bytearray)):
            raise TypeError("document_bytes must be bytes-like data.")

        if not (72 <= dpi <= 1200):
            raise ValueError("dpi must be between 72 and 1200.")

        if not (0 <= jpg_quality <= 100):
            raise ValueError("jpg_quality must be in the range [0, 100].")

        try:
            input_pdf = fitz.open(stream=document_bytes, filetype="pdf")
        except Exception as exc:
            logger.error(f"Failed to load PDF from bytes: {exc}")
            raise

        output_pdf = fitz.open()

        try:
            page_count = input_pdf.page_count
            scale = dpi / 72.0  # Render matrix scaling (72 dpi is PDF default)

            for index, page in enumerate(input_pdf):
                if preserve_image_only_pages:
                    try:
                        has_text = bool(page.get_text("text", flags=fitz.TEXTFLAGS_TEXT).strip())
                    except RuntimeError:
                        # Some documents may fail to extract text; assume rasterisation is needed.
                        has_text = True

                    if not has_text:
                        output_pdf.insert_pdf(input_pdf, from_page=index, to_page=index)
                        logger.info(f"Copied original page {index + 1}/{page_count} (no selectable text)")
                        continue

                matrix = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=matrix, alpha=False)

                try:
                    img_bytes = pix.tobytes(
                        output="jpeg", jpg_quality=jpg_quality)
                except ValueError as exc:
                    # Some pixmaps (e.g., grayscale) can trigger a ValueError when encoding as JPEG.
                    logger.warning(
                        f"Falling back to PNG for page {index + 1} due to JPEG encoding error: {exc}"
                    )
                    img_bytes = pix.tobytes(output="png")

                # Use the original page rectangle to keep layout consistent.
                page_rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
                new_page = output_pdf.new_page(
                    width=page_rect.width, height=page_rect.height)
                new_page.insert_image(page_rect, stream=img_bytes)
                logger.info(f"Processed page {index + 1}/{page_count}")

            converted_bytes = output_pdf.tobytes()
            logger.info(
                f"Converted PDF size: {len(converted_bytes) / (1024 * 1024):.2f} MB")
            return converted_bytes

        except Exception as exc:
            logger.error(f"Error during PDF conversion: {exc}")
            raise
        finally:
            input_pdf.close()
            output_pdf.close()

    @abstractmethod
    def preprocess(self) -> bytes:
        # Implement your preprocessing logic here
        pass


class LandingAIDocumentPreprocessor(DocumentPreprocessor):
    def __init__(self, document: Union[str, bytes] = None):
        super().__init__(document)

    def preprocess(self) -> bytes:
        # Read the document
        document_bytes = self.document_reader(self.document)
        with open("original_doc.pdf", "wb") as f:
            f.write(document_bytes)

        # Rotate the document pages if needed
        rotated_document_bytes = self.document_rotator(document_bytes)
        with open("rotated_document.pdf", "wb") as f:
            f.write(rotated_document_bytes)

        # Convert PDF pages to images and back to PDF
        converted_document_bytes = self.convert_pdf_to_images_to_pdf(
            rotated_document_bytes)
        with open("converted_document.pdf", "wb") as f:
            f.write(converted_document_bytes)

        return converted_document_bytes

# Document preprocessor factory class


class DocumentPreprocessorFactory:
    processor: DocumentPreprocessor

    def __init__(self, service: ServiceType):
        if service == ServiceType.LANDING_AI:
            self.processor = LandingAIDocumentPreprocessor
        else:
            raise ValueError(f"Unsupported service type: {service}")
