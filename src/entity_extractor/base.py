from __future__ import annotations

from typing import Dict, List, Any
from abc import ABC, abstractmethod


class EntityExtractor(ABC):
    """Base interface for all entity extractors."""

    def __init__(self, contexts: Dict[str, List[Dict[str, Any]]]) -> None:
        self.contexts = contexts

    @abstractmethod
    def extract(self, *args: Any, **kwargs: Any) -> dict:
        """Extract entities from the provided text and return them in a structured format."""
        raise NotImplementedError
