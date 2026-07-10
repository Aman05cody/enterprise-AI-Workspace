"""Google Drive API client (OAuth access token)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx

from eaw.domain.common.errors import AppError, ValidationAppError

# Google Workspace export MIME maps
EXPORT_MIME = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.presentation": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
}

TEXT_LIKE = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "text/html",
    "application/json",
    "application/xml",
    "text/xml",
}


@dataclass
class DriveItem:
    id: str
    name: str
    mime_type: str
    is_folder: bool
    modified_time: Optional[str]
    web_view_link: Optional[str]
    size: Optional[int]


class GoogleDriveClient:
    def __init__(
        self,
        access_token: str,
        *,
        api_base: str = "https://www.googleapis.com",
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        if not access_token or not access_token.strip():
            raise ValidationAppError("Google Drive access token is required")
        self.access_token = access_token.strip()
        self.api_base = api_base.rstrip("/")
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        url = path if path.startswith("http") else f"{self.api_base}{path}"
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(url, headers=self._headers(), params=params)
        if resp.status_code == 401 and self.refresh_token:
            self._refresh_access_token()
            with httpx.Client(timeout=60.0) as client:
                resp = client.get(url, headers=self._headers(), params=params)
        if resp.status_code == 401:
            raise AppError("Google Drive authentication failed — reconnect token")
        if resp.status_code >= 400:
            raise AppError(
                f"Google Drive API error {resp.status_code}",
                details={"body": resp.text[:400]},
            )
        return resp.json()

    def _refresh_access_token(self) -> None:
        if not (self.refresh_token and self.client_id and self.client_secret):
            raise AppError("Access token expired and refresh is not configured")
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        if resp.status_code >= 400:
            raise AppError("Failed to refresh Google access token")
        data = resp.json()
        self.access_token = data["access_token"]

    def verify_token(self) -> dict:
        # about endpoint
        return self._get("/drive/v3/about", params={"fields": "user,storageQuota"})

    def list_children(
        self,
        *,
        folder_id: str = "root",
        page_size: int = 50,
        folders_only: bool = False,
    ) -> list[DriveItem]:
        q = f"'{folder_id}' in parents and trashed=false"
        if folders_only:
            q += " and mimeType='application/vnd.google-apps.folder'"
        data = self._get(
            "/drive/v3/files",
            params={
                "q": q,
                "pageSize": page_size,
                "fields": "files(id,name,mimeType,modifiedTime,webViewLink,size)",
                "orderBy": "folder,name",
            },
        )
        items: list[DriveItem] = []
        for f in data.get("files") or []:
            mime = f.get("mimeType") or ""
            items.append(
                DriveItem(
                    id=f["id"],
                    name=f.get("name") or "Untitled",
                    mime_type=mime,
                    is_folder=mime == "application/vnd.google-apps.folder",
                    modified_time=f.get("modifiedTime"),
                    web_view_link=f.get("webViewLink"),
                    size=int(f["size"]) if f.get("size") else None,
                )
            )
        return items

    def list_files_recursive(
        self,
        folder_id: str = "root",
        *,
        max_files: int = 50,
        max_depth: int = 3,
    ) -> list[DriveItem]:
        found: list[DriveItem] = []

        def walk(fid: str, depth: int) -> None:
            if len(found) >= max_files or depth > max_depth:
                return
            children = self.list_children(folder_id=fid, page_size=100)
            for child in children:
                if child.is_folder:
                    walk(child.id, depth + 1)
                else:
                    if self._is_indexable(child):
                        found.append(child)
                        if len(found) >= max_files:
                            return

        walk(folder_id, 0)
        return found

    def _is_indexable(self, item: DriveItem) -> bool:
        if item.mime_type in EXPORT_MIME:
            return True
        if item.mime_type in TEXT_LIKE:
            return True
        name = (item.name or "").lower()
        return name.endswith(
            (".txt", ".md", ".csv", ".json", ".py", ".ts", ".js", ".html", ".yml", ".yaml")
        )

    def download_text(self, file_id: str, mime_type: str, *, max_bytes: int = 2_000_000) -> str:
        if mime_type in EXPORT_MIME:
            export_mime = EXPORT_MIME[mime_type]
            url = f"{self.api_base}/drive/v3/files/{file_id}/export"
            with httpx.Client(timeout=60.0) as client:
                resp = client.get(
                    url,
                    headers=self._headers(),
                    params={"mimeType": export_mime},
                )
            if resp.status_code >= 400:
                raise AppError(f"Failed to export Drive file: {resp.status_code}")
            return resp.text[:max_bytes]

        url = f"{self.api_base}/drive/v3/files/{file_id}"
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(
                url,
                headers=self._headers(),
                params={"alt": "media"},
            )
        if resp.status_code >= 400:
            raise AppError(f"Failed to download Drive file: {resp.status_code}")
        raw = resp.content[:max_bytes]
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")
