import argparse
import json
import sys

from src.services.mistral_document_ai import MistralDocumentAIClient
from src.services.mistral_document_ai.params import (
    MistralDAChatCompletionMessageParam,
    MistralDADocumentParam
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke test for the Azure-hosted Mistral Document AI client."
    )
    parser.add_argument(
        "pdf_url",
        help="HTTP(S) or data: URL pointing to the PDF to be analysed."
    )
    parser.add_argument(
        "--no-image-base64",
        action="store_true",
        help="Disable returning page images in base64 within the response."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Request timeout in seconds (default 60)."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    client = MistralDocumentAIClient(timeout=args.timeout)
    params = MistralDAChatCompletionMessageParam(
        document=MistralDADocumentParam(
            type="document_url",
            document_url=args.pdf_url
        ),
        include_image_base64=not args.no_image_base64
    )

    response = client.analyze_document(params)
    print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
