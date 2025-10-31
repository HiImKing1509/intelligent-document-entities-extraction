from __future__ import annotations

from typing import Dict, Type, Union

from src.models.services import ServiceType

from src.ocr.base import DocumentParser
from src.ocr.landingai_document_parser import LandingAIDocumentParser


class DocumentParserFactory:
    """Factory that returns the appropriate document parser for a service."""

    _PARSER_MAP: Dict[ServiceType, Type[DocumentParser]] = {
        ServiceType.LANDING_AI: LandingAIDocumentParser,
    }

    @classmethod
    def create_parser(cls, service: ServiceType, document: bytes) -> DocumentParser:
        try:
            parser_cls = cls._PARSER_MAP[service]
        except KeyError as error:
            raise ValueError(
                f"No document parser registered for service '{service.value}'."
            ) from error

        return parser_cls(document=document)
