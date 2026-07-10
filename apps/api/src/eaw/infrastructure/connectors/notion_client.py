"""Notion API client (internal integration token)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx

from eaw.domain.common.errors import AppError, ValidationAppError


@dataclass
class NotionPage:
    id: str
    title: str
    url: Optional[str]
    last_edited_time: Optional[str]
    object_type: str  # page | database


class NotionClient:
    def __init__(
        self,
        token: str,
        *,
        api_base: str = "https://api.notion.com",
        api_version: str = "2022-06-28",
    ) -> None:
        if not token or not token.strip():
            raise ValidationAppError("Notion integration token is required")
        self.token = token.strip()
        self.api_base = api_base.rstrip("/")
        self.api_version = api_version

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self.api_version,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = path if path.startswith("http") else f"{self.api_base}{path}"
        with httpx.Client(timeout=60.0) as client:
            resp = client.request(method, url, headers=self._headers(), **kwargs)
        if resp.status_code == 401:
            raise AppError("Notion authentication failed — check integration token")
        if resp.status_code == 403:
            raise AppError("Notion access forbidden — share pages with the integration")
        if resp.status_code >= 400:
            raise AppError(
                f"Notion API error {resp.status_code}",
                details={"body": resp.text[:400]},
            )
        if resp.status_code == 204:
            return None
        return resp.json()

    def verify_token(self) -> dict:
        # List users is a light auth check; fallback to search empty
        try:
            return self._request("GET", "/v1/users/me")
        except AppError:
            # Older tokens / permissions — use search
            data = self.search(query="", page_size=1)
            return {"bot": True, "search_ok": True, "results": len(data)}

    def search(
        self, *, query: str = "", page_size: int = 20, start_cursor: Optional[str] = None
    ) -> list[dict]:
        body: dict[str, Any] = {
            "page_size": min(page_size, 100),
            "filter": {"value": "page", "property": "object"},
        }
        if query:
            body["query"] = query
        if start_cursor:
            body["start_cursor"] = start_cursor
        data = self._request("POST", "/v1/search", json=body)
        return list(data.get("results") or [])

    def list_pages(self, *, max_pages: int = 50) -> list[NotionPage]:
        results: list[NotionPage] = []
        cursor: Optional[str] = None
        while len(results) < max_pages:
            body: dict[str, Any] = {
                "page_size": min(25, max_pages - len(results)),
                "filter": {"value": "page", "property": "object"},
            }
            if cursor:
                body["start_cursor"] = cursor
            data = self._request("POST", "/v1/search", json=body)
            for item in data.get("results") or []:
                results.append(self._to_page(item))
                if len(results) >= max_pages:
                    break
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break
        return results

    def _to_page(self, item: dict) -> NotionPage:
        title = self._extract_title(item)
        return NotionPage(
            id=item.get("id") or "",
            title=title or "Untitled",
            url=item.get("url"),
            last_edited_time=item.get("last_edited_time"),
            object_type=item.get("object") or "page",
        )

    @staticmethod
    def _extract_title(item: dict) -> str:
        props = item.get("properties") or {}
        for prop in props.values():
            if prop.get("type") == "title":
                parts = prop.get("title") or []
                return "".join(p.get("plain_text") or "" for p in parts).strip()
        # child page
        if item.get("object") == "page":
            parent = item.get("parent") or {}
            if parent.get("type") == "page_id":
                return "Child page"
        return "Untitled"

    def get_page(self, page_id: str) -> dict:
        return self._request("GET", f"/v1/pages/{page_id}")

    def get_block_children(self, block_id: str, *, max_blocks: int = 200) -> list[dict]:
        blocks: list[dict] = []
        cursor: Optional[str] = None
        while len(blocks) < max_blocks:
            params: dict[str, Any] = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            data = self._request(
                "GET", f"/v1/blocks/{block_id}/children", params=params
            )
            blocks.extend(data.get("results") or [])
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break
        return blocks

    def page_to_markdown(self, page_id: str, *, title: str = "") -> str:
        blocks = self.get_block_children(page_id)
        lines: list[str] = []
        if title:
            lines.append(f"# {title}")
            lines.append("")
        for b in blocks:
            text = self._block_to_text(b)
            if text:
                lines.append(text)
        return "\n".join(lines).strip()

    def _rich_text(self, rich: list[dict] | None) -> str:
        if not rich:
            return ""
        return "".join(t.get("plain_text") or "" for t in rich)

    def _block_to_text(self, block: dict) -> str:
        btype = block.get("type") or ""
        data = block.get(btype) or {}
        if btype in {
            "paragraph",
            "heading_1",
            "heading_2",
            "heading_3",
            "bulleted_list_item",
            "numbered_list_item",
            "quote",
            "callout",
            "to_do",
        }:
            text = self._rich_text(data.get("rich_text"))
            if btype == "heading_1":
                return f"# {text}"
            if btype == "heading_2":
                return f"## {text}"
            if btype == "heading_3":
                return f"### {text}"
            if btype == "bulleted_list_item":
                return f"- {text}"
            if btype == "numbered_list_item":
                return f"1. {text}"
            if btype == "quote":
                return f"> {text}"
            if btype == "to_do":
                mark = "x" if data.get("checked") else " "
                return f"- [{mark}] {text}"
            return text
        if btype == "code":
            lang = data.get("language") or ""
            code = self._rich_text(data.get("rich_text"))
            return f"```{lang}\n{code}\n```"
        if btype == "divider":
            return "---"
        if btype == "child_page":
            return f"[Child page: {data.get('title') or 'Untitled'}]"
        return ""
