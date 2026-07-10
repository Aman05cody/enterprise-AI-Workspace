"""GitHub REST API client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx

from eaw.domain.common.errors import AppError, ValidationAppError


CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".sql",
    ".sh",
    ".css",
    ".html",
    ".vue",
    ".svelte",
}

SKIP_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    "vendor",
    "__pycache__",
    ".venv",
    "venv",
    "target",
    "coverage",
}


@dataclass
class GitHubRepo:
    id: int
    full_name: str
    name: str
    private: bool
    default_branch: str
    description: Optional[str]
    html_url: str
    language: Optional[str]


class GitHubClient:
    def __init__(self, token: str, *, api_base: str = "https://api.github.com") -> None:
        if not token or not token.strip():
            raise ValidationAppError("GitHub token is required")
        self.token = token.strip()
        self.api_base = api_base.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Enterprise-AI-Workspace",
        }

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        url = path if path.startswith("http") else f"{self.api_base}{path}"
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(url, headers=self._headers(), params=params)
        if resp.status_code == 401:
            raise AppError("GitHub authentication failed — check token scopes")
        if resp.status_code == 403:
            raise AppError("GitHub API rate limited or forbidden", details={"body": resp.text[:300]})
        if resp.status_code == 404:
            raise AppError("GitHub resource not found")
        if resp.status_code >= 400:
            raise AppError(
                f"GitHub API error {resp.status_code}",
                details={"body": resp.text[:400]},
            )
        if resp.status_code == 204:
            return None
        return resp.json()

    def verify_token(self) -> dict:
        return self._get("/user")

    def list_repos(self, *, per_page: int = 50, max_pages: int = 3) -> list[GitHubRepo]:
        repos: list[GitHubRepo] = []
        for page in range(1, max_pages + 1):
            data = self._get(
                "/user/repos",
                params={
                    "per_page": per_page,
                    "page": page,
                    "sort": "updated",
                    "affiliation": "owner,collaborator,organization_member",
                },
            )
            if not data:
                break
            for r in data:
                repos.append(
                    GitHubRepo(
                        id=r["id"],
                        full_name=r["full_name"],
                        name=r["name"],
                        private=bool(r.get("private")),
                        default_branch=r.get("default_branch") or "main",
                        description=r.get("description"),
                        html_url=r.get("html_url") or "",
                        language=r.get("language"),
                    )
                )
            if len(data) < per_page:
                break
        return repos

    def get_tree(self, owner: str, repo: str, branch: str) -> list[dict]:
        data = self._get(f"/repos/{owner}/{repo}/git/trees/{branch}", params={"recursive": "1"})
        return list(data.get("tree") or []) if data else []

    def get_file_content(self, owner: str, repo: str, path: str, ref: str) -> tuple[str, str]:
        """Return (decoded_text, html_or_api_url)."""
        import base64

        data = self._get(
            f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
        )
        if not data or data.get("type") != "file":
            raise AppError(f"Not a file: {path}")
        encoding = data.get("encoding")
        content = data.get("content") or ""
        if encoding == "base64":
            raw = base64.b64decode(content)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="replace")
        else:
            text = str(content)
        return text, data.get("html_url") or data.get("url") or path

    def get_pull(self, owner: str, repo: str, number: int) -> dict:
        return self._get(f"/repos/{owner}/{repo}/pulls/{number}")

    def get_pull_files(self, owner: str, repo: str, number: int) -> list[dict]:
        return self._get(f"/repos/{owner}/{repo}/pulls/{number}/files") or []

    def get_pull_diff(self, owner: str, repo: str, number: int, *, max_chars: int = 30000) -> str:
        url = f"{self.api_base}/repos/{owner}/{repo}/pulls/{number}"
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(
                url,
                headers={
                    **self._headers(),
                    "Accept": "application/vnd.github.v3.diff",
                },
            )
        if resp.status_code >= 400:
            raise AppError(f"Failed to fetch PR diff: {resp.status_code}")
        return resp.text[:max_chars]

    @staticmethod
    def select_indexable_paths(
        tree: list[dict],
        *,
        max_files: int = 80,
        max_file_bytes: int = 200_000,
    ) -> list[str]:
        paths: list[str] = []
        # Prefer README and docs first
        prioritized: list[str] = []
        normal: list[str] = []
        for node in tree:
            if node.get("type") != "blob":
                continue
            path = node.get("path") or ""
            size = int(node.get("size") or 0)
            if size > max_file_bytes:
                continue
            parts = path.split("/")
            if any(p in SKIP_DIRS for p in parts):
                continue
            lower = path.lower()
            ext = "." + lower.rsplit(".", 1)[-1] if "." in lower else ""
            if ext not in CODE_EXTENSIONS and not lower.endswith("readme"):
                continue
            if "readme" in lower or lower.startswith("docs/"):
                prioritized.append(path)
            else:
                normal.append(path)
        for p in prioritized + normal:
            paths.append(p)
            if len(paths) >= max_files:
                break
        return paths
