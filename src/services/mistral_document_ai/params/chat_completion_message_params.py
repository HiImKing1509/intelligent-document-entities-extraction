from pydantic import BaseModel, Field


class MistralDADocumentParam(BaseModel):
    """
    Represents the base64 PDF payload consumed by the Mistral Document AI endpoint.
    """
    base64_data: str = Field(
        ...,
        description="Raw base64-encoded PDF bytes."
    )

    def to_payload(self) -> dict:
        """
        Serialise to the document structure expected by the API.
        """
        return {
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{self.base64_data}",
        }


class MistralDAChatCompletionMessageParam(BaseModel):
    """
    Parameters required to invoke the Mistral Document AI endpoint.
    """
    model: str = Field(
        default="mistral-document-ai-2505",
        description="Target Mistral Document AI model hosted on Azure."
    )
    document: MistralDADocumentParam = Field(
        ...,
        description="Base64 document payload definition consumed by the OCR endpoint."
    )
    include_image_base64: bool = Field(
        default=True,
        description="Controls whether rendered page images are embedded in the response."
    )

    def to_payload(self) -> dict:
        """
        Convert the parameter model into a JSON-serialisable payload for the API.
        """
        return {
            "model": self.model,
            "document": self.document.to_payload(),
            "include_image_base64": self.include_image_base64,
        }
