import re
from difflib import SequenceMatcher
from typing import Union, Dict, Any, List
from landingai_ade.types.parse_response import ParseResponse


class DocumentProcessor:
    def __init__(self, document: Union[ParseResponse, dict], schema: Dict[str, Any] = None) -> None:
        self.document = document
        self.schema = schema

    def process(self) -> Dict[str, List[Dict[str, Any]]]:
        if isinstance(self.document, ParseResponse):
            return self._landing_ai_response_processor()
        elif isinstance(self.document, dict):
            pass
        else:
            raise ValueError("Unsupported document type for processing.")
        pass

    def _landing_ai_response_processor(self) -> Dict[str, List[Dict[str, Any]]]:
        processed_steps = []
        chunk_texts = []
        for chunk in self.document.chunks:
            print(f"Chunk type: {chunk.type}")
            if chunk.type in ['scan_code', 'marginalia']:
                continue
            lines = chunk.markdown.split('\n')
            remaining_lines = lines[2:] if len(lines) > 2 else []

            cleaned_lines = []
            for line in remaining_lines:
                cleaned_line = line.lstrip('#').strip()
                cleaned_line = cleaned_line.replace('**', '')
                cleaned_lines.append(cleaned_line)

            chunk_texts.append('\n'.join(cleaned_lines))

        step_markers = []
        schema_steps = self.schema.get("steps", [])
        for i, step in enumerate(schema_steps):
            step_name = step.get("step")
            print(f"Looking for step: {step_name}")
            if not step_name:
                continue

            for j, text in enumerate(chunk_texts):
                if not text:
                    continue
                first_line = text.split('\n')[0]
                if re.match(r'Step\s+[\w\d]+[:.]', first_line):
                    if SequenceMatcher(None, first_line, step_name).ratio() > 0.85:
                        step_markers.append(
                            {'step_index': i, 'chunk_index': j, 'step_name': step_name})
                        break

        step_markers.sort(key=lambda x: x['chunk_index'])

        for i, marker in enumerate(step_markers):
            schema_step_index = marker['step_index']
            start_chunk_index = marker['chunk_index']

            end_chunk_index = len(chunk_texts)
            if i + 1 < len(step_markers):
                end_chunk_index = step_markers[i+1]['chunk_index']

            step_chunks = chunk_texts[start_chunk_index:end_chunk_index]
            context = '\n'.join(step_chunks)

            original_step = schema_steps[schema_step_index]
            processed_steps.append({
                'name': original_step.get("step"),
                'fields': original_step.get("fields", {}),
                'context': context
            })

        return {'steps': processed_steps}
