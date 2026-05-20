import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.hub: dict[str, WebSocket] = {}        # user_id → WebSocket
        self.hub_users: dict[str, str] = {}        # user_id → username
        self.usernames: dict[str, str] = {}        # user_id → last known username
        self.avatars: dict[str, str | None] = {}   # user_id → avatar_url
        self.matches: dict[str, dict[str, WebSocket]] = {}  # match_id → {user_id → ws}

    # ── Hub ──────────────────────────────────────────────────────────────────

    async def connect_hub(self, user_id: str, username: str, ws: WebSocket, avatar_url: str | None = None) -> None:
        await ws.accept()
        self.hub[user_id] = ws
        self.hub_users[user_id] = username
        self.usernames[user_id] = username
        self.avatars[user_id] = avatar_url

    def disconnect_hub(self, user_id: str, ws: WebSocket) -> None:
        # Guard: only remove if this is still the active connection for the user
        if self.hub.get(user_id) is ws:
            self.hub.pop(user_id)
            self.hub_users.pop(user_id, None)

    def online_players_list(self) -> list[dict[str, str | bool | None]]:
        online_ids = set(self.hub_users)
        for room in self.matches.values():
            online_ids.update(room)

        playing_ids = {
            user_id
            for room in self.matches.values()
            for user_id in room
        }

        return [
            {
                "user_id": uid,
                "username": self.usernames.get(uid, self.hub_users.get(uid, "Player")),
                "playing": uid in playing_ids,
                "avatar_url": self.avatars.get(uid),
            }
            for uid in online_ids
        ]

    async def broadcast_hub(self, data: dict[str, Any]) -> None:
        payload = json.dumps(data)
        for ws in list(self.hub.values()):
            try:
                await ws.send_text(payload)
            except Exception:
                pass

    async def broadcast_presence(self) -> None:
        payload = json.dumps({
            "type": "players_online",
            "players": self.online_players_list(),
        })
        sockets = list(self.hub.values())
        for room in self.matches.values():
            sockets.extend(room.values())
        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                pass

    async def send_to_user(self, user_id: str, data: dict[str, Any]) -> None:
        ws = self.hub.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                pass

    # ── Match ─────────────────────────────────────────────────────────────────

    async def connect_match(self, match_id: str, user_id: str, username: str, ws: WebSocket) -> None:
        await ws.accept()
        self.usernames[user_id] = username
        if match_id not in self.matches:
            self.matches[match_id] = {}
        self.matches[match_id][user_id] = ws

    def disconnect_match(self, match_id: str, user_id: str, ws: WebSocket) -> None:
        room = self.matches.get(match_id, {})
        if room.get(user_id) is ws:
            room.pop(user_id)
        if not room:
            self.matches.pop(match_id, None)

    def match_user_ids(self, match_id: str) -> list[str]:
        return list(self.matches.get(match_id, {}).keys())

    async def broadcast_match(self, match_id: str, data: dict[str, Any]) -> None:
        payload = json.dumps(data)
        for ws in list(self.matches.get(match_id, {}).values()):
            try:
                await ws.send_text(payload)
            except Exception:
                pass

    async def send_to_match_user(
        self, match_id: str, user_id: str, data: dict[str, Any]
    ) -> None:
        ws = self.matches.get(match_id, {}).get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                pass

    async def send_to_any(self, user_id: str, data: dict[str, Any]) -> None:
        payload = json.dumps(data)
        ws = self.hub.get(user_id)
        if ws:
            try:
                await ws.send_text(payload)
            except Exception:
                pass
        for room in self.matches.values():
            ws = room.get(user_id)
            if ws:
                try:
                    await ws.send_text(payload)
                except Exception:
                    pass


manager = ConnectionManager()
