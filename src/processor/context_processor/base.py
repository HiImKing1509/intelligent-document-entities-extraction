from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ContextProcessor(ABC):
    """Base contract for building document context."""

    def __init__(self, parsed_document: Any, schema: Dict[str, Any]) -> None:
        self.parsed_document = parsed_document
        self.schema = schema or {}

    @abstractmethod
    def process(self, *args, **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        """Build structured context from a parsed document."""
        raise NotImplementedError
