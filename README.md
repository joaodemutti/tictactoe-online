# Tic-Tac-Toe Online

Real-time multiplayer Tic-Tac-Toe in the browser. Two players connect, pick their roles, and play — with live move sync, win/draw detection, and a chat drawer.

## Stack

- **Backend** — Python, FastAPI, asyncio, WebSockets
- **Database** — PostgreSQL 16 (via asyncpg + SQLAlchemy async)
- **Auth** — JWT in an httponly cookie (bcrypt passwords)
- **Frontend** — Jinja2 templates, Tailwind CSS (CDN), GSAP animations, plain JavaScript
- **i18n** — English and Brazilian Portuguese (server-side, switchable per user)
- **Edge** — Runs behind a Cloudflare Tunnel; CORS + WebSocket Origin checks restrict access to the app's own origin
- **Bot protection** — Cloudflare Turnstile on login/signup (optional in dev)
- **Dev DB** — Docker Compose

## Features

- Signup / login with optional avatar upload (cropped + resized to WebP)
- Cloudflare Turnstile captcha on login/signup (skipped when no secret is set)
- Language switch between English and Portuguese, remembered per account
- Invite any online player to a game
- Role selection (X, O, or random) with a 5-second countdown
- Animated board: X drawn with two SVG lines, O with a circle stroke — both using GSAP
- Win and draw detection with a full-screen overlay, auto-redirects to hub after 4 s
- Direct messages between players with a slide-in chat drawer and unread badge

## Prerequisites

- Python 3.11+
- Docker (for the local Postgres container)

## Getting started

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\Activate.ps1  # Windows PowerShell

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env
cp .env.example .env           # macOS/Linux
# Copy-Item .env.example .env  # Windows

# 4. Start PostgreSQL
docker compose up -d

# 5. Grant DB privileges (run once, after creating the tictactoe_user / tictactoe_app roles)
sudo -u postgres psql -d tictactoe -f scripts/roles.sql

# 6. Run migrations
alembic upgrade head

# 7. Start the server
uvicorn app.main:app --reload
```

Open <http://localhost:8000> in two separate browser profiles or tabs to test multiplayer.

## Environment variables

| Variable | Description | Default in `.env.example` |
|---|---|---|
| `DATABASE_URL` | App runtime connection (role `tictactoe_app`, DML only) | `postgresql+asyncpg://tictactoe_app:CHANGE_ME@localhost:5432/tictactoe` |
| `MIGRATION_DATABASE_URL` | Alembic connection (role `tictactoe_user`, owner/DDL) | `postgresql+asyncpg://tictactoe_user:CHANGE_ME@localhost:5432/tictactoe` |
| `JWT_SECRET` | Secret key for signing tokens | `change-me-in-production` |
| `JWT_EXPIRE_MINUTES` | Token lifetime | `10080` (7 days) |
| `ALLOWED_ORIGINS` | Comma-separated origins allowed for CORS and the WebSocket Origin check. In production set this to the domain only. | `https://jogodavelha-online.com.br,http://localhost:8000,http://127.0.0.1:8000` |
| `TURNSTILE_SITE_KEY` | Cloudflare Turnstile public key (rendered in the frontend widget). Empty hides the widget. | _(empty)_ |
| `TURNSTILE_SECRET_KEY` | Turnstile private key (backend verification). Empty skips verification (dev). | _(empty)_ |

> Behind Cloudflare, the real client IP arrives in the `CF-Connecting-IP` header; `get_client_ip()` reads it (falling back to the socket peer in dev) and is used for Turnstile verification.

## Project layout

```
app/
  config.py          # Pydantic Settings (reads .env)
  database.py        # Async engine + session factory
  models.py          # ORM models: User, Match, MatchPlayer, Move, Message
  schemas.py         # Pydantic request/response models
  auth.py            # JWT + bcrypt helpers, verify_turnstile()
  deps.py            # FastAPI dependencies (get_current_user, get_db, get_client_ip, ws_origin_allowed)
  i18n.py            # EN / PT-BR translations + language detection
  templating.py      # Jinja2 setup + _ctx() template context helper
  main.py            # App entry point, CORS middleware, router mounts
  routes/
    auth.py          # /login, /signup, /logout, /language, /profile, avatar upload
    hub.py           # GET / (hub page), player search
    match.py         # POST /match/invite, GET /match/{id}
    messages.py      # GET /messages/contacts, GET /messages/{user_id}
  ws/
    manager.py       # ConnectionManager — hub + match WebSocket rooms
    hub.py           # WS /ws/hub — online players, invites, chat
    match.py         # WS /ws/match/{id} — role selection, moves, game over
    chat.py          # Shared send_message / mark_read helpers
  services/          # DB-access logic for users, games, and messages
  game/
    logic.py         # check_winner(), is_draw()
static/
  js/                # hub.js, match.js — WebSocket clients
  avatars/           # Uploaded user avatars (WebP)
templates/
  base.html          # Shared layout + chat drawer
  hub.html           # Online players grid
  match.html         # Game board, role modal, game-over overlay
  auth/
    login.html       # Includes the Turnstile widget when configured
    signup.html      # Avatar picker + Turnstile widget
```

## Security notes

- **CORS** — `CORSMiddleware` restricts HTTP requests to `ALLOWED_ORIGINS` (credentials enabled, `GET`/`POST` only).
- **WebSocket Origin** — every WS handshake (`/ws/hub`, `/ws/match/{id}`) rejects connections whose `Origin` is absent or not in `ALLOWED_ORIGINS` (CORS does not cover WebSockets).
- **Captcha** — login/signup verify the Turnstile token server-side before checking credentials or creating a user; verification is skipped when `TURNSTILE_SECRET_KEY` is empty.
