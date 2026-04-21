import hashlib
import secrets


from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select
from typing import Annotated
from fastapi import Cookie, FastAPI

templates = Jinja2Templates(directory="templates")
app: FastAPI = FastAPI()


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    pw : str
    messages: list["ChatMessage"] = Relationship(back_populates="user")
    sessions: list["UserSession"] = Relationship(back_populates="user")

class UserSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    token: str
    user_id: int = Field(foreign_key="user.id")
    user: User | None = Relationship(back_populates="sessions")


class ChatMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    message: str
    user_id: int = Field(foreign_key="user.id")
    user: User | None = Relationship(back_populates="messages")


class MessageOut(SQLModel):
    id: int | None
    message: str
    name: str

class PollResponse(SQLModel):
    messages: list[MessageOut]


class SendResponse(SQLModel):
    ok: bool

class LoginInformation(SQLModel):
    name : str
    password : str 



sqlite_url = "sqlite:///store.db"
engine = create_engine(
    sqlite_url,
    connect_args={"check_same_thread": False},
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def create_session_token():
    return secrets.token_hex(32)

# renvoie l'utilisateur associé au token s'il existe 

def get_current_user(session_token: str | None, session: Session) -> User | None:
    if session_token is None:       
        return None
    statement = select(UserSession).where(UserSession.token == session_token)
    user_session = session.exec(statement).first()
    if user_session is None:         
        return None
    return user_session.user         


# les codes ... get 

@app.get("/chat")
async def chat(request: Request, session_token: Annotated[str | None, Cookie()] = None):
    """Serve the chat client page. Returns HTTP 200 on success."""
    with Session(engine) as session:
        user = get_current_user(session_token, session)
        if user is None : 
            return RedirectResponse(url='/login')
    return templates.TemplateResponse(
        request=request,
        name="chat_1.html",
        context={"user_name" : user.name,},
    )

@app.get("/login")
async def login(request: Request):
    """Serve the login page. Returns HTTP 200 on success."""
    return templates.TemplateResponse(
        request=request,
        name="login_0.html",
        context={},
    )

@app.get("/poll", response_model=PollResponse)
async def poll(session_token: Annotated[str | None, Cookie()] = None) -> PollResponse:
    """Return the current message history. Returns HTTP 200 on success."""
    with Session(engine) as session:
        user = get_current_user(session_token, session)
        if user is None : 
            raise HTTPException(status_code=401, detail="Not authenticated")
        statement = select(ChatMessage).order_by(ChatMessage.id)
        messages = session.exec(statement).all()
        result = [MessageOut(id=m.id, message=m.message, name=m.user.name)  for m in messages]
    return PollResponse(messages=result)


# les code ... post 

@app.post("/send", response_model=SendResponse)
async def send(msg: ChatMessage, session_token: Annotated[str | None, Cookie()] = None) -> SendResponse:
    """Store one new chat message. Returns HTTP 200 on success."""
    with Session(engine) as session:
        user = get_current_user(session_token, session)
        if user is None : 
            raise HTTPException(status_code=401, detail="Not authenticated")
        new_msg = ChatMessage(user_id=user.id, message=msg.message)  
        session.add(new_msg)  
        session.commit()
    return SendResponse(ok=True)

@app.post("/login", response_model=SendResponse)
async def login(login_info: LoginInformation, response : Response) -> SendResponse:
    """Store one login information. Returns HTTP 200 on success."""
    with Session(engine) as session:
        selection = select(User).where(User.name == login_info.name)
        existing = session.exec(selection).first()
        if not existing or existing.pw !=hash_password(login_info.password):
            raise HTTPException(status_code=401, detail="Mauvais id et mdp")
        user_session = UserSession(token = create_session_token(), user_id = existing.id)
        session.add(user_session)
        session.commit()
        token_to_send = user_session.token
    response.set_cookie(key="session_token", value=token_to_send, httponly=True)
    return SendResponse(ok=True)

@app.post("/register", response_model=SendResponse)
async def register(login_info: LoginInformation, response : Response) -> SendResponse:
    """Store one register information. Returns HTTP 200 on success."""
    with Session(engine) as session:
        selection = select(User).where(User.name == login_info.name)
        existing = session.exec(selection).first()
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")
        hashed = hash_password(login_info.password)
        log = User(name=login_info.name, pw = hashed)
        session.add(log)
        session.commit()   
        session.refresh(log) 
        user_session = UserSession(token=create_session_token(), user_id=log.id)
        session.add(user_session)
        session.commit()   
    response.set_cookie(key="session_token", value=user_session.token, httponly=True) 
    return SendResponse(ok=True)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()