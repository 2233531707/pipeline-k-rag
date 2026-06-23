from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault(
    "SAVE_DIR",
    os.path.join(os.environ.get("CLAUDE_JOB_DIR", tempfile.gettempdir()), "yuxi-test-saves"),
)

from server.routers import chat_router
from yuxi.services import conversation_service as service

pytestmark = pytest.mark.unit


class FakeUpload:
    def __init__(self, filename: str, content: bytes, content_type: str | None = None):
        self.filename = filename
        self.content_type = content_type
        self._content = content
        self._offset = 0

    async def seek(self, offset: int) -> None:
        self._offset = offset

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._content):
            return b""
        end = len(self._content) if size < 0 else min(len(self._content), self._offset + size)
        chunk = self._content[self._offset : end]
        self._offset = end
        return chunk


class ChunkedOnlyUpload(FakeUpload):
    async def read(self, size: int = -1) -> bytes:
        if size < 0:
            raise AssertionError("upload must be read in bounded chunks")
        return await super().read(size)


class FakeMinioClient:
    KB_BUCKETS = {"documents": "knowledgebases"}

    def __init__(self):
        self.objects: dict[tuple[str, str], bytes] = {}
        self.uploads: list[dict] = []
        self.path_uploads: list[Path] = []
        self.path_downloads: list[Path] = []

    async def aupload_file_from_path(
        self, bucket_name: str, object_name: str, file_path: str, content_type: str | None = None
    ):
        path = Path(file_path)
        self.path_uploads.append(path)
        data = path.read_bytes()
        self.objects[(bucket_name, object_name)] = data
        return SimpleNamespace(
            bucket_name=bucket_name,
            object_name=object_name,
            url=f"http://minio:9000/{bucket_name}/{object_name}",
        )

    async def aupload_file(self, bucket_name: str, object_name: str, data: bytes, content_type: str | None = None):
        self.objects[(bucket_name, object_name)] = data
        self.uploads.append(
            {
                "bucket_name": bucket_name,
                "object_name": object_name,
                "data": data,
                "content_type": content_type,
            }
        )
        return SimpleNamespace(
            bucket_name=bucket_name,
            object_name=object_name,
            url=f"http://minio:9000/{bucket_name}/{object_name}",
        )

    async def adownload_file_to_path(self, bucket_name: str, object_name: str, file_path: str) -> None:
        path = Path(file_path)
        try:
            path.write_bytes(self.objects[(bucket_name, object_name)])
        except KeyError as exc:
            raise service.StorageError("missing object") from exc
        self.path_downloads.append(path)

    async def adownload_file(self, bucket_name: str, object_name: str) -> bytes:
        try:
            return self.objects[(bucket_name, object_name)]
        except KeyError as exc:
            raise service.StorageError("missing object") from exc


@dataclass
class FakeConversation:
    id: int = 1
    uid: str = "user-1"
    agent_id: str = "agent-1"
    status: str = "active"
    extra_metadata: dict | None = None


class FakeConversationRepository:
    def __init__(self, db):
        self.conversation = FakeConversation()
        self.attachments: list[dict] = []

    async def get_conversation_by_thread_id(self, thread_id: str):
        return self.conversation

    async def add_attachment(self, conversation_id: int, attachment_info: dict):
        self.attachments.append(attachment_info)
        return attachment_info

    async def add_attachments(self, conversation_id: int, attachment_infos: list[dict]):
        self.attachments.extend(attachment_infos)
        return attachment_infos

    async def get_attachments(self, conversation_id: int):
        return list(self.attachments)


@pytest.mark.asyncio
async def test_upload_tmp_attachment_writes_user_scoped_minio_object(monkeypatch):
    fake_minio = FakeMinioClient()
    monkeypatch.setattr(service, "get_minio_client", lambda: fake_minio)

    payload = b"%PDF-1.7 attachment"
    response = await service.upload_tmp_attachment_view(
        file=FakeUpload("demo.pdf", payload, "application/pdf"),
        current_uid="user-1",
    )

    assert response["bucket_name"] == "knowledgebases"
    assert response["object_name"].startswith("tmp/chat_attachments/user-1/")
    assert response["parse_methods"][0] == "disable"
    assert fake_minio.objects[("knowledgebases", response["object_name"])] == payload
    assert response["content_hash"] == hashlib.sha256(payload).hexdigest()
    assert len(fake_minio.path_uploads) == 1
    assert not fake_minio.path_uploads[0].exists()


@pytest.mark.asyncio
async def test_parse_tmp_attachment_uses_selected_method_and_uploads_markdown(monkeypatch):
    fake_minio = FakeMinioClient()
    object_name = "tmp/chat_attachments/user-1/tmp-1/original/demo.pdf"
    fake_minio.objects[("knowledgebases", object_name)] = b"pdf-bytes"
    monkeypatch.setattr(service, "get_minio_client", lambda: fake_minio)

    parse_calls = []

    async def fake_parse(source: str, params: dict | None = None) -> str:
        parse_calls.append({"source": source, "params": params})
        return "# parsed"

    monkeypatch.setattr(service.Parser, "aparse", staticmethod(fake_parse))

    response = await service.parse_tmp_attachment_view(
        object_name=object_name,
        file_name="demo.pdf",
        parse_method="disable",
        bucket_name="knowledgebases",
        current_uid="user-1",
    )

    assert parse_calls == [
        {
            "source": f"minio://knowledgebases/{object_name}",
            "params": {"ocr_engine": "disable"},
        }
    ]
    assert response["parsed_object_name"] == "tmp/chat_attachments/user-1/tmp-1/parsed/demo.md"
    assert fake_minio.objects[("knowledgebases", response["parsed_object_name"])] == b"# parsed"


@pytest.mark.asyncio
async def test_confirm_tmp_thread_attachments_materializes_original_and_parsed_files(monkeypatch, tmp_path: Path):
    fake_minio = FakeMinioClient()
    original_object = "tmp/chat_attachments/user-1/tmp-1/original/demo.pdf"
    parsed_object = "tmp/chat_attachments/user-1/tmp-1/parsed/demo.md"
    fake_minio.objects[("knowledgebases", original_object)] = b"pdf-bytes"
    fake_minio.objects[("knowledgebases", parsed_object)] = b"# parsed"
    fake_repo = FakeConversationRepository(db=None)

    monkeypatch.setattr(service, "get_minio_client", lambda: fake_minio)
    monkeypatch.setattr(service, "ConversationRepository", lambda db: fake_repo)
    monkeypatch.setattr(service.app_config, "save_dir", str(tmp_path))

    def fake_uploads_dir(thread_id: str) -> Path:
        path = tmp_path / "threads" / thread_id / "user-data" / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    monkeypatch.setattr(service, "ensure_thread_dirs", lambda thread_id, user_id: fake_uploads_dir(thread_id))
    monkeypatch.setattr(service, "sandbox_uploads_dir", fake_uploads_dir)

    async def noop_sync(**kwargs):
        return None

    async def noop_invalidate(thread_id: str):
        return None

    monkeypatch.setattr(service, "_sync_thread_upload_state", noop_sync)
    monkeypatch.setattr(service, "invalidate_mention_cache", noop_invalidate)

    response = await service.confirm_tmp_thread_attachments_view(
        thread_id="thread-1",
        attachments=[
            {
                "file_name": "demo.pdf",
                "file_type": "application/pdf",
                "bucket_name": "knowledgebases",
                "object_name": original_object,
                "parsed_object_name": parsed_object,
                "truncated": False,
            }
        ],
        db=None,
        current_uid="user-1",
    )

    [attachment] = response["attachments"]
    assert attachment["status"] == "parsed"
    original_name = Path(attachment["original_path"]).name
    markdown_name = Path(attachment["path"]).name
    assert original_name.endswith("_demo.pdf")
    assert markdown_name.endswith("_demo.md")
    assert (tmp_path / "threads" / "thread-1" / "user-data" / "uploads" / original_name).read_bytes() == b"pdf-bytes"
    assert (
        tmp_path / "threads" / "thread-1" / "user-data" / "uploads" / "attachments" / markdown_name
    ).read_text(encoding="utf-8") == "# parsed"
    assert Path(fake_repo.attachments[0]["original_path"]).name == original_name
    assert len(fake_minio.path_downloads) == 1
    assert not fake_minio.path_downloads[0].exists()


@pytest.mark.asyncio
async def test_parse_tmp_attachment_uses_object_name_for_type_validation(monkeypatch):
    fake_minio = FakeMinioClient()
    object_name = "tmp/chat_attachments/user-1/tmp-1/original/demo.docx"
    fake_minio.objects[("knowledgebases", object_name)] = b"docx-bytes"
    monkeypatch.setattr(service, "get_minio_client", lambda: fake_minio)

    with pytest.raises(service.HTTPException) as exc_info:
        await service.parse_tmp_attachment_view(
            object_name=object_name,
            file_name="demo.pdf",
            parse_method="disable",
            bucket_name="knowledgebases",
            current_uid="user-1",
        )

    assert exc_info.value.status_code == 400
    assert "PDF 和图片" in exc_info.value.detail


@pytest.mark.asyncio
async def test_parse_tmp_attachment_handles_url_metacharacters(monkeypatch):
    fake_minio = FakeMinioClient()
    object_name = "tmp/chat_attachments/user-1/tmp-1/original/q1?.pdf"
    fake_minio.objects[("knowledgebases", object_name)] = b"pdf-bytes"
    monkeypatch.setattr(service, "get_minio_client", lambda: fake_minio)

    parse_calls = []

    async def fake_parse(source: str, params: dict | None = None) -> str:
        parse_calls.append(source)
        return "# parsed"

    monkeypatch.setattr(service.Parser, "aparse", staticmethod(fake_parse))

    response = await service.parse_tmp_attachment_view(
        object_name=object_name,
        file_name="ignored.pdf",
        parse_method="disable",
        bucket_name="knowledgebases",
        current_uid="user-1",
    )

    assert parse_calls == ["minio://knowledgebases/tmp/chat_attachments/user-1/tmp-1/original/q1%3F.pdf"]
    assert response["parsed_object_name"] == "tmp/chat_attachments/user-1/tmp-1/parsed/q1?.md"


@pytest.mark.asyncio
async def test_confirm_tmp_thread_attachments_rejects_non_parsed_object(monkeypatch):
    fake_minio = FakeMinioClient()
    original_object = "tmp/chat_attachments/user-1/tmp-1/original/demo.pdf"
    fake_minio.objects[("knowledgebases", original_object)] = b"pdf-bytes"
    fake_repo = FakeConversationRepository(db=None)

    monkeypatch.setattr(service, "get_minio_client", lambda: fake_minio)
    monkeypatch.setattr(service, "ConversationRepository", lambda db: fake_repo)

    with pytest.raises(service.HTTPException) as exc_info:
        await service.confirm_tmp_thread_attachments_view(
            thread_id="thread-1",
            attachments=[
                {
                    "file_name": "demo.pdf",
                    "file_type": "application/pdf",
                    "bucket_name": "knowledgebases",
                    "object_name": original_object,
                    "parsed_object_name": original_object,
                }
            ],
            db=None,
            current_uid="user-1",
        )

    assert exc_info.value.status_code == 400
    assert fake_repo.attachments == []


@pytest.mark.asyncio
async def test_confirm_tmp_thread_attachments_validates_batch_before_commit(monkeypatch):
    fake_minio = FakeMinioClient()
    valid_object = "tmp/chat_attachments/user-1/tmp-1/original/valid.pdf"
    missing_object = "tmp/chat_attachments/user-1/tmp-2/original/missing.pdf"
    fake_minio.objects[("knowledgebases", valid_object)] = b"pdf-bytes"
    fake_repo = FakeConversationRepository(db=None)

    monkeypatch.setattr(service, "get_minio_client", lambda: fake_minio)
    monkeypatch.setattr(service, "ConversationRepository", lambda db: fake_repo)

    with pytest.raises(service.HTTPException) as exc_info:
        await service.confirm_tmp_thread_attachments_view(
            thread_id="thread-1",
            attachments=[
                {"file_name": "valid.pdf", "bucket_name": "knowledgebases", "object_name": valid_object},
                {"file_name": "missing.pdf", "bucket_name": "knowledgebases", "object_name": missing_object},
            ],
            db=None,
            current_uid="user-1",
        )

    assert exc_info.value.status_code == 400
    assert fake_repo.attachments == []


@pytest.mark.asyncio
async def test_confirm_tmp_thread_attachments_keeps_duplicate_names_separate(monkeypatch, tmp_path: Path):
    fake_minio = FakeMinioClient()
    first_object = "tmp/chat_attachments/user-1/tmp-1/original/report.pdf"
    second_object = "tmp/chat_attachments/user-1/tmp-2/original/report.pdf"
    fake_minio.objects[("knowledgebases", first_object)] = b"first"
    fake_minio.objects[("knowledgebases", second_object)] = b"second"
    fake_repo = FakeConversationRepository(db=None)

    monkeypatch.setattr(service, "get_minio_client", lambda: fake_minio)
    monkeypatch.setattr(service, "ConversationRepository", lambda db: fake_repo)
    monkeypatch.setattr(service.app_config, "save_dir", str(tmp_path))

    def fake_uploads_dir(thread_id: str) -> Path:
        path = tmp_path / "threads" / thread_id / "user-data" / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    monkeypatch.setattr(service, "ensure_thread_dirs", lambda thread_id, uid: fake_uploads_dir(thread_id))
    monkeypatch.setattr(service, "sandbox_uploads_dir", fake_uploads_dir)

    async def noop_sync(**kwargs):
        return None

    async def noop_invalidate(thread_id: str):
        return None

    monkeypatch.setattr(service, "_sync_thread_upload_state", noop_sync)
    monkeypatch.setattr(service, "invalidate_mention_cache", noop_invalidate)

    response = await service.confirm_tmp_thread_attachments_view(
        thread_id="thread-1",
        attachments=[
            {"file_name": "report.pdf", "bucket_name": "knowledgebases", "object_name": first_object},
            {"file_name": "report.pdf", "bucket_name": "knowledgebases", "object_name": second_object},
        ],
        db=None,
        current_uid="user-1",
    )

    first, second = response["attachments"]
    upload_dir = tmp_path / "threads" / "thread-1" / "user-data" / "uploads"
    assert first["original_path"] != second["original_path"]
    assert (upload_dir / Path(first["original_path"]).name).read_bytes() == b"first"
    assert (upload_dir / Path(second["original_path"]).name).read_bytes() == b"second"



@pytest.mark.asyncio
async def test_large_tmp_attachment_is_stored_without_parse_capability(monkeypatch):
    fake_minio = FakeMinioClient()
    monkeypatch.setattr(service, "get_minio_client", lambda: fake_minio)
    monkeypatch.setattr(service, "MAX_ATTACHMENT_PARSE_SIZE_BYTES", 5)

    response = await service.upload_tmp_attachment_view(
        file=FakeUpload("large.pdf", b"%PDF-1.7", "application/pdf"),
        current_uid="user-1",
    )

    assert response["file_size"] == 8
    assert response["parse_supported"] is False
    assert response["parse_methods"] == []
    assert "100 MB" in response["parse_unavailable_reason"]
    assert fake_minio.objects[("knowledgebases", response["object_name"])] == b"%PDF-1.7"


@pytest.mark.asyncio
async def test_upload_thread_attachment_streams_to_disk_and_cleans_staging_file(monkeypatch, tmp_path: Path):
    fake_repo = FakeConversationRepository(db=None)
    staging_dir = tmp_path / "staging"
    uploads_dir = tmp_path / "threads" / "thread-1" / "user-data" / "uploads"

    monkeypatch.setattr(service, "ConversationRepository", lambda db: fake_repo)
    monkeypatch.setattr(service, "UPLOAD_TEMP_DIR", staging_dir)
    monkeypatch.setattr(service.app_config, "save_dir", str(tmp_path))
    monkeypatch.setattr(
        service,
        "ensure_thread_dirs",
        lambda thread_id, uid: uploads_dir.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setattr(service, "sandbox_uploads_dir", lambda thread_id: uploads_dir)

    async def noop_sync(**kwargs):
        return None

    async def noop_invalidate(thread_id: str):
        return None

    monkeypatch.setattr(service, "_sync_thread_upload_state", noop_sync)
    monkeypatch.setattr(service, "invalidate_mention_cache", noop_invalidate)
    monkeypatch.setattr(service, "MAX_ATTACHMENT_PARSE_SIZE_BYTES", 0)

    response = await service.upload_thread_attachment_view(
        thread_id="thread-1",
        file=ChunkedOnlyUpload("report.txt", b"streamed content", "text/plain"),
        db=None,
        current_uid="user-1",
    )

    assert response["status"] == "uploaded"
    assert response["file_size"] == len(b"streamed content")
    assert (uploads_dir / "report.txt").read_bytes() == b"streamed content"
    assert list(staging_dir.iterdir()) == []



async def test_tmp_attachment_route_audits_metadata_without_exposing_hash(monkeypatch):
    audit_calls = []

    async def fake_upload_tmp_attachment_view(*, file, current_uid):
        return {
            "tmp_file_id": "tmp-1",
            "file_name": "notes.txt",
            "file_type": "text/plain",
            "file_size": 5,
            "bucket_name": "knowledgebases",
            "object_name": "tmp/chat_attachments/user-1/tmp-1/original/notes.txt",
            "minio_url": "minio://knowledgebases/notes.txt",
            "uploaded_at": "2026-06-22T00:00:00Z",
            "parse_supported": False,
            "parse_methods": [],
            "parse_unavailable_reason": None,
            "content_hash": "hash-1",
        }

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(chat_router, "upload_tmp_attachment_view", fake_upload_tmp_attachment_view)
    monkeypatch.setattr(chat_router, "audit_upload", fake_audit_upload, raising=False)

    result = await chat_router.upload_tmp_attachment(
        file=FakeUpload("notes.txt", b"hello", "text/plain"),
        current_user=SimpleNamespace(uid="user-1", id=5),
        db=object(),
    )

    assert "content_hash" not in result
    assert audit_calls == [
        {
            "db": audit_calls[0]["db"],
            "user_id": 5,
            "entry": "chat_tmp_attachment",
            "filename": "notes.txt",
            "size": 5,
            "detected_type": ".txt",
            "content_hash": "hash-1",
            "result": "success",
        }
    ]
    assert "hello" not in str(audit_calls)


async def test_thread_attachment_route_audits_metadata_without_exposing_hash(monkeypatch):
    audit_calls = []

    async def fake_upload_thread_attachment_view(**kwargs):
        return {
            "file_id": "file-1",
            "file_name": "notes.txt",
            "file_type": "text/plain",
            "file_size": 5,
            "status": "uploaded",
            "uploaded_at": "2026-06-22T00:00:00Z",
            "path": "/home/gem/user-data/uploads/notes.txt",
            "content_hash": "hash-2",
        }

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(chat_router, "upload_thread_attachment_view", fake_upload_thread_attachment_view)
    monkeypatch.setattr(chat_router, "audit_upload", fake_audit_upload)

    result = await chat_router.upload_thread_attachment(
        thread_id="thread-1",
        file=FakeUpload("notes.txt", b"hello", "text/plain"),
        db=object(),
        current_user=SimpleNamespace(uid="user-1", id=5),
    )

    assert "content_hash" not in result
    assert audit_calls[0]["entry"] == "chat_thread_attachment"
    assert audit_calls[0]["content_hash"] == "hash-2"
    assert audit_calls[0]["result"] == "success"
    assert "hello" not in str(audit_calls)


async def test_tmp_attachment_route_audits_rejected_upload_without_content(monkeypatch):
    audit_calls = []

    async def fake_upload_tmp_attachment_view(*, file, current_uid):
        raise chat_router.HTTPException(status_code=400, detail="真实文件类型 .exe 与扩展名 .txt 不一致")

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(chat_router, "upload_tmp_attachment_view", fake_upload_tmp_attachment_view)
    monkeypatch.setattr(chat_router, "audit_upload", fake_audit_upload)

    with pytest.raises(chat_router.HTTPException):
        await chat_router.upload_tmp_attachment(
            file=FakeUpload("payload.txt", b"MZ secret", "text/plain"),
            current_user=SimpleNamespace(uid="user-1", id=5),
            db=object(),
        )

    assert audit_calls[0]["entry"] == "chat_tmp_attachment"
    assert audit_calls[0]["filename"] == "payload.txt"
    assert audit_calls[0]["detected_type"] == ".txt"
    assert audit_calls[0]["result"] == "rejected"
    assert "真实文件类型" in audit_calls[0]["reason"]
    assert "MZ secret" not in str(audit_calls)


async def test_thread_attachment_route_audits_rejected_upload_without_content(monkeypatch):
    audit_calls = []

    async def fake_upload_thread_attachment_view(**kwargs):
        raise chat_router.HTTPException(status_code=400, detail="真实文件类型 .exe 与扩展名 .txt 不一致")

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(chat_router, "upload_thread_attachment_view", fake_upload_thread_attachment_view)
    monkeypatch.setattr(chat_router, "audit_upload", fake_audit_upload)

    with pytest.raises(chat_router.HTTPException):
        await chat_router.upload_thread_attachment(
            thread_id="thread-1",
            file=FakeUpload("payload.txt", b"MZ secret", "text/plain"),
            db=object(),
            current_user=SimpleNamespace(uid="user-1", id=5),
        )

    assert audit_calls[0]["entry"] == "chat_thread_attachment"
    assert audit_calls[0]["filename"] == "payload.txt"
    assert audit_calls[0]["detected_type"] == ".txt"
    assert audit_calls[0]["result"] == "rejected"
    assert "真实文件类型" in audit_calls[0]["reason"]
    assert "MZ secret" not in str(audit_calls)


async def test_chat_image_upload_audits_metadata_without_content(monkeypatch):
    audit_calls = []

    def fake_process_uploaded_image(image_data, filename):
        return {
            "success": True,
            "image_content": "base64-image",
            "thumbnail_content": "base64-thumb",
            "width": 1,
            "height": 1,
            "format": "PNG",
            "mime_type": "image/png",
            "size_bytes": len(image_data),
        }

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(chat_router, "process_uploaded_image", fake_process_uploaded_image)
    monkeypatch.setattr(chat_router, "audit_upload", fake_audit_upload)

    payload = b"png-bytes"
    result = await chat_router.upload_image(
        file=FakeUpload("demo.png", payload, "image/png"),
        current_user=SimpleNamespace(uid="user-1", id=5),
        db=object(),
    )

    assert result.success is True
    assert audit_calls[0]["entry"] == "chat_image"
    assert audit_calls[0]["filename"] == "demo.png"
    assert audit_calls[0]["size"] == len(payload)
    assert audit_calls[0]["detected_type"] == ".png"
    assert audit_calls[0]["content_hash"] == hashlib.sha256(payload).hexdigest()
    assert audit_calls[0]["result"] == "success"
    assert "png-bytes" not in str(audit_calls)


async def test_chat_image_upload_audits_rejected_content_type_without_content(monkeypatch):
    audit_calls = []

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(chat_router, "audit_upload", fake_audit_upload)

    with pytest.raises(chat_router.HTTPException):
        await chat_router.upload_image(
            file=FakeUpload("payload.txt", b"MZ secret", "text/plain"),
            current_user=SimpleNamespace(uid="user-1", id=5),
            db=object(),
        )

    assert audit_calls[0]["entry"] == "chat_image"
    assert audit_calls[0]["filename"] == "payload.txt"
    assert audit_calls[0]["detected_type"] == ".txt"
    assert audit_calls[0]["result"] == "rejected"
    assert "只支持图片" in audit_calls[0]["reason"]
    assert "MZ secret" not in str(audit_calls)
