"""Google Drive indexable file filter tests."""

from eaw.infrastructure.connectors.gdrive_client import DriveItem, GoogleDriveClient


def _item(name: str, mime: str) -> DriveItem:
    return DriveItem(
        id="1",
        name=name,
        mime_type=mime,
        is_folder=False,
        modified_time=None,
        web_view_link=None,
        size=10,
    )


def test_indexable_types() -> None:
    client = GoogleDriveClient("ya29.test_token_value")
    assert client._is_indexable(
        _item("Doc", "application/vnd.google-apps.document")
    )
    assert client._is_indexable(_item("notes.txt", "text/plain"))
    assert client._is_indexable(_item("readme.md", "application/octet-stream"))
    assert not client._is_indexable(_item("photo.jpg", "image/jpeg"))
