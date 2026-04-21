from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Field, Session, SQLModel, create_engine, select

templates = Jinja2Templates(directory="templates")
app: FastAPI = FastAPI()



# A single chat message sent by one user.
class ChatMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    message: str

# The response returned by the polling endpoint.
class PollResponse(SQLModel):
    messages: list[ChatMessage]


# Small response model used after a message is accepted.
class SendResponse(SQLModel):
    ok: bool


sqlite_url = "sqlite:///store.db"
engine = create_engine(
    sqlite_url,
    connect_args={"check_same_thread": False},
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

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
    with Session(engine) as session:
        statement = select(ChatMessage).order_by(ChatMessage.id)
        messages = session.exec(statement).all()
    return PollResponse(messages=list(messages))

@app.post("/send", response_model=SendResponse)
async def send(msg: ChatMessage) -> SendResponse:
    """Store one new chat message. Returns HTTP 200 on success."""
    with Session(engine) as session:
        session.add(msg)
        session.commit()
    return SendResponse(ok=True)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


