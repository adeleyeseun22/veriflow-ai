from functools import cached_property
from pathlib import Path

from minio import Minio
from minio.error import S3Error
from starlette.concurrency import run_in_threadpool

from veriflow_api.config import settings


class ObjectStorageError(RuntimeError):
    """Raised when the object-storage service cannot complete an operation."""


class ObjectStorage:
    @cached_property
    def client(self) -> Minio:
        endpoint = settings.minio_endpoint.removeprefix("http://").removeprefix("https://")
        return Minio(
            endpoint=endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    async def check_connection(self) -> None:
        try:
            await run_in_threadpool(self.client.list_buckets)
        except Exception as error:  # MinIO may surface urllib3 errors as well as S3Error.
            raise ObjectStorageError("Object storage is unavailable.") from error

    async def ensure_bucket(self) -> None:
        try:
            exists = await run_in_threadpool(self.client.bucket_exists, settings.minio_bucket)
            if not exists:
                await run_in_threadpool(self.client.make_bucket, settings.minio_bucket)
        except S3Error as error:
            if error.code not in {"BucketAlreadyExists", "BucketAlreadyOwnedByYou"}:
                raise ObjectStorageError("Unable to prepare the document bucket.") from error
        except Exception as error:
            raise ObjectStorageError("Unable to prepare the document bucket.") from error

    async def upload_file(
        self,
        *,
        source_path: Path,
        object_name: str,
        content_type: str,
    ) -> None:
        await self.ensure_bucket()

        try:
            await run_in_threadpool(
                self.client.fput_object,
                settings.minio_bucket,
                object_name,
                str(source_path),
                content_type,
            )
        except Exception as error:
            raise ObjectStorageError("Unable to store the uploaded document.") from error

    async def delete_object(self, object_name: str) -> None:
        try:
            await run_in_threadpool(
                self.client.remove_object,
                settings.minio_bucket,
                object_name,
            )
        except Exception as error:
            raise ObjectStorageError("Unable to remove the stored document.") from error


object_storage = ObjectStorage()


async def check_object_storage() -> None:
    await object_storage.check_connection()
