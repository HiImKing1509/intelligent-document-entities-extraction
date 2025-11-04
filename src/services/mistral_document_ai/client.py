from typing import Any, Dict, Optional

import requests
from requests import Session

from core import settings
from src.services.mistral_document_ai.params import MistralDAChatCompletionMessageParam


class MistralDocumentAIClient:
    """
    Minimal client for invoking the Azure-hosted Mistral Document AI OCR endpoint.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: float = 60.0,
        session: Optional[Session] = None
    ) -> None:
        self.api_key = api_key or settings.AZURE_MISTRAL_API_KEY
        self.endpoint = (
            endpoint or settings.AZURE_MISTRAL_ENDPOINT).rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def analyze_document(self, params: MistralDAChatCompletionMessageParam) -> Dict[str, Any]:
        """
        Submit a document to the OCR endpoint and return the parsed JSON response.
        """
        payload = params.to_payload()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            response = self.session.post(
                url=self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"Mistral Document AI request failed with status {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except requests.RequestException as exc:
            raise RuntimeError(
                "Failed to reach Mistral Document AI service") from exc

        try:
            return response
        except ValueError as exc:
            raise RuntimeError(
                "Mistral Document AI response could not be decoded as JSON") from exc

    def __repr__(self) -> str:
        return f"MistralDocumentAIClient(endpoint={self.endpoint})"
