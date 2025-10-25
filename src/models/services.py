from enum import Enum

class ServiceType(str, Enum):
    LANDING_AI = "LandingAI"
    AZURE_OPENAI = "AzureOpenAI"
    GOOGLE_GEMINI = "GoogleGemini"

class LLMModel(str, Enum):
    pass

class AzureOpenAIModel(LLMModel):
    GPT_4O = "gpt-4o"
    GPT_4_1 = "gpt-4.1"
    GPT_5 = "gpt-5"