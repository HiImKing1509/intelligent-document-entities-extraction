from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Union

import fitz
import requests
from loguru import logger

from src.models.services import ServiceType
from src.processor.page_processor import PageRotator, SkewDetector


@dataclass(frozen=True)
class PreprocessingSettings:
    """Configuration that balances readability with manageable file sizes."""

    min_dpi: int = 240
    max_dpi: int = 360
    target_long_edge_px: int = 3400
    jpg_quality: int = 82
    preserve_image_only_pages: bool = True
    optimize_garbage: int = 4
    optimize_clean: bool = True
    optimize_deflate: bool = True

    def __post_init__(self) -> None:
        if self.min_dpi <= 0:
            raise ValueError("min_dpi must be positive.")
        if self.max_dpi < self.min_dpi:
            raise ValueError(
                "max_dpi must be greater than or equal to min_dpi.")
        if self.target_long_edge_px <= 0:
            raise ValueError("target_long_edge_px must be positive.")
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
                current_dpi = self._determine_page_dpi(page)
                scale = current_dpi / 72.0

                if self.settings.preserve_image_only_pages:
                    try:
                        has_text = bool(
                            page.get_text(
                                "text", flags=fitz.TEXTFLAGS_TEXT).strip()
                        )
                    except RuntimeError:
                        has_text = True

                    if not has_text:
                        output_pdf.insert_pdf(
                            input_pdf, from_page=index, to_page=index)
                        logger.info(
                            f"Copied original page {index + 1}/{page_count} (no selectable text)"
                        )
                        continue

                matrix = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=matrix, alpha=False)

                try:
                    img_bytes = pix.tobytes(
                        output="jpeg", jpg_quality=self.settings.jpg_quality
                    )
                except ValueError as exc:
                    logger.warning(
                        f"Falling back to PNG for page {index + 1} due to JPEG encoding error: {exc}"
                    )
                    img_bytes = pix.tobytes(output="png")

                page_rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
                new_page = output_pdf.new_page(
                    width=page_rect.width, height=page_rect.height)
                new_page.insert_image(page_rect, stream=img_bytes)
                logger.info(
                    f"Processed page {index + 1}/{page_count} at {current_dpi} DPI"
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

    def _determine_page_dpi(self, page: fitz.Page) -> int:
        long_edge_inches = max(page.rect.width, page.rect.height) / 72.0
        if long_edge_inches <= 0:
            return self.settings.min_dpi

        target_dpi = int(
            round(self.settings.target_long_edge_px / long_edge_inches))
        clamped_dpi = max(
            self.settings.min_dpi,
            min(self.settings.max_dpi, target_dpi),
        )
        logger.debug(
            "Selected rasterisation DPI {} for page {} (long_edge_inches={:.2f})",
            clamped_dpi,
            page.number + 1,
            long_edge_inches,
        )
        return clamped_dpi

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


class LandingAIDocumentPreprocessor(DocumentPreprocessor):
    def __init__(
        self,
        document: Union[str, bytes, None] = None,
        settings: Optional[PreprocessingSettings] = None,
    ) -> None:
        super().__init__(document=document, settings=settings)

    def preprocess(self) -> bytes:
        document_bytes = self.document_reader(self.document)
        rotated_document_bytes = self.document_rotator(document_bytes)
        converted_document_bytes = self.convert_pdf_to_images_to_pdf(
            rotated_document_bytes)
        skew_corrected_document_bytes = self.skew_detector(
            converted_document_bytes)
        return skew_corrected_document_bytes


class DocumentPreprocessorFactory:
    processor: DocumentPreprocessor

    def __init__(self, service: ServiceType):
        if service == ServiceType.LANDING_AI:
            self.processor = LandingAIDocumentPreprocessor
        else:
            raise ValueError(f"Unsupported service type: {service}")
