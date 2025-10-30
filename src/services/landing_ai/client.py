from core import settings
from loguru import logger
from landingai_ade import LandingAIADE
from landingai_ade.types.parse_response import ParseResponse


class LandingAIClient:
    def __init__(self) -> None:
        logger.info("Initializing LandingAI Client")
        self.client = LandingAIADE(apikey=settings.LANDING_AI_API_KEY)

    def parse(self, document: bytes) -> ParseResponse:
        response = self.client.parse(
            document_url=None,
            document=document,
            model='dpt-2-latest',
        )
        return response

    def extract(self) -> None:
        pass
