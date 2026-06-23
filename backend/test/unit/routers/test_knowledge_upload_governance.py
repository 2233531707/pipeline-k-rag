import asyncio
import os
import time
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

from server.routers import knowledge_router


pytestmark = pytest.mark.asyncio


async def test_knowledge_upload_streams_from_temporary_path_and_cleans_it(monkeypatch):
    payload = b"streamed knowledge content"
    uploaded_path: Path | None = None

    async def fake_file_existed_in_db(kb_id: str, content_hash: str) -> bool:
        assert kb_id == "kb_1"
        assert content_hash == sha256(payload).hexdigest()
        return False

    async def fake_get_same_name_files(kb_id: str, filename: str) -> list:
        return []

    class FakeMinioClient:
        async def aupload_file_from_path(self, bucket_name: str, object_name: str, file_path: str):
            nonlocal uploaded_path
            uploaded_path = Path(file_path)
            assert uploaded_path.read_bytes() == payload
            return SimpleNamespace(url=f"minio://{bucket_name}/{object_name}")

    monkeypatch.setattr(knowledge_router, "MAX_UPLOAD_SIZE_BYTES", 512 * 1024 * 1024)
    monkeypatch.setattr(knowledge_router.knowledge_base, "file_existed_in_db", fake_file_existed_in_db)
    monkeypatch.setattr(knowledge_router.knowledge_base, "get_same_name_files", fake_get_same_name_files)
    monkeypatch.setattr(knowledge_router, "get_minio_client", lambda: FakeMinioClient())

    result = await knowledge_router.upload_file(
        UploadFile(filename="Demo.txt", file=BytesIO(payload)),
        kb_id="kb_1",
        current_user=SimpleNamespace(uid="user_1"),
    )

    assert result["size"] == len(payload)
    assert result["content_hash"] == sha256(payload).hexdigest()
    assert result["minio_path"].startswith("minio://knowledgebases/kb_1/upload/")
    assert uploaded_path is not None
    assert not uploaded_path.exists()



async def test_knowledge_upload_rejects_disguised_pdf_before_storage(monkeypatch):
    storage_called = False
    audit_calls = []

    class FakeMinioClient:
        async def aupload_file_from_path(self, *args, **kwargs):
            nonlocal storage_called
            storage_called = True

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(knowledge_router, "get_minio_client", lambda: FakeMinioClient())
    monkeypatch.setattr(knowledge_router, "audit_upload", fake_audit_upload)

    with pytest.raises(HTTPException) as exc_info:
        await knowledge_router.upload_file(
            UploadFile(filename="malware.pdf", file=BytesIO(b"MZ" + b"\x00" * 32)),
            kb_id="kb_1",
            current_user=SimpleNamespace(uid="user_1", id=7),
            db=object(),
        )

    assert exc_info.value.status_code == 400
    assert "真实类型" in exc_info.value.detail
    assert storage_called is False
    assert audit_calls[0]["result"] == "rejected"
    assert audit_calls[0]["entry"] == "knowledge_file"
    assert "真实类型" in audit_calls[0]["reason"]
    assert "MZ" not in str(audit_calls)



@pytest.mark.parametrize(
    "filename",
    ["fake.docx", "fake.xlsx", "fake.pptx", "fake.xls", "fake.png", "fake.tiff", "fake.zip"],
)
async def test_knowledge_upload_rejects_disguised_binary_before_storage(monkeypatch, filename):
    async def fake_file_existed_in_db(kb_id: str, content_hash: str) -> bool:
        return False

    async def fake_get_same_name_files(kb_id: str, stored_filename: str) -> list:
        return []

    class FakeMinioClient:
        async def aupload_file_from_path(self, *args, **kwargs):
            raise AssertionError("disguised files must be rejected before storage")

    monkeypatch.setattr(knowledge_router.knowledge_base, "file_existed_in_db", fake_file_existed_in_db)
    monkeypatch.setattr(knowledge_router.knowledge_base, "get_same_name_files", fake_get_same_name_files)
    monkeypatch.setattr(knowledge_router, "get_minio_client", lambda: FakeMinioClient())

    with pytest.raises(HTTPException) as exc_info:
        await knowledge_router.upload_file(
            UploadFile(filename=filename, file=BytesIO(b"MZ" + b"\x00" * 64)),
            kb_id="kb_1",
            current_user=SimpleNamespace(uid="user_1"),
        )

    assert exc_info.value.status_code == 400
    assert "真实类型" in exc_info.value.detail



async def test_knowledge_upload_returns_retryable_429_when_user_limit_is_reached(monkeypatch):
    from yuxi.services.upload_admission import UploadAdmission

    storage_started = asyncio.Event()
    release_storage = asyncio.Event()

    async def fake_file_existed_in_db(kb_id: str, content_hash: str) -> bool:
        return False

    async def fake_get_same_name_files(kb_id: str, filename: str) -> list:
        return []

    class FakeMinioClient:
        async def aupload_file_from_path(self, bucket_name: str, object_name: str, file_path: str):
            storage_started.set()
            await release_storage.wait()
            return SimpleNamespace(url=f"minio://{bucket_name}/{object_name}")

    monkeypatch.setattr(knowledge_router.knowledge_base, "file_existed_in_db", fake_file_existed_in_db)
    monkeypatch.setattr(knowledge_router.knowledge_base, "get_same_name_files", fake_get_same_name_files)
    monkeypatch.setattr(knowledge_router, "get_minio_client", lambda: FakeMinioClient())
    monkeypatch.setattr(
        knowledge_router,
        "large_upload_admission",
        UploadAdmission(per_user_limit=1, global_limit=2, retry_after_seconds=3),
    )

    first_upload = asyncio.create_task(
        knowledge_router.upload_file(
            UploadFile(filename="first.txt", file=BytesIO(b"first")),
            kb_id="kb_1",
            current_user=SimpleNamespace(uid="user_1"),
        )
    )
    await storage_started.wait()

    try:
        with pytest.raises(HTTPException) as exc_info:
            await knowledge_router.upload_file(
                UploadFile(filename="second.txt", file=BytesIO(b"second")),
                kb_id="kb_1",
                current_user=SimpleNamespace(uid="user_1"),
            )

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers == {"Retry-After": "3"}
    finally:
        release_storage.set()
        await first_upload



async def test_stale_upload_cleanup_removes_only_expired_files(tmp_path):
    from yuxi.utils.upload_utils import cleanup_stale_upload_files

    old_file = tmp_path / "old.upload"
    fresh_file = tmp_path / "fresh.upload"
    old_file.write_bytes(b"old")
    fresh_file.write_bytes(b"fresh")
    now = time.time()
    os.utime(old_file, (now - 25 * 60 * 60, now - 25 * 60 * 60))

    removed = await cleanup_stale_upload_files(tmp_path, older_than_seconds=24 * 60 * 60, now=now)

    assert removed == 1
    assert not old_file.exists()
    assert fresh_file.exists()



async def test_workspace_import_streams_existing_file_path(monkeypatch, tmp_path):
    payload = b"workspace knowledge"
    workspace_file = tmp_path / "workspace.txt"
    workspace_file.write_bytes(payload)

    async def fake_ensure_database_supports_documents(kb_id: str, operation: str) -> None:
        return None

    async def fake_file_existed_in_db(kb_id: str, content_hash: str) -> bool:
        assert content_hash == sha256(payload).hexdigest()
        return False

    async def fake_get_same_name_files(kb_id: str, filename: str) -> list:
        return []

    class FakeMinioClient:
        async def aupload_file_from_path(self, bucket_name: str, object_name: str, file_path: str):
            assert Path(file_path) == workspace_file
            return SimpleNamespace(url=f"minio://{bucket_name}/{object_name}")

    monkeypatch.setattr(
        knowledge_router,
        "_ensure_database_supports_documents",
        fake_ensure_database_supports_documents,
    )
    monkeypatch.setattr(knowledge_router, "resolve_workspace_file_path", lambda **kwargs: workspace_file)
    monkeypatch.setattr(knowledge_router.knowledge_base, "file_existed_in_db", fake_file_existed_in_db)
    monkeypatch.setattr(knowledge_router.knowledge_base, "get_same_name_files", fake_get_same_name_files)
    monkeypatch.setattr(knowledge_router, "get_minio_client", lambda: FakeMinioClient())

    result = await knowledge_router.import_workspace_files(
        knowledge_router.WorkspaceImportRequest(kb_id="kb_1", paths=["/workspace/workspace.txt"]),
        current_user=SimpleNamespace(uid="user_1"),
    )

    assert result["items"][0]["size"] == len(payload)
    assert result["items"][0]["content_hash"] == sha256(payload).hexdigest()


async def test_knowledge_upload_records_metadata_only_audit(monkeypatch):
    payload = b"audited knowledge"
    audit_calls = []

    async def fake_file_existed_in_db(kb_id: str, content_hash: str) -> bool:
        return False

    async def fake_get_same_name_files(kb_id: str, filename: str) -> list:
        return []

    class FakeMinioClient:
        async def aupload_file_from_path(self, bucket_name: str, object_name: str, file_path: str):
            return SimpleNamespace(url=f"minio://{bucket_name}/{object_name}")

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(knowledge_router.knowledge_base, "file_existed_in_db", fake_file_existed_in_db)
    monkeypatch.setattr(knowledge_router.knowledge_base, "get_same_name_files", fake_get_same_name_files)
    monkeypatch.setattr(knowledge_router, "get_minio_client", lambda: FakeMinioClient())
    monkeypatch.setattr(knowledge_router, "audit_upload", fake_audit_upload)

    result = await knowledge_router.upload_file(
        UploadFile(filename="audit.txt", file=BytesIO(payload)),
        kb_id="kb_1",
        current_user=SimpleNamespace(uid="user_1", id=7),
        db=object(),
    )

    assert result["size"] == len(payload)
    assert audit_calls == [
        {
            "db": audit_calls[0]["db"],
            "user_id": 7,
            "entry": "knowledge_file",
            "filename": "audit.txt",
            "size": len(payload),
            "detected_type": ".txt",
            "content_hash": sha256(payload).hexdigest(),
            "result": "success",
        }
    ]
    assert payload.decode() not in str(audit_calls)
