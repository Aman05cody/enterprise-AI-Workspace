"""Jira Cloud REST API client (email + API token)."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import quote

import httpx

from eaw.domain.common.errors import AppError, ValidationAppError


@dataclass
class JiraProject:
    id: str
    key: str
    name: str
    project_type: Optional[str]
    style: Optional[str]


class JiraClient:
    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        api_token: str,
    ) -> None:
        if not base_url or not email or not api_token:
            raise ValidationAppError("Jira base_url, email, and api_token are required")
        self.base_url = base_url.rstrip("/")
        self.email = email.strip()
        self.api_token = api_token.strip()

    def _headers(self) -> dict[str, str]:
        basic = base64.b64encode(
            f"{self.email}:{self.api_token}".encode("utf-8")
        ).decode("ascii")
        return {
            "Authorization": f"Basic {basic}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(url, headers=self._headers(), params=params)
        if resp.status_code == 401:
            raise AppError("Jira authentication failed — check email/API token")
        if resp.status_code >= 400:
            raise AppError(
                f"Jira API error {resp.status_code}",
                details={"body": resp.text[:400]},
            )
        if resp.status_code == 204:
            return None
        return resp.json()

    def _post(self, path: str, json_body: dict) -> Any:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=self._headers(), json=json_body)
        if resp.status_code >= 400:
            raise AppError(
                f"Jira API error {resp.status_code}",
                details={"body": resp.text[:400]},
            )
        return resp.json()

    def verify(self) -> dict:
        return self._get("/rest/api/3/myself")

    def list_projects(self, *, max_results: int = 50) -> list[JiraProject]:
        data = self._get(
            "/rest/api/3/project/search",
            params={"maxResults": max_results},
        )
        values = data.get("values") if isinstance(data, dict) else data
        projects: list[JiraProject] = []
        for p in values or []:
            projects.append(
                JiraProject(
                    id=str(p.get("id")),
                    key=p.get("key") or "",
                    name=p.get("name") or "",
                    project_type=p.get("projectTypeKey"),
                    style=p.get("style"),
                )
            )
        return projects

    def search_issues(
        self,
        jql: str,
        *,
        max_results: int = 50,
        fields: Optional[list[str]] = None,
    ) -> list[dict]:
        field_list = fields or [
            "summary",
            "description",
            "status",
            "assignee",
            "reporter",
            "priority",
            "issuetype",
            "created",
            "updated",
            "comment",
            "labels",
            "parent",
            "sprint",
        ]
        # Prefer new search endpoint; fall back to classic
        try:
            data = self._post(
                "/rest/api/3/search/jql",
                {
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": field_list,
                },
            )
            return list(data.get("issues") or data.get("values") or [])
        except AppError:
            data = self._get(
                "/rest/api/3/search",
                params={
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": ",".join(field_list),
                },
            )
            return list(data.get("issues") or [])

    def get_issue(self, issue_key: str) -> dict:
        return self._get(
            f"/rest/api/3/issue/{quote(issue_key)}",
            params={
                "fields": "summary,description,status,assignee,reporter,priority,issuetype,created,updated,comment,labels,parent,subtasks"
            },
        )

    def list_boards(self, project_key: Optional[str] = None) -> list[dict]:
        params: dict[str, Any] = {"maxResults": 50}
        if project_key:
            params["projectKeyOrId"] = project_key
        try:
            data = self._get("/rest/agile/1.0/board", params=params)
            return list(data.get("values") or [])
        except AppError:
            return []

    def list_sprints(self, board_id: int | str, *, state: str = "active,closed") -> list[dict]:
        data = self._get(
            f"/rest/agile/1.0/board/{board_id}/sprint",
            params={"state": state, "maxResults": 20},
        )
        return list(data.get("values") or [])

    def sprint_issues(self, sprint_id: int | str, *, max_results: int = 50) -> list[dict]:
        data = self._get(
            f"/rest/agile/1.0/sprint/{sprint_id}/issue",
            params={
                "maxResults": max_results,
                "fields": "summary,status,assignee,issuetype,priority,story_points",
            },
        )
        return list(data.get("issues") or [])

    @staticmethod
    def adf_to_text(node: Any) -> str:
        """Flatten Atlassian Document Format to plain text."""
        if node is None:
            return ""
        if isinstance(node, str):
            return node
        if isinstance(node, list):
            return "\n".join(JiraClient.adf_to_text(n) for n in node)
        if not isinstance(node, dict):
            return str(node)
        if node.get("type") == "text":
            return node.get("text") or ""
        content = node.get("content")
        if content:
            parts = [JiraClient.adf_to_text(c) for c in content]
            joined = "".join(parts) if node.get("type") in {"paragraph", "heading"} else "\n".join(
                p for p in parts if p
            )
            return joined
        return ""

    @classmethod
    def issue_to_markdown(cls, issue: dict) -> str:
        key = issue.get("key") or ""
        fields = issue.get("fields") or {}
        summary = fields.get("summary") or ""
        status = (fields.get("status") or {}).get("name")
        itype = (fields.get("issuetype") or {}).get("name")
        assignee = (fields.get("assignee") or {}).get("displayName") or "Unassigned"
        priority = (fields.get("priority") or {}).get("name")
        labels = ", ".join(fields.get("labels") or [])
        desc = cls.adf_to_text(fields.get("description"))
        lines = [
            f"# {key}: {summary}",
            "",
            f"- Type: {itype}",
            f"- Status: {status}",
            f"- Assignee: {assignee}",
            f"- Priority: {priority}",
            f"- Labels: {labels or '—'}",
            "",
            "## Description",
            desc or "_(no description)_",
        ]
        comments = ((fields.get("comment") or {}).get("comments")) or []
        if comments:
            lines.append("")
            lines.append("## Comments")
            for c in comments[-10:]:
                author = (c.get("author") or {}).get("displayName") or "user"
                body = cls.adf_to_text(c.get("body"))
                lines.append(f"### {author}")
                lines.append(body)
        return "\n".join(lines)
