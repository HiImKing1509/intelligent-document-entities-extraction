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

    @abstractmethod
    def preprocess(self) -> bytes:
        # Implement your preprocessing logic here
        pass


class LandingAIDocumentPreprocessor(DocumentPreprocessor):
    def __init__(self, document: Union[str, bytes] = None):
        super().__init__(document)

    def preprocess(self) -> bytes:
        document_bytes = self.document_reader(self.document)
        # with open("original_doc.pdf", "wb") as f:
        #     f.write(document_bytes)
        rotated_document_bytes = self.document_rotator(document_bytes)
        with open("rotated_document.pdf", "wb") as f:
            f.write(rotated_document_bytes)
        return rotated_document_bytes

# Document preprocessor factory class


class DocumentPreprocessorFactory:
    processor: DocumentPreprocessor

    def __init__(self, service: ServiceType):
        if service == ServiceType.LANDING_AI:
            self.processor = LandingAIDocumentPreprocessor
        else:
            raise ValueError(f"Unsupported service type: {service}")
