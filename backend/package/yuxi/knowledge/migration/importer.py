""".yuxikb.zip 导入、索引重建与回滚服务。"""

from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from yuxi import knowledge_base
from yuxi.knowledge.implementations.milvus import MilvusKB
from yuxi.knowledge.migration import schemas, validator
from yuxi.repositories.knowledge_base_repository import KnowledgeBaseRepository
from yuxi.repositories.knowledge_file_repository import KnowledgeFileRepository
from yuxi.storage.minio.client import MinIOClient, get_minio_client
from yuxi.utils import logger

IMPORT_TASK_TYPE = "knowledge_base_portable_import"
IMPORT_CHUNK_BATCH_SIZE = 256


class ImportError(Exception):
    """导入失败。"""


def _generate_file_id() -> str:
    return f"file_{uuid.uuid4().hex}"


def _resolve_import_kb_name(package: schemas.PackageManifest, target_name: str | None) -> str:
    return (target_name or "").strip() or f"{package.database_name} (导入)"


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _count_jsonl(path: Path) -> int:
    return sum(1 for _ in _iter_jsonl(path))


async def run_preflight(zip_path: Path) -> dict[str, Any]:
    tmp_dir = Path(tempfile.mkdtemp(prefix="yuxikb-preflight-"))
    try:
        validator.validate_zip_safety(zip_path, tmp_dir)
        package = validator.validate_manifest_file(tmp_dir)
        validator.validate_checksums(tmp_dir, package)
        report = validator.build_preflight_report(tmp_dir, package)
        report["preflight_passed"] = True
        return report
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def run_import(
    zip_path: Path,
    *,
    target_name: str | None = None,
    embedding_model_spec: str,
    graph_chat_model_spec: str | None = None,
    created_by: str,
    created_by_department_id: str = "",
) -> dict[str, Any]:
    tmp_dir = Path(tempfile.mkdtemp(prefix="yuxikb-import-"))
    new_kb_id: str | None = None
    try:
        validator.validate_zip_safety(zip_path, tmp_dir)
        package = validator.validate_manifest_file(tmp_dir)
        validator.validate_checksums(tmp_dir, package)
        if package.kb_type.lower() != "milvus":
            raise ImportError("便携迁移包当前仅支持 Milvus 知识库")

        database_meta_path = tmp_dir / "database.json"
        database_meta = schemas.DatabaseMeta(name=package.database_name, kb_type=package.kb_type)
        if database_meta_path.is_file():
            database_meta = schemas.DatabaseMeta.model_validate_json(database_meta_path.read_text(encoding="utf-8"))

        group = await knowledge_base.ensure_group_by_name(package.group_name, created_by=created_by)
        created = await knowledge_base.create_database(
            _resolve_import_kb_name(package, target_name),
            database_meta.description,
            kb_type="milvus",
            embedding_model_spec=embedding_model_spec,
            created_by=created_by,
            created_by_department_id=created_by_department_id,
            group_id=group["group_id"] if group else None,
            **database_meta.additional_params,
        )
        new_kb_id = created["kb_id"]
        kb_instance = await knowledge_base.aget_kb(new_kb_id)
        if not isinstance(kb_instance, MilvusKB):
            raise ImportError("导入目标不是 Milvus 知识库")

        records_path = tmp_dir / "files" / "records.jsonl"
        file_id_map: dict[str, str] = {}
        for item in _iter_jsonl(records_path):
            record = schemas.FileRecord.model_validate(item)
            file_id_map[record.file_id] = _generate_file_id()
        if package.stats.get("files", 0) and not file_id_map:
            raise ImportError("迁移包缺少 files/records.jsonl")

        minio_client = get_minio_client()
        file_repo = KnowledgeFileRepository()
        files_uploaded = 0
        for item in _iter_jsonl(records_path):
            record = schemas.FileRecord.model_validate(item)
            new_file_id = file_id_map[record.file_id]
            original_url = None
            markdown_url = None
            if record.original_archive_path:
                source_path = tmp_dir / record.original_archive_path
                if not source_path.is_file():
                    raise ImportError(f"迁移包缺少原始文件: {record.original_archive_path}")
                object_name = f"{new_kb_id}/upload/{new_file_id}_{Path(record.filename).name}"
                original_url = (
                    await minio_client.aupload_file_from_path(
                        MinIOClient.KB_BUCKETS["documents"],
                        object_name,
                        str(source_path),
                        content_type=record.content_type,
                    )
                ).url
            if record.markdown_archive_path:
                markdown_path = tmp_dir / record.markdown_archive_path
                if not markdown_path.is_file():
                    raise ImportError(f"迁移包缺少 Markdown: {record.markdown_archive_path}")
                markdown_url = (
                    await minio_client.aupload_file_from_path(
                        MinIOClient.KB_BUCKETS["parsed"],
                        f"{new_kb_id}/parsed/{new_file_id}.md",
                        str(markdown_path),
                        content_type="text/markdown",
                    )
                ).url

            status = "parsed" if markdown_url else "uploaded"
            metadata = {
                "file_id": new_file_id,
                "kb_id": new_kb_id,
                "parent_id": None,
                "filename": record.filename,
                "original_filename": record.original_filename,
                "file_type": record.file_type,
                "path": original_url,
                "minio_url": original_url,
                "markdown_file": markdown_url,
                "status": status,
                "content_hash": record.content_hash,
                "size": record.file_size,
                "content_type": record.content_type,
                "processing_params": record.processing_params,
                "is_folder": record.is_folder,
                "created_by": created_by,
            }
            await file_repo.upsert(
                new_file_id,
                {
                    "kb_id": new_kb_id,
                    "parent_id": None,
                    "filename": record.filename,
                    "original_filename": record.original_filename,
                    "file_type": record.file_type,
                    "path": original_url,
                    "minio_url": original_url,
                    "markdown_file": markdown_url,
                    "status": status,
                    "content_hash": record.content_hash,
                    "file_size": record.file_size,
                    "content_type": record.content_type,
                    "processing_params": record.processing_params,
                    "is_folder": record.is_folder,
                    "created_by": created_by,
                },
            )
            kb_instance.files_meta[new_file_id] = metadata
            files_uploaded += int(not record.is_folder)

        for item in _iter_jsonl(records_path):
            record = schemas.FileRecord.model_validate(item)
            if not record.parent_id:
                continue
            parent_id = file_id_map.get(record.parent_id)
            if not parent_id:
                raise ImportError(f"文件引用了未知父目录: {record.parent_id}")
            new_file_id = file_id_map[record.file_id]
            await file_repo.upsert(new_file_id, {"parent_id": parent_id})
            kb_instance.files_meta[new_file_id]["parent_id"] = parent_id

        chunk_count = 0
        has_graph_extraction_results = False
        restored_chunks: list[dict[str, Any]] = []
        chunks_path = tmp_dir / "chunks" / "chunks.jsonl"
        for chunk_data in _iter_jsonl(chunks_path):
            record = schemas.ChunkRecord.model_validate(chunk_data)
            new_file_id = file_id_map.get(record.file_id)
            if not new_file_id:
                raise ImportError(f"Chunk 引用了未知文件: {record.file_id}")
            chunk_id = f"{new_file_id}_chunk_{record.chunk_index}"
            has_graph_extraction_results = has_graph_extraction_results or bool(record.extraction_result)
            restored_chunks.append(
                {
                    "id": chunk_id,
                    "chunk_id": chunk_id,
                    "file_id": new_file_id,
                    "chunk_index": record.chunk_index,
                    "content": record.content,
                    "start_char_pos": record.start_char_pos,
                    "end_char_pos": record.end_char_pos,
                    "ent_ids": [],
                    "tags": record.tags,
                    "extraction_result": record.extraction_result,
                    "graph_indexed": not bool(record.extraction_result),
                }
            )
            if len(restored_chunks) >= IMPORT_CHUNK_BATCH_SIZE:
                chunk_count += await kb_instance.restore_chunks(new_kb_id, restored_chunks)
                restored_chunks.clear()
        if restored_chunks:
            chunk_count += await kb_instance.restore_chunks(new_kb_id, restored_chunks)

        query_params_path = tmp_dir / "settings" / "query_params.json"
        if query_params_path.is_file():
            query_params = json.loads(query_params_path.read_text(encoding="utf-8"))
            await KnowledgeBaseRepository().update(new_kb_id, {"query_params": query_params})
            kb_instance.databases_meta[new_kb_id]["query_params"] = query_params

        entities_count = _count_jsonl(tmp_dir / "graph" / "entities.jsonl")
        relationships_count = _count_jsonl(tmp_dir / "graph" / "relationships.jsonl")
        graph_config_path = tmp_dir / "graph" / "config.json"
        graph_result = None
        if has_graph_extraction_results:
            if not graph_config_path.is_file():
                raise ImportError("迁移包包含图谱抽取结果但缺少 graph/config.json")
            if not graph_chat_model_spec:
                raise ImportError("迁移包包含图谱数据，必须选择图谱抽取 Chat 模型")
            from yuxi.knowledge.graphs.milvus_graph_service import MilvusGraphService

            graph_config = json.loads(graph_config_path.read_text(encoding="utf-8"))
            extractor_options = dict(graph_config.get("extractor_options") or {})
            extractor_options["model_spec"] = graph_chat_model_spec
            graph_service = MilvusGraphService(kb_id=new_kb_id)
            await graph_service.configure(
                new_kb_id,
                extractor_type=graph_config.get("extractor_type") or "llm",
                extractor_options=extractor_options,
                created_by=created_by,
            )
            graph_result = await graph_service.build_pending_chunks(new_kb_id, batch_size=100)
            if graph_result["failed"]:
                raise ImportError(f"图谱索引重建失败 {graph_result['failed']} 个 Chunk")

        from yuxi.agents.buildin import agent_manager

        await agent_manager.reload_all()
        return {
            "kb_id": new_kb_id,
            "database_name": created.get("name") or database_meta.name,
            "files_uploaded": files_uploaded,
            "chunks_imported": chunk_count,
            "entities_imported": entities_count,
            "relationships_imported": relationships_count,
            "graph_imported": graph_result is not None,
            "document_vectors_rebuilt": chunk_count,
            "graph_vectors_rebuilt": graph_result["success"] if graph_result else 0,
            "warnings": [],
        }
    except Exception as exc:
        if new_kb_id:
            try:
                await knowledge_base.delete_database(new_kb_id)
            except Exception as cleanup_error:
                logger.error(f"迁移导入回滚失败 kb_id={new_kb_id}: {cleanup_error}")
        if isinstance(exc, (validator.ValidationError, ImportError)):
            raise
        raise ImportError(f"导入失败: {exc}") from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
