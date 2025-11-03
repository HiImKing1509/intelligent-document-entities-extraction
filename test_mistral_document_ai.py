import argparse
import json
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from src.services.mistral_document_ai import MistralDocumentAIClient
from src.services.mistral_document_ai.params import (
    MistralDAChatCompletionMessageParam,
    MistralDADocumentParam,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke test for the Azure-hosted Mistral Document AI client."
    )
    parser.add_argument(
        "document_ref",
        help="Path, HTTP(S) URL, or data URL pointing to the document to be analysed.",
    )
    parser.add_argument(
        "--no-image-base64",
        action="store_true",
        help="Disable returning page images in base64 within the response.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Request timeout in seconds (default 60).",
    )
    parser.add_argument(
        "--fetch-timeout",
        type=float,
        default=30.0,
        help="Timeout to use when downloading a remote document (default 30).",
    )
    parser.add_argument(
        "--content-type",
        type=str,
        default=None,
        help="Override content type for the generated data URL.",
    )
    return parser.parse_args()


def resolve_document_param(
    document_ref: str,
    content_type: Optional[str],
    fetch_timeout: float,
) -> MistralDADocumentParam:
    path = Path(document_ref)
    if path.exists():
        return MistralDADocumentParam.from_file(str(path), content_type=content_type)

    if document_ref.startswith("data:"):
        return MistralDADocumentParam(document_url=document_ref)

    parsed = urlparse(document_ref)
    if parsed.scheme in {"http", "https"}:
        return MistralDADocumentParam.from_http_url(
            document_ref,
            content_type=content_type,
            timeout=fetch_timeout,
        )

    raise ValueError(
        "document_ref must be an existing file path, HTTP(S) URL, or a data URL."
    )


def main() -> int:
    args = parse_args()

    document_param = resolve_document_param(
        args.document_ref,
        content_type=args.content_type,
        fetch_timeout=args.fetch_timeout,
    )

    client = MistralDocumentAIClient(timeout=args.timeout)
    params = MistralDAChatCompletionMessageParam(
        document=document_param,
        include_image_base64=not args.no_image_base64,
    )

    response = client.analyze_document(params)
    print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
