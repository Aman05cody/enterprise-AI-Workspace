"""Local object storage tests."""

from pathlib import Path

import pytest

from eaw.domain.common.errors import NotFoundError
from eaw.infrastructure.storage.local import LocalObjectStorage


def test_put_get_delete(tmp_path: Path) -> None:
    store = LocalObjectStorage(tmp_path)
    key = "org/kb/doc/v1/file.txt"
    store.put_object(key=key, body=b"hello world", content_type="text/plain")
    assert store.exists(key=key)
    assert store.get_object(key=key) == b"hello world"
    store.delete_object(key=key)
    assert not store.exists(key=key)


def test_path_traversal_blocked(tmp_path: Path) -> None:
    store = LocalObjectStorage(tmp_path)
    with pytest.raises(ValueError):
        store._path("../outside.txt")


def test_missing_file(tmp_path: Path) -> None:
    store = LocalObjectStorage(tmp_path)
    with pytest.raises(NotFoundError):
        store.get_object(key="missing/file.bin")
