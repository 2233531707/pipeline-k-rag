from io import BytesIO

import pytest
from fastapi import UploadFile

from yuxi.storage.minio import utils as minio_utils


pytestmark = pytest.mark.asyncio


async def test_image_upload_rejects_content_type_spoof_before_storage(monkeypatch):
    storage_called = False

    async def fake_upload(*args, **kwargs):
        nonlocal storage_called
        storage_called = True

    monkeypatch.setattr(minio_utils, "aupload_file_to_minio", fake_upload)
    upload = UploadFile(filename="avatar.png", file=BytesIO(b"MZ" + b"\x00" * 32))
    upload.headers = {"content-type": "image/png"}

    with pytest.raises(ValueError, match="真实类型"):
        await minio_utils.upload_image_to_minio(
            upload,
            object_prefix="avatar/1",
            max_size_bytes=5 * 1024 * 1024,
            too_large_message="图片大小不能超过 5MB",
        )

    assert storage_called is False
