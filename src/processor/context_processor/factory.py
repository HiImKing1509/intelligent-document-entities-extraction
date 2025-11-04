from __future__ import annotations

from typing import Any, Dict, Type

from src.models.services import ServiceType
from src.processor.context_processor.base import ContextProcessor
from src.processor.context_processor._landingai import LandingAIContextProcessor
from src.processor.context_processor._mistral_document_ai import MistralDAContextProcessor


class ContextProcessorFactory:
    """Factory for instantiating service specific context processors."""

    _PROCESSOR_MAP: Dict[ServiceType, Type[ContextProcessor]] = {
        ServiceType.LANDING_AI: LandingAIContextProcessor,
        ServiceType.MISTRAL_DOCUMENT_AI: MistralDAContextProcessor,
    }

    @classmethod
    def create_processor(
        cls,
        *,
        service: ServiceType,
        parsed_document: Any,
        schema: Dict[str, Any],
    ) -> ContextProcessor:
        try:
            processor_cls = cls._PROCESSOR_MAP[service]
        except KeyError as error:
            raise ValueError(
                f"No context processor registered for service '{service.value}'."
            ) from error

        return processor_cls(parsed_document=parsed_document, schema=schema)
