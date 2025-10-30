import pytesseract
from core.configs import Settings

settings = Settings()
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
