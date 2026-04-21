from collections import deque

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from fastapi import Request

templates = Jinja2Templates(directory="templates")
app: FastAPI = FastAPI()



# A single chat message sent by one user.
class ChatMessage(BaseModel):
    name: str
    message: str


# The response returned by the polling endpoint.
class PollResponse(BaseModel):
    messages: list[ChatMessage]


# Small response model used after a message is accepted.
class SendResponse(BaseModel):
    ok: bool


# In-memory message history for this demo application.
messages: deque[ChatMessage] = deque(maxlen=128)


@app.get("/chat")
async def chat(request: Request):
    """Serve the chat client page. Returns HTTP 200 on success."""
    return templates.TemplateResponse(
        request=request,
        name="chat_0.html",
        context={},
    )

@app.get("/poll", response_model=PollResponse)
async def poll() -> PollResponse:
    """Return the current message history. Returns HTTP 200 on success."""
    return PollResponse(messages=list(messages))

@app.post("/send", response_model=SendResponse)
async def send(msg: ChatMessage) -> SendResponse:
    """Store one new chat message. Returns HTTP 200 on success."""
    messages.append(msg)
    return SendResponse(ok=True)


