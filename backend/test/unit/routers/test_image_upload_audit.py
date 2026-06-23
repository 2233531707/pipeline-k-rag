from __future__ import annotations

import hashlib
import importlib
from types import SimpleNamespace

import pytest

from server.routers import auth_router

pytestmark = pytest.mark.unit


class FakeUpload:
    def __init__(self, filename: str, content: bytes, content_type: str | None = None):
        self.filename = filename
        self.content_type = content_type
        self._content = content
        self._offset = 0

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._content):
            return b""
        end = len(self._content) if size < 0 else min(len(self._content), self._offset + size)
        chunk = self._content[self._offset : end]
        self._offset = end
        return chunk

    async def seek(self, offset: int) -> None:
        self._offset = offset


class FakeDb:
    async def commit(self) -> None:
        return None


async def test_avatar_upload_audits_metadata_without_content(monkeypatch):
    audit_calls = []
    upload_offsets = []

    async def fake_upload_image_to_minio(file, **kwargs):
        upload_offsets.append(file._offset)
        return "https://minio/avatar.png"

    async def fake_log_operation(*args, **kwargs):
        return None

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(auth_router, "upload_image_to_minio", fake_upload_image_to_minio)
    monkeypatch.setattr(auth_router, "log_operation", fake_log_operation)
    monkeypatch.setattr(auth_router, "audit_upload", fake_audit_upload, raising=False)

    payload = b"png-bytes"
    user = SimpleNamespace(id=5, uid="user-1", avatar=None)
    result = await auth_router.upload_user_avatar(
        file=FakeUpload("avatar.png", payload, "image/png"),
        current_user=user,
        db=FakeDb(),
    )

    assert result["success"] is True
    assert user.avatar == "https://minio/avatar.png"
    assert upload_offsets == [0]
    assert audit_calls[0]["entry"] == "avatar_upload"
    assert audit_calls[0]["filename"] == "avatar.png"
    assert audit_calls[0]["size"] == len(payload)
    assert audit_calls[0]["detected_type"] == ".png"
    assert audit_calls[0]["content_hash"] == hashlib.sha256(payload).hexdigest()
    assert audit_calls[0]["result"] == "success"
    assert "png-bytes" not in str(audit_calls)


async def test_avatar_upload_audits_rejected_upload_without_content(monkeypatch):
    audit_calls = []

    async def fake_upload_image_to_minio(file, **kwargs):
        raise ValueError("图片真实类型与后缀不匹配")

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(auth_router, "upload_image_to_minio", fake_upload_image_to_minio)
    monkeypatch.setattr(auth_router, "audit_upload", fake_audit_upload, raising=False)

    payload = b"MZ secret"
    with pytest.raises(auth_router.HTTPException):
        await auth_router.upload_user_avatar(
            file=FakeUpload("avatar.png", payload, "image/png"),
            current_user=SimpleNamespace(id=5, uid="user-1", avatar=None),
            db=FakeDb(),
        )

    assert audit_calls[0]["entry"] == "avatar_upload"
    assert audit_calls[0]["filename"] == "avatar.png"
    assert audit_calls[0]["detected_type"] == ".png"
    assert audit_calls[0]["content_hash"] == hashlib.sha256(payload).hexdigest()
    assert audit_calls[0]["result"] == "rejected"
    assert "真实类型" in audit_calls[0]["reason"]
    assert "MZ secret" not in str(audit_calls)


async def test_user_image_upload_audits_metadata_without_content(monkeypatch):
    user_router = importlib.import_module("server.routers.user_router")

    audit_calls = []
    upload_offsets = []

    async def fake_upload_image_to_minio(file, **kwargs):
        upload_offsets.append(file._offset)
        return "https://minio/image.png"

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(user_router, "upload_image_to_minio", fake_upload_image_to_minio)
    monkeypatch.setattr(user_router, "audit_upload", fake_audit_upload, raising=False)

    payload = b"png-bytes"
    result = await user_router.upload_user_image(
        file=FakeUpload("image.png", payload, "image/png"),
        current_user=SimpleNamespace(id=5, uid="user-1"),
        db=FakeDb(),
    )

    assert result["success"] is True
    assert upload_offsets == [0]
    assert audit_calls[0]["entry"] == "user_image_upload"
    assert audit_calls[0]["filename"] == "image.png"
    assert audit_calls[0]["size"] == len(payload)
    assert audit_calls[0]["detected_type"] == ".png"
    assert audit_calls[0]["content_hash"] == hashlib.sha256(payload).hexdigest()
    assert audit_calls[0]["result"] == "success"
    assert "png-bytes" not in str(audit_calls)


async def test_user_image_upload_audits_rejected_upload_without_content(monkeypatch):
    user_router = importlib.import_module("server.routers.user_router")
    audit_calls = []

    async def fake_upload_image_to_minio(file, **kwargs):
        raise ValueError("图片真实类型与后缀不匹配")

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(user_router, "upload_image_to_minio", fake_upload_image_to_minio)
    monkeypatch.setattr(user_router, "audit_upload", fake_audit_upload, raising=False)

    payload = b"MZ secret"
    with pytest.raises(user_router.HTTPException):
        await user_router.upload_user_image(
            file=FakeUpload("image.png", payload, "image/png"),
            current_user=SimpleNamespace(id=5, uid="user-1"),
            db=FakeDb(),
        )

    assert audit_calls[0]["entry"] == "user_image_upload"
    assert audit_calls[0]["filename"] == "image.png"
    assert audit_calls[0]["detected_type"] == ".png"
    assert audit_calls[0]["content_hash"] == hashlib.sha256(payload).hexdigest()
    assert audit_calls[0]["result"] == "rejected"
    assert "真实类型" in audit_calls[0]["reason"]
    assert "MZ secret" not in str(audit_calls)
