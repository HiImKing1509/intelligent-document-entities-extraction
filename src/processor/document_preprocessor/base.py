from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple, Union

import fitz
import requests
from loguru import logger

from src.processor.page_processor import PageRotator, SkewDetector


@dataclass(frozen=True)
class PreprocessingSettings:
    """Configuration that balances readability with manageable file sizes."""

    raster_dpi: int = 450
    jpg_quality: int = 82
    preserve_image_only_pages: bool = True
    optimize_garbage: int = 4
    optimize_clean: bool = True
    optimize_deflate: bool = True

    def __post_init__(self) -> None:
        if self.raster_dpi <= 0:
            raise ValueError("raster_dpi must be positive.")
        if not (0 <= self.jpg_quality <= 100):
            raise ValueError("jpg_quality must be in the range [0, 100].")
        if not (0 <= self.optimize_garbage <= 4):
            raise ValueError("optimize_garbage must be in the range [0, 4].")


class DocumentPreprocessor(ABC):
    def __init__(
        self,
        document: Union[str, bytes, None] = None,
        settings: Optional[PreprocessingSettings] = None,
    ) -> None:
        self.document = document
        self.settings = settings or PreprocessingSettings()

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
            except FileNotFoundError as exc:
                raise FileNotFoundError(
                    f"Document not found at path: {document}"
                ) from exc
            except IOError as exc:
                raise IOError(f"Failed to read document: {exc}") from exc
            return pdf_bytes
        logger.info(f"PDF size: {len(document) / (1024*1024):.2f} MB")
        return document

    def document_rotator(self, document_bytes: bytes) -> bytes:
        try:
            doc = fitz.open(stream=document_bytes, filetype="pdf")
        except Exception as exc:  # pragma: no cover - passthrough for fitz issues
            logger.error(f"Failed to load document into fitz: {exc}")
            raise

        try:
            page_rotator = PageRotator()
            for page in doc:
                page_rotator.rotate(page)

            rotated_document_bytes = self._serialize_pdf(doc)
            logger.info(
                f"Rotated PDF size: {len(rotated_document_bytes) / (1024*1024):.2f} MB"
            )
            return rotated_document_bytes
        finally:
            doc.close()

    def convert_pdf_to_images_to_pdf(self, document_bytes: bytes) -> bytes:
        """Render each PDF page to an image and rebuild a PDF from the rendered pages."""

        if not isinstance(document_bytes, (bytes, bytearray)):
            raise TypeError("document_bytes must be bytes-like data.")

        try:
            input_pdf = fitz.open(stream=document_bytes, filetype="pdf")
        except Exception as exc:
            logger.error(f"Failed to load PDF from bytes: {exc}")
            raise

        output_pdf = fitz.open()

        try:
            page_count = input_pdf.page_count

            for index, page in enumerate(input_pdf):
                if self._should_copy_page(page):
                    output_pdf.insert_pdf(
                        input_pdf, from_page=index, to_page=index)
                    logger.info(
                        f"Copied original page {index + 1}/{page_count} (no selectable text)"
                    )
                    continue

                image_bytes, page_rect = self._render_page_to_image(page)
                self._append_rasterized_page(
                    output_pdf, page_rect, image_bytes)
                logger.info(
                    f"Processed page {index + 1}/{page_count} at {self.settings.raster_dpi} DPI"
                )

            converted_bytes = self._serialize_pdf(output_pdf)
            logger.info(
                f"Converted PDF size: {len(converted_bytes) / (1024 * 1024):.2f} MB"
            )
            return converted_bytes

        except Exception as exc:
            logger.error(f"Error during PDF conversion: {exc}")
            raise
        finally:
            input_pdf.close()
            output_pdf.close()

    def skew_detector(self, document_bytes: bytes) -> bytes:
        if not isinstance(document_bytes, (bytes, bytearray)):
            raise TypeError("document_bytes must be bytes-like data.")

        try:
            input_pdf = fitz.open(stream=document_bytes, filetype="pdf")
        except Exception as exc:
            logger.error(f"Failed to load PDF for skew detection: {exc}")
            raise

        output_pdf = fitz.open()
        detector = SkewDetector()

        try:
            page_count = input_pdf.page_count
            for index in range(page_count):
                page = input_pdf.load_page(index)
                result = detector.deskew_page(page)

                if result.image_bytes is None:
                    output_pdf.insert_pdf(
                        input_pdf, from_page=index, to_page=index)
                    continue

                new_page = output_pdf.new_page(
                    width=result.width_pts, height=result.height_pts
                )
                new_page.insert_image(new_page.rect, stream=result.image_bytes)
                logger.info(
                    f"Deskewed page {index + 1}/{page_count} by {result.angle:.2f} degrees"
                )

            corrected_bytes = self._serialize_pdf(output_pdf)
            logger.info(
                f"Skew-corrected PDF size: {len(corrected_bytes) / (1024 * 1024):.2f} MB"
            )
            return corrected_bytes
        except Exception as exc:
            logger.error(f"Error during skew correction: {exc}")
            raise
        finally:
            input_pdf.close()
            output_pdf.close()

    def _should_copy_page(self, page: fitz.Page) -> bool:
        """Return True when a page contains no selectable text and can be copied directly."""
        if not self.settings.preserve_image_only_pages:
            return False

        try:
            extracted_text = page.get_text(
                "text", flags=fitz.TEXTFLAGS_TEXT).strip()
        except RuntimeError as exc:
            logger.debug(
                "Failed to extract text for page %s: %s. Rasterising page.",
                page.number + 1,
                exc,
            )
            return False

        return not extracted_text

    def _render_page_to_image(self, page: fitz.Page) -> Tuple[bytes, fitz.Rect]:
        """Rasterise a page using the fixed DPI budget."""
        scale = self.settings.raster_dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        try:
            image_bytes = pix.tobytes(
                output="jpeg", jpg_quality=self.settings.jpg_quality)
        except ValueError as exc:
            logger.warning(
                "Falling back to PNG for page %s due to JPEG encoding error: %s",
                page.number + 1,
                exc,
            )
            image_bytes = pix.tobytes(output="png")

        page_rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
        return image_bytes, page_rect

    @staticmethod
    def _append_rasterized_page(
        document: fitz.Document,
        page_rect: fitz.Rect,
        image_bytes: bytes,
    ) -> None:
        """Insert a rasterised image into the output PDF."""
        new_page = document.new_page(
            width=page_rect.width, height=page_rect.height)
        new_page.insert_image(page_rect, stream=image_bytes)

    def _serialize_pdf(self, document: fitz.Document) -> bytes:
        try:
            return document.tobytes(
                garbage=self.settings.optimize_garbage,
                clean=self.settings.optimize_clean,
                deflate=self.settings.optimize_deflate,
            )
        except TypeError:
            return document.tobytes()

    @abstractmethod
    def preprocess(self) -> bytes:
        raise NotImplementedError
