from typing import Any, Dict, List, Optional
from openai import AzureOpenAI, AsyncAzureOpenAI

from core import settings

from src.models.services import AzureOpenAIModel
from src.services.llms.azure_openai.params import AzureOpenAIChatCompletionMessageParam
 
class AzureOpenAIClient:
    def __init__(
        self,
        openai_model: AzureOpenAIModel = AzureOpenAIModel.GPT_4O,
        openai_api_version: str = settings.OPENAI_API_VERSION,
        use_async: bool = False
    ):
        """
        Initialize the AzureOpenAI client with the specified settings.
 
        :param openai_model: The model to use for OpenAI.
        :param openai_api_version: The API version to use.
        :param use_async: Whether to use asynchronous API calls.
        """
        _AzureOpenAIClient = AsyncAzureOpenAI if use_async else AzureOpenAI
 
        try:
            self.client = _AzureOpenAIClient(
                api_key=settings.OPENAI_API_KEY,
                api_version=openai_api_version,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
            self.openai_model = openai_model.value
        except Exception as e:
            raise RuntimeError("Error initializing OpenAI client") from e
        
    def structured_output_generate_response(self, params: AzureOpenAIChatCompletionMessageParam) -> Dict[str, Any]:
        """
        Get a Structured Output Azure OpenAI response from the OpenAI API synchronously.

        :param params: The parameters for the message to send to the API.
        :return: A dictionary containing the response content and token usage.
        """
 
        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.openai_model,
                messages=params.message_text,
                temperature=params.temperature,
                response_format=params.response_format,
                # seed=params.seed,
                # max_tokens=params.max_tokens
            )
            return completion.choices[0].message.parsed
        except Exception as e:
            raise RuntimeError("Error fetching GPT response") from e
    
    def __repr__(self) -> str:
        return f"AzureOpenAIClient(openai_model={self.openai_model})"