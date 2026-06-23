"""测试便携迁移包导入与失败回滚。"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from yuxi.knowledge.migration import checksums, importer, manifest, schemas


def _build_package(tmp_path: Path, *, group_name: str | None = None) -> Path:
    root = tmp_path / "package"
    (root / "files" / "originals").mkdir(parents=True)
    (root / "files" / "parsed").mkdir(parents=True)
    (root / "chunks").mkdir()
    (root / "checksums").mkdir()

    (root / "files" / "originals" / "old-file__demo.txt").write_text("hello", encoding="utf-8")
    (root / "files" / "parsed" / "old-file.md").write_text("# hello", encoding="utf-8")
    file_record = schemas.FileRecord(
        file_id="old-file",
        filename="demo.txt",
        original_filename="demo",
        file_type=".txt",
        original_archive_path="files/originals/old-file__demo.txt",
        markdown_archive_path="files/parsed/old-file.md",
    )
    (root / "files" / "records.jsonl").write_text(file_record.model_dump_json() + "\n", encoding="utf-8")

    chunk_record = schemas.ChunkRecord(
        chunk_id="old-chunk",
        file_id="old-file",
        chunk_index=0,
        content="hello",
    )
    (root / "chunks" / "chunks.jsonl").write_text(chunk_record.model_dump_json() + "\n", encoding="utf-8")
    package_manifest = manifest.build_manifest(
        database_name="来源知识库",
        kb_type="milvus",
        group_name=group_name,
        file_count=1,
        chunk_count=1,
    )
    (root / "manifest.json").write_text(package_manifest.model_dump_json(indent=2), encoding="utf-8")
    (root / "database.json").write_text(
        schemas.DatabaseMeta(name="来源知识库", description="迁移测试").model_dump_json(indent=2),
        encoding="utf-8",
    )

    package_files = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    ]
    (root / "checksums" / "sha256.json").write_text(
        json.dumps(checksums.build_checksums(root, package_files)),
        encoding="utf-8",
    )

    package_path = tmp_path / "sample.yuxikb.zip"
    with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in root.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(root).as_posix())
    return package_path


class FakeMilvusKB:
    def __init__(self, *, fail_restore: bool = False):
        self.fail_restore = fail_restore
        self.files_meta = {}
        self.databases_meta = {"kb-actual": {}}
        self.restored_chunks = []

    async def restore_chunks(self, kb_id: str, chunks: list[dict]) -> int:
        if self.fail_restore:
            raise RuntimeError("restore failed")
        assert kb_id == "kb-actual"
        self.restored_chunks = chunks
        return len(chunks)


class FakeFileRepository:
    def __init__(self):
        self.records = []

    async def upsert(self, file_id: str, data: dict):
        self.records.append((file_id, data))


class FakeMinioClient:
    def __init__(self):
        self.uploads = []

    async def aupload_file_from_path(self, bucket_name: str, object_name: str, file_path: str, content_type=None):
        self.uploads.append((bucket_name, object_name, Path(file_path).read_bytes(), content_type))
        return SimpleNamespace(url=f"minio://{bucket_name}/{object_name}")


@pytest.mark.asyncio
async def test_import_uses_created_kb_id_and_remaps_records(tmp_path: Path, monkeypatch):
    package_path = _build_package(tmp_path)
    fake_kb = FakeMilvusKB()
    fake_file_repo = FakeFileRepository()
    fake_minio = FakeMinioClient()

    monkeypatch.setattr(importer, "MilvusKB", FakeMilvusKB)
    monkeypatch.setattr(
        importer.knowledge_base,
        "create_database",
        AsyncMock(return_value={"kb_id": "kb-actual", "name": "导入知识库"}),
    )
    monkeypatch.setattr(importer.knowledge_base, "aget_kb", AsyncMock(return_value=fake_kb))
    monkeypatch.setattr(importer.knowledge_base, "delete_database", AsyncMock())
    monkeypatch.setattr(importer, "KnowledgeFileRepository", lambda: fake_file_repo)
    monkeypatch.setattr(importer, "get_minio_client", lambda: fake_minio)

    from yuxi.agents.buildin import agent_manager

    monkeypatch.setattr(agent_manager, "reload_all", AsyncMock())

    result = await importer.run_import(
        package_path,
        target_name="导入知识库",
        embedding_model_spec="provider:embedding",
        created_by="user-1",
    )

    assert result["kb_id"] == "kb-actual"
    assert result["files_uploaded"] == 1
    assert result["chunks_imported"] == 1
    new_file_id = next(iter(fake_kb.files_meta))
    assert new_file_id != "old-file"
    assert fake_kb.restored_chunks[0]["file_id"] == new_file_id
    assert fake_kb.restored_chunks[0]["id"] == f"{new_file_id}_chunk_0"
    assert all("kb-actual/" in upload[1] for upload in fake_minio.uploads)
    assert fake_file_repo.records[0][0] == new_file_id


@pytest.mark.asyncio
async def test_import_reuses_or_creates_manifest_group(tmp_path: Path, monkeypatch):
    package_path = _build_package(tmp_path, group_name="项目资料")
    fake_kb = FakeMilvusKB()

    async def fake_ensure_group(group_name, created_by=None):
        assert group_name == "项目资料"
        assert created_by == "user-1"
        return {"group_id": "group-1", "name": group_name, "is_default": False}

    create_database = AsyncMock(return_value={"kb_id": "kb-actual", "name": "导入知识库"})
    monkeypatch.setattr(importer, "MilvusKB", FakeMilvusKB)
    monkeypatch.setattr(importer.knowledge_base, "ensure_group_by_name", fake_ensure_group)
    monkeypatch.setattr(importer.knowledge_base, "create_database", create_database)
    monkeypatch.setattr(importer.knowledge_base, "aget_kb", AsyncMock(return_value=fake_kb))
    monkeypatch.setattr(importer.knowledge_base, "delete_database", AsyncMock())
    monkeypatch.setattr(importer, "KnowledgeFileRepository", FakeFileRepository)
    monkeypatch.setattr(importer, "get_minio_client", FakeMinioClient)

    from yuxi.agents.buildin import agent_manager

    monkeypatch.setattr(agent_manager, "reload_all", AsyncMock())

    await importer.run_import(
        package_path,
        target_name="导入知识库",
        embedding_model_spec="provider:embedding",
        created_by="user-1",
    )

    assert create_database.await_args.kwargs["group_id"] == "group-1"


@pytest.mark.asyncio
async def test_import_deletes_created_database_when_restore_fails(tmp_path: Path, monkeypatch):
    package_path = _build_package(tmp_path)
    fake_kb = FakeMilvusKB(fail_restore=True)
    delete_database = AsyncMock()

    monkeypatch.setattr(importer, "MilvusKB", FakeMilvusKB)
    monkeypatch.setattr(
        importer.knowledge_base,
        "create_database",
        AsyncMock(return_value={"kb_id": "kb-actual", "name": "导入知识库"}),
    )
    monkeypatch.setattr(importer.knowledge_base, "aget_kb", AsyncMock(return_value=fake_kb))
    monkeypatch.setattr(importer.knowledge_base, "delete_database", delete_database)
    monkeypatch.setattr(importer, "KnowledgeFileRepository", FakeFileRepository)
    monkeypatch.setattr(importer, "get_minio_client", FakeMinioClient)

    with pytest.raises(importer.ImportError, match="restore failed"):
        await importer.run_import(
            package_path,
            embedding_model_spec="provider:embedding",
            created_by="user-1",
        )

    delete_database.assert_awaited_once_with("kb-actual")
