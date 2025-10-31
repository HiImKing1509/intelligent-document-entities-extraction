from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:  # pragma: no cover - only used for type hints
    from landingai_ade.types.parse_response import ParseResponse


class DocumentParser(ABC):
    """Base interface for all OCR document parsers."""

    def __init__(self, document: bytes) -> None:
        self.document = document

    @abstractmethod
    def parse(self, plot: bool = False) -> Union[ParseResponse, dict]:
        """Parse the document and optionally return visualization assets."""
