from typing import Optional, Union

from src.processor.document_preprocessor.base import DocumentPreprocessor, PreprocessingSettings


class MistralDocumentAIPreprocessor(DocumentPreprocessor):
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
