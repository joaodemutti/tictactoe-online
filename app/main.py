from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.deps import RequiresLogin
from app.routes import auth, hub, match, messages
from app.ws import hub as ws_hub
from app.ws import match as ws_match

app = FastAPI()

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
