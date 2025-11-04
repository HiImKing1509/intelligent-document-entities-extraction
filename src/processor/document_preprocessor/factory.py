from typing import Any, Dict, Type

from src.models.services import ServiceType
from src.processor.document_preprocessor.base import DocumentPreprocessor
from src.processor.document_preprocessor._landing_ai import LandingAIDocumentPreprocessor
from src.processor.document_preprocessor._mistral_document_ai import MistralDocumentAIPreprocessor


class DocumentPreprocessorFactory:
    _PROCESSOR_MAP: Dict[ServiceType, Type[DocumentPreprocessor]] = {
        ServiceType.LANDING_AI: LandingAIDocumentPreprocessor,
        ServiceType.MISTRAL_DOCUMENT_AI: MistralDocumentAIPreprocessor,
    }

    @classmethod
    def create_processor(
        cls,
        *,
        service: ServiceType,
        document: Any,
    ) -> DocumentPreprocessor:
        try:
            processor_cls = cls._PROCESSOR_MAP[service]
        except KeyError as error:
            raise ValueError(
                f"No document processor registered for service '{service.value}'."
            ) from error

        return processor_cls(document=document)
