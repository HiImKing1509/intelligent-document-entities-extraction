from __future__ import annotations

from typing import Type, Dict, List, Any
from src.models.services import ServiceType

from src.entity_extractor.base import EntityExtractor
from src.entity_extractor._landing_ai import LandingAIEntityExtractor


class EntityExtractorFactory:
    """Factory that returns the appropriate entity extractor for a service."""

    _EXTRACTOR_MAP: Dict[ServiceType, Type[EntityExtractor]] = {
        ServiceType.LANDING_AI: LandingAIEntityExtractor,
    }

    @classmethod
    def create_extractor(
            cls,
            *,
            service: ServiceType,
            contexts: Dict[str, List[Dict[str, Any]]]
    ) -> EntityExtractor:
        try:
            extractor_cls = cls._EXTRACTOR_MAP[service]
        except KeyError as error:
            raise ValueError(
                f"No entity extractor registered for service '{service.value}'."
            ) from error

        return extractor_cls(contexts=contexts)
