from typing import Optional, Literal

from pydantic import BaseModel, Field, model_validator


class MistralDADocumentParam(BaseModel):
    """
    Represents the document payload expected by the Mistral Document AI endpoint.
    """
    type: Literal["document_url", "document_bytes"] = Field(
        ...,
        description="Origin of the document content sent to the OCR endpoint."
    )
    document_url: Optional[str] = Field(
        default=None,
        description="Required when type is 'document_url'. Supports remote URLs or data URLs."
    )
    document_base64: Optional[str] = Field(
        default=None,
        description="Required when type is 'document_bytes'. Raw base64 payload."
    )

    @model_validator(mode="after")
    def validate_document_payload(self) -> "MistralDADocumentParam":
        if self.type == "document_url" and not self.document_url:
            raise ValueError(
                "document_url must be provided when type is 'document_url'.")

        if self.type == "document_bytes" and not self.document_base64:
            raise ValueError(
                "document_base64 must be provided when type is 'document_bytes'.")

        return self


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
