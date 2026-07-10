"""S3-compatible object storage adapter (MinIO / AWS S3)."""

from __future__ import annotations

from typing import BinaryIO, Optional

from eaw.application.ports.object_storage import ObjectStoragePort
from eaw.domain.common.errors import NotFoundError


class S3ObjectStorage(ObjectStoragePort):
    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
        use_ssl: bool = False,
    ) -> None:
        import boto3
        from botocore.client import Config

        self.bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            use_ssl=use_ssl,
            config=Config(signature_version="s3v4"),
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except Exception:  # noqa: BLE001
            try:
                self._client.create_bucket(Bucket=self.bucket)
            except Exception:  # noqa: BLE001
                # Bucket may already exist or permissions differ — put will fail clearly
                pass

    def put_object(
        self,
        *,
        key: str,
        body: BinaryIO | bytes,
        content_type: str,
        content_length: Optional[int] = None,
    ) -> str:
        data = body if isinstance(body, bytes) else body.read()
        extra = {"ContentType": content_type}
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            **extra,
        )
        return key

    def get_object(self, *, key: str) -> bytes:
        try:
            obj = self._client.get_object(Bucket=self.bucket, Key=key)
            return obj["Body"].read()
        except Exception as exc:  # noqa: BLE001
            raise NotFoundError("File not found in storage") from exc

    def delete_object(self, *, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, *, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False
