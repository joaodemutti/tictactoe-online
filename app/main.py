from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.deps import RequiresLogin
from app.routes import auth, hub, match, messages
from app.ws import hub as ws_hub
from app.ws import match as ws_match

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(hub.router)
app.include_router(match.router)
app.include_router(messages.router)
app.include_router(ws_hub.router)
app.include_router(ws_match.router)


@app.exception_handler(RequiresLogin)
async def requires_login_handler(request: Request, exc: RequiresLogin):
    return RedirectResponse("/login", status_code=303)
