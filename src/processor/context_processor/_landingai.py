from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List

from landingai_ade.types.parse_response import ParseResponse

from src.processor.context_processor.base import ContextProcessor


class LandingAIContextProcessor(ContextProcessor):
    """Builds contextual step data from LandingAI ParseResponse results."""

    def __init__(self, parsed_document: ParseResponse, schema: Dict[str, Any]) -> None:
        if not isinstance(parsed_document, ParseResponse):
            raise TypeError(
                "LandingAIContextProcessor expects a LandingAI ParseResponse object."
            )

        super().__init__(parsed_document=parsed_document, schema=schema)

    def process(self) -> Dict[str, List[Dict[str, Any]]]:
        processed_steps: List[Dict[str, Any]] = []
        chunk_texts: List[str] = []

        for chunk in self.parsed_document.chunks:
            print(f"Chunk type: {chunk.type}")
            if chunk.type in ["scan_code", "marginalia"]:
                continue

            lines = chunk.markdown.split("\n")
            remaining_lines = lines[2:] if len(lines) > 2 else []

            cleaned_lines = []
            for line in remaining_lines:
                cleaned_line = line.lstrip("#").strip()
                cleaned_line = cleaned_line.replace("**", "")
                cleaned_lines.append(cleaned_line)

            chunk_texts.append("\n".join(cleaned_lines))

        schema_steps: List[Dict[str, Any]] = self.schema.get("steps", [])
        step_markers: List[Dict[str, Any]] = self._match_schema_steps_to_chunks(
            chunk_texts=chunk_texts, schema_steps=schema_steps
        )

        for idx, marker in enumerate(step_markers):
            schema_step_index = marker["step_index"]
            start_chunk_index = marker["chunk_index"]
            end_chunk_index = (
                step_markers[idx + 1]["chunk_index"]
                if idx + 1 < len(step_markers)
                else len(chunk_texts)
            )

            step_chunks = chunk_texts[start_chunk_index:end_chunk_index]
            context = "\n".join(step_chunks)

            original_step = schema_steps[schema_step_index]
            processed_steps.append(
                {
                    "name": original_step.get("step"),
                    "fields": original_step.get("fields", {}),
                    "context": context,
                }
            )

        return {"steps": processed_steps}

    def _match_schema_steps_to_chunks(
        self, *, chunk_texts: List[str], schema_steps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        step_markers: List[Dict[str, Any]] = []
        for i, step in enumerate(schema_steps):
            step_name = step.get("step")
            print(f"Looking for step: {step_name}")
            if not step_name:
                continue

            for j, text in enumerate(chunk_texts):
                if not text:
                    continue
                first_line = text.split("\n")[0]
                if re.match(r"Step\s+[\w\d]+[:.]", first_line):
                    similarity = SequenceMatcher(
                        None, first_line, step_name).ratio()
                    if similarity > 0.85:
                        step_markers.append(
                            {
                                "step_index": i,
                                "chunk_index": j,
                                "step_name": step_name,
                            }
                        )
                        break

        step_markers.sort(key=lambda marker: marker["chunk_index"])
        return step_markers
