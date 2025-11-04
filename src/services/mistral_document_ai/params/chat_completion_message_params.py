from typing import Optional

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


class MistralDADocumentAnnotationFormatParam(BaseModel):
    """
    Defines the document annotation schema consumed by the Document AI endpoint.
    """
    schema: dict = Field(
        ...,
        description="JSON schema describing the expected document-level annotations."
    )

    def to_payload(self) -> dict:
        """
        Serialise the annotation schema to the format required by the API.
        """
        return {
            "type": "json_schema",
            "json_schema": {
                "schema": self.schema,
                "name": "document_annotation",
                "strict": True,
            },
        }


class MistralDABBoxAnnotationFormatParam(BaseModel):
    """
    Defines the bounding-box annotation schema consumed by the Document AI endpoint.
    """
    schema: dict = Field(
        ...,
        description="JSON schema describing the expected bounding-box annotations."
    )

    def to_payload(self) -> dict:
        """
        Serialise the bounding-box annotation schema to the format required by the API.
        """
        return {
            "type": "json_schema",
            "json_schema": {
                "schema": self.schema,
                "name": "bbox_annotation",
                "strict": True,
            },
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
    document_annotation_format: Optional[MistralDADocumentAnnotationFormatParam] = Field(
        default=None,
        description="Optional JSON schema describing the document-level annotations expected from the model."
    )
    bbox_annotation_format: Optional[MistralDABBoxAnnotationFormatParam] = Field(
        default=None,
        description="Optional JSON schema describing the bounding-box annotations expected from the model."
    )
    include_image_base64: bool = Field(
        default=True,
        description="Controls whether rendered page images are embedded in the response."
    )

    def to_payload(self) -> dict:
        """
        Convert the parameter model into a JSON-serialisable payload for the API.
        """
        payload = {
            "model": self.model,
            "document": self.document.to_payload(),
            "include_image_base64": self.include_image_base64,
        }
        if self.document_annotation_format is not None:
            payload["document_annotation_format"] = self.document_annotation_format.to_payload()
        if self.bbox_annotation_format is not None:
            payload["bbox_annotation_format"] = self.bbox_annotation_format.to_payload()
        return payload
