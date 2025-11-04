from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.processor.context_processor.base import ContextProcessor


class MistralDAContextProcessor(ContextProcessor):
    """Builds contextual step data from Mistral Document AI ParseResponse results."""

    def __init__(self, parsed_document: Dict[str, Any], schema: Dict[str, Any]) -> None:
        if not isinstance(parsed_document, dict):
            raise TypeError(
                "MistralDAContextProcessor expects a Mistral Document AI ParseResponse object."
            )

        super().__init__(parsed_document=parsed_document, schema=schema)

    def process(self) -> Dict[str, List[Dict[str, Any]]]:
        pages = self.parsed_document.get("pages")
        if not pages:
            raise ValueError("Parsed document contains no pages.")

        combined_sections: List[str] = []
        processed_pages: List[Dict[str, Any]] = []

        for index, page in enumerate(pages):
            markdown = page.get("markdown")
            if not isinstance(markdown, str) or not markdown.strip():
                raise ValueError(
                    f"Parsed document page {index} contains no markdown.")

            cleaned_markdown = markdown.strip()
            if combined_sections and not cleaned_markdown.startswith("---"):
                combined_sections.append("")  # preserve spacing between pages
            combined_sections.append(cleaned_markdown)

            processed_pages.append(
                {
                    "page_index": page.get("index", index),
                    "context": cleaned_markdown,
                }
            )

        combined_markdown = "\n".join(combined_sections)

        with open(Path("combined_mistral_output.md"), "w", encoding="utf-8") as f:
            f.write(combined_markdown)

        breakpoint()
