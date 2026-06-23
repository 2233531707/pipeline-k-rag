from hashlib import sha256
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

from server.routers import knowledge_eval_router


pytestmark = pytest.mark.asyncio


async def test_evaluation_jsonl_rejects_oversize_before_service(monkeypatch):
    service_created = False

    class FakeService:
        def __init__(self):
            nonlocal service_created
            service_created = True

    monkeypatch.setattr(knowledge_eval_router, "MAX_EVALUATION_JSONL_BYTES", 5)
    monkeypatch.setattr(knowledge_eval_router, "EvaluationService", FakeService)

    with pytest.raises(HTTPException) as exc_info:
        await knowledge_eval_router.upload_evaluation_dataset(
            kb_id="kb_1",
            file=UploadFile(filename="dataset.jsonl", file=BytesIO(b'{"query":"too large"}\n')),
            name="dataset",
            description="",
            current_user=SimpleNamespace(uid="admin"),
        )

    assert exc_info.value.status_code == 400
    assert "20 MB" in exc_info.value.detail
    assert service_created is False


async def test_evaluation_jsonl_upload_records_metadata_only_audit(monkeypatch):
    payload = b"{\"query\":\"where is valve 7\"}\n"
    audit_calls = []

    class FakeService:
        async def upload_dataset_from_path(
            self, *, kb_id, file_path, filename, name, description, created_by
        ):
            assert file_path.read_bytes() == payload
            return {"id": "dataset-1"}

    async def fake_audit_upload(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(knowledge_eval_router, "EvaluationService", FakeService)
    monkeypatch.setattr(knowledge_eval_router, "audit_upload", fake_audit_upload, raising=False)

    result = await knowledge_eval_router.upload_evaluation_dataset(
        kb_id="kb_1",
        file=UploadFile(filename="dataset.jsonl", file=BytesIO(payload)),
        name="dataset",
        description="",
        current_user=SimpleNamespace(uid="admin", id=9),
        db=object(),
    )

    assert result["data"]["id"] == "dataset-1"
    assert audit_calls == [
        {
            "db": audit_calls[0]["db"],
            "user_id": 9,
            "entry": "evaluation_jsonl",
            "filename": "dataset.jsonl",
            "size": len(payload),
            "detected_type": ".jsonl",
            "content_hash": sha256(payload).hexdigest(),
            "result": "success",
        }
    ]
    assert payload.decode() not in str(audit_calls)
