import json
from typing import Dict, List, Any, Union
from loguru import logger

from core import settings
from src.models.services import ServiceType, AzureOpenAIModel
from src.processor import StructuredJSON2PydanticConverter
from src.services.llms.azure_openai.params import AzureOpenAIChatCompletionMessageParam
from src.services.llms.azure_openai import AzureOpenAIClient

class EntitiesExtractor:

    _LANDING_AI_SYSTEM_PROMPT = (
        "You are a document intelligence AI assistant in entities extraction. "
        "Your task is to identify and extract the required entities from the provided text, and structure your response strictly according to the predefined schema.\n"
        "**Entities extraction instructions:**\n"
        "- Extract exactly texts present in context (without adding, omitting or modifying) with plausible handled stripped spacing.\n"
        "- **option <field name> []** represents a checkbox, extract as boolean value: true if checked, false if not checked. Otherwise, consecutive [] represent an empty filled box.\n"
        "- Ensure number of values, don't omit any values, even if they are empty and maintain the order of elements in lists. "
        "There are groups of fields representing lists that their length need to be equal, these fields are adjacent in the image. This a group of list: [Security name, Code, No. of share, Redeem All], [From $, to $, %p.a], the number of elements of those sets need to be equal.\n"
        "\n"
        "**Entities extraction response format scenarios:**\n"
        "**- Checkboxes: True/False values:**\n"
        "   + option `field_name` [] -> False.\n"
        "   + option `field_name` [x] -> True.\n"
        "**- Monetary values: Keep dots and commas. Correct stripped values without dollar ($) sign**\n"
        "   + $ a , b c d . e f -> a,bcd.ef\n"
        "   + $ [] or [0.00] -> empty (\"\") value\n"
        "**- Percentage values: Correct stripped values without percentage (%) sign**\n"
        "   + a b c % -> abc\n"
        "   + $ [] or [0.00] -> empty (\"\") value\n"
        "**- Date values: Year can be 2 or 4 digits - Get exactly what they are in context. Correct stripped values**\n"
        "   + D (D) / M (M) / Y (Y) -> D(D)/M(M)/Y(Y)\n"
        "   + D D / M M / Y Y Y Y -> DD/MM/YYYY\n"
        "   + D D - M M - Y Y Y Y -> DD-MM-YYYY\n"
        "**- List values: Maintain the order of elements in lists as in the context**\n"
        "   + item1, item2, item3 -> [item1, item2, item3]\n"
        "   + [a] [,] [b] [c] [d] ... -> Element 'a,bcd' in list\n"
        "   + [ ] [ ] [ ] ... -> An empty element in the list\n"
        "   + 0.00 -> An empty element (\"\") in the list\n"
        "\n"
        "Your primary goal is to extract accurate entities from the provided text, and produce clean, structured output ready for downstream processing.\n"
    )

    def __init__(
            self, 
            contexts: Dict[str, List[Dict[str, Any]]],
            service: str = ServiceType.LANDING_AI,
    ) -> None:
        self.contexts = contexts
        self.service = service
        if service == ServiceType.LANDING_AI:
            self._SYSTEM_PROMPT = self._LANDING_AI_SYSTEM_PROMPT
        else:
            raise ValueError(f"Unsupported service type: {service}")

    @staticmethod
    def _post_process_extracted_value(value: Union[str, bool, List[str], List[bool]]) -> Any:
        """
        Post-process the extracted value based on its type.
        """
        PLACEHOLDER_STRINGS = ["0.00", "()-"]
        if isinstance(value, str):
            if value.replace(" ", "") in PLACEHOLDER_STRINGS:
                return ""
            else:
                return value
        elif isinstance(value, bool):
            return value
        elif isinstance(value, list):
            processed_list = []
            for item in value:
                if isinstance(item, str):
                    if item.replace(" ", "") in PLACEHOLDER_STRINGS:
                        processed_list.append("")
                    else:
                        processed_list.append(item)
                elif isinstance(item, bool):
                    processed_list.append(item)
            return processed_list
        else:
            return value

    @staticmethod
    def _structured_entity_extraction(json_entity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract entities from the given JSON structure.
        """
        extracted_entities = []
        for key, value in json_entity.items():
            value = EntitiesExtractor._post_process_extracted_value(value)
            if isinstance(value, (str, bool)):
                entity = {
                    "name": key,
                    "values": [{"value": value}],
                    "type": "string" if isinstance(value, str) else "boolean"
                }
            elif isinstance(value, list):
                values = [{"value": item} for item in value]
                value_type = "list[string]" if all(isinstance(item, str) for item in value) else "list[boolean]" if all(isinstance(item, bool) for item in value) else "list[mixed]" 
                entity = {
                    "name": key,
                    "values": values,
                    "type": value_type
                }
            else:
                continue
            extracted_entities.append(entity)
        return extracted_entities

    def extract(self) -> Dict[str, List[Dict[str, Any]]]:

        response = {
            "steps": []
        }

        converter = StructuredJSON2PydanticConverter()
        azure_openai_client = AzureOpenAIClient(
            openai_model=AzureOpenAIModel.GPT_4O,
            openai_api_version=settings.OPENAI_API_VERSION,
            use_async=False,
        )

        steps = self.contexts.get("steps", [])
        if not steps:
            logger.warning("No steps found in contexts for entity extraction.")
            return None
        
        for i, step in enumerate(steps):
            step_name = step.get('name', f'step_{i+1}')
            step_fields = step.get('fields', [])
            if step_fields:
                logger.info(f"Extracting entities for step: {step_name}")
                pydantic_model = converter.convert(step_fields)
                params = AzureOpenAIChatCompletionMessageParam(
                    message_text=[
                        {
                            "role": "system", 
                            "content": self._SYSTEM_PROMPT
                        },
                        {
                            "role": "user", 
                            "content": (
                                f"Extract the following entities from the text below and format them according to the schema:\n\n"
                                f"Text:\n{step.get('context', '')}\n\n"
                            )
                        }
                    ],
                    response_format=pydantic_model,
                    temperature=0.25,
                )

                gpt_response = azure_openai_client.structured_output_generate_response(params=params)
                if gpt_response:
                    json_gpt_response = converter.serialize(
                        model_class=pydantic_model,
                        data=gpt_response,
                        verbose=False
                    )
                    print(f"Context:\n{step.get('context', '')}\n")
                    print(json.dumps(json_gpt_response, indent=4))

                    response["steps"].append({
                        "step": step.get("name"),
                        "fields": self._structured_entity_extraction(json_gpt_response)
                    })
                else:
                    logger.warning(f"No response from LLM for step: {step_name}")
                    response["steps"].append({
                        "step": step.get("name"),
                        "fields": []
                    })
        return response