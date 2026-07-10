"""Storage factory."""

from functools import lru_cache
from pathlib import Path

from eaw.application.ports.object_storage import ObjectStoragePort
from eaw.core.config import get_settings
from eaw.infrastructure.storage.local import LocalObjectStorage
from eaw.infrastructure.storage.s3 import S3ObjectStorage


@lru_cache
def get_object_storage() -> ObjectStoragePort:
    settings = get_settings()
    backend = (settings.storage_backend or "local").lower()
    if backend == "s3":
        return S3ObjectStorage(
            endpoint_url=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            use_ssl=settings.s3_use_ssl,
        )
    root = Path(settings.local_storage_path)
    if not root.is_absolute():
        # monorepo root / data/uploads when relative
        # factory.py → storage → infrastructure → eaw → src → api → apps → repo
        monorepo = Path(__file__).resolve().parents[6]
        root = monorepo / root
    return LocalObjectStorage(root)
