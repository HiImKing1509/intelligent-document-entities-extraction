from base64 import b64encode
from mimetypes import guess_type
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field, model_validator


def _as_data_url(content_type: str, data: bytes) -> str:
    encoded = b64encode(data).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


class MistralDADocumentParam(BaseModel):
    """
    Represents the document payload expected by the Mistral Document AI endpoint.
    """
    type: str = Field(
        default="document_url",
        description="Origin of the document content sent to the OCR endpoint."
    )
    document_url: Optional[str] = Field(
        default=None,
        description="Supports HTTP(S) URLs or base64 data URLs."
    )

    @model_validator(mode="after")
    def validate_document_payload(self) -> "MistralDADocumentParam":
        if not self.document_url:
            raise ValueError("document_url must be provided.")

        if not self.document_url.startswith(("http://", "https://", "data:")):
            raise ValueError("document_url must be HTTP(S) or data URL.")

        return self

    @classmethod
    def from_file(cls, file_path: str, content_type: Optional[str] = None) -> "MistralDADocumentParam":
        """
        Build a document parameter by reading the supplied file and encoding it as a data URL.
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Document path {file_path} does not exist or is not a file.")

        inferred_content_type = content_type or guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        return cls(document_url=_as_data_url(inferred_content_type, data))

    @classmethod
    def from_http_url(
        cls,
        url: str,
        content_type: Optional[str] = None,
        timeout: float = 30.0
    ) -> "MistralDADocumentParam":
        """
        Fetch the document located at the provided HTTP(S) URL and encode it as a data URL.
        """
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("URL scheme must be HTTP or HTTPS.")

        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        resolved_content_type = content_type or response.headers.get("Content-Type") or "application/octet-stream"
        return cls(document_url=_as_data_url(resolved_content_type, response.content))

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> "MistralDADocumentParam":
        """
        Encode raw bytes as a data URL.
        """
        return cls(document_url=_as_data_url(content_type, data))


class MistralDAChatCompletionMessageParam(BaseModel):
    """
    The parameters for a message to the Mistral Document AI API.
    """
    model: str = Field(
        default="mistral-document-ai-2505",
        description="Target Mistral Document AI model hosted on Azure."
    )
    document: MistralDADocumentParam = Field(
        ...,
        description="Document payload definition consumed by the OCR endpoint."
    )
    include_image_base64: bool = Field(
        default=True,
        description="Controls whether rendered page images are embedded in the response."
    )

    def to_payload(self) -> dict:
        """
        Convert the parameter model into a JSON-serialisable payload for the API.
        """
        return self.model_dump(exclude_none=True)
