from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Type


class AzureOpenAIChatCompletionMessageParam(BaseModel):
    """
    The parameters for a message to the Azure OpenAI API.
    """
    message_text: List[Dict[str, str]] = Field(
        default=None,
        description="The text of the message to send to the API."
    )
    response_format: Optional[Union[Dict[str, str], Type[BaseModel]]] = Field(
        default={"type": "text"},
        description="The format of the response. It can be a dictionary or a Pydantic model."
    )
    temperature: float = Field(
        default=None,
        description="The temperature setting for the model."
    )
    # max_tokens: Optional[int] = Field(
    #     default=None,
    #     description="The maximum number of tokens in the response."
    # )
    # seed: Optional[int] = Field(
    #     default=None,
    #     description="The seed for the model."
    # )