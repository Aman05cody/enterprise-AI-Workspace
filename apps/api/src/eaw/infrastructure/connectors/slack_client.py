"""Slack Web API client (bot token)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx

from eaw.domain.common.errors import AppError, ValidationAppError


@dataclass
class SlackChannel:
    id: str
    name: str
    is_private: bool
    is_archived: bool
    num_members: Optional[int]
    topic: Optional[str]
    purpose: Optional[str]


class SlackClient:
    def __init__(
        self, token: str, *, api_base: str = "https://slack.com/api"
    ) -> None:
        if not token or not token.strip():
            raise ValidationAppError("Slack bot token is required")
        self.token = token.strip()
        self.api_base = api_base.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _post(self, method: str, payload: Optional[dict] = None) -> dict:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{self.api_base}/{method}",
                headers=self._headers(),
                json=payload or {},
            )
        if resp.status_code >= 400:
            raise AppError(
                f"Slack HTTP error {resp.status_code}",
                details={"body": resp.text[:300]},
            )
        data = resp.json()
        if not data.get("ok"):
            err = data.get("error") or "unknown_error"
            raise AppError(f"Slack API error: {err}", details=data)
        return data

    def _get(self, method: str, params: Optional[dict] = None) -> dict:
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(
                f"{self.api_base}/{method}",
                headers=self._headers(),
                params=params or {},
            )
        if resp.status_code >= 400:
            raise AppError(
                f"Slack HTTP error {resp.status_code}",
                details={"body": resp.text[:300]},
            )
        data = resp.json()
        if not data.get("ok"):
            err = data.get("error") or "unknown_error"
            raise AppError(f"Slack API error: {err}", details=data)
        return data

    def verify_token(self) -> dict:
        return self._post("auth.test")

    def list_channels(self, *, limit: int = 100) -> list[SlackChannel]:
        channels: list[SlackChannel] = []
        cursor: Optional[str] = None
        while len(channels) < limit:
            params: dict[str, Any] = {
                "types": "public_channel,private_channel",
                "exclude_archived": True,
                "limit": min(100, limit - len(channels)),
            }
            if cursor:
                params["cursor"] = cursor
            data = self._get("conversations.list", params)
            for ch in data.get("channels") or []:
                channels.append(
                    SlackChannel(
                        id=ch["id"],
                        name=ch.get("name") or ch["id"],
                        is_private=bool(ch.get("is_private")),
                        is_archived=bool(ch.get("is_archived")),
                        num_members=ch.get("num_members"),
                        topic=(ch.get("topic") or {}).get("value"),
                        purpose=(ch.get("purpose") or {}).get("value"),
                    )
                )
            cursor = (data.get("response_metadata") or {}).get("next_cursor") or None
            if not cursor:
                break
        return channels

    def history(
        self,
        channel_id: str,
        *,
        limit: int = 200,
        oldest: Optional[str] = None,
    ) -> list[dict]:
        messages: list[dict] = []
        cursor: Optional[str] = None
        while len(messages) < limit:
            params: dict[str, Any] = {
                "channel": channel_id,
                "limit": min(200, limit - len(messages)),
            }
            if oldest:
                params["oldest"] = oldest
            if cursor:
                params["cursor"] = cursor
            data = self._get("conversations.history", params)
            batch = data.get("messages") or []
            messages.extend(batch)
            cursor = (data.get("response_metadata") or {}).get("next_cursor") or None
            if not cursor or not batch:
                break
        # chronological
        messages.reverse()
        return messages

    def replies(self, channel_id: str, thread_ts: str, *, limit: int = 50) -> list[dict]:
        data = self._get(
            "conversations.replies",
            {"channel": channel_id, "ts": thread_ts, "limit": limit},
        )
        return list(data.get("messages") or [])

    @staticmethod
    def messages_to_text(messages: list[dict], *, channel_name: str = "") -> str:
        lines = []
        if channel_name:
            lines.append(f"# Slack channel #{channel_name}")
            lines.append("")
        for m in messages:
            if m.get("subtype") in {"channel_join", "channel_leave", "bot_message"}:
                # keep bot messages if they have text
                if m.get("subtype") != "bot_message":
                    continue
            user = m.get("user") or m.get("username") or "user"
            text = (m.get("text") or "").strip()
            if not text:
                continue
            ts = m.get("ts") or ""
            lines.append(f"[{ts}] {user}: {text}")
        return "\n".join(lines)
