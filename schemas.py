from typing import Literal

from pydantic import BaseModel, Field , model_validator

class Message(BaseModel):
    role: Literal["user","assistant"]
    text : str = Field(min_length=1 , max_length=4000)

class ChatRequest(BaseModel):
    messages : list[Message] = Field(min_length=1 , max_length=50)
    system : str | None = Field(default=None ,  max_length=2000)
    temperature : float = Field(default=0.7 , ge=0 , le=2)

    @model_validator(mode="after")
    def last_message_must_be_user(self):
        if self.messages[-1].role !="user":
            raise ValueError("The last message must be of user")
        return self

class Usage(BaseModel):
    input_tokens :int
    output_tokens : int
    total_tokens : int

class ChatResponse(BaseModel):
    reply : str
    model : str
    usage :Usage
    latency_ms : int

#uv	run	python	-c	"from	app.schemas	import	ChatRequest;	print('ok')"
