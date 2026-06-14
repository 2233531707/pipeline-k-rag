""".yuxikb.zip 导出服务。"""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

from yuxi import knowledge_base
from yuxi.knowledge.migration import checksums, manifest, schemas
from yuxi.knowledge.utils.kb_utils import is_minio_url, parse_minio_url
from yuxi.repositories.knowledge_chunk_repository import KnowledgeChunkRepository
from yuxi.repositories.knowledge_file_repository import KnowledgeFileRepository
from yuxi.repositories.knowledge_graph_repository import KnowledgeGraphRepository
from yuxi.storage.minio.client import get_minio_client
from yuxi.utils import logger

EXPORT_BATCH_SIZE = 500


def _sanitise_filename(name: str) -> str:
    return name.replace("/", "_").replace("\\", "_").replace("..", "_")


def _strip_sensitive(value: Any) -> Any:
    forbidden = {"api_key", "api_token", "token", "secret", "password", "credential"}
    if isinstance(value, dict):
        return {
            key: _strip_sensitive(item)
            for key, item in value.items()
            if not any(part in key.lower() for part in forbidden)
        }
    if isinstance(value, list):
        return [_strip_sensitive(item) for item in value]
    return value


async def _download_minio_file(url: str | None, destination: Path) -> bool:
    if not url or not is_minio_url(url):
        return False
    bucket_name, object_name = parse_minio_url(url)
    await get_minio_client().adownload_file_to_path(bucket_name, object_name, str(destination))
    return True


async def export_portable_package(kb_id: str, work_dir: str, *, created_by: str) -> Path:
    db_info = await knowledge_base.get_database_info(kb_id)
    if not db_info:
        raise ValueError(f"知识库 {kb_id} 不存在")
    if str(db_info.get("kb_type") or "").lower() != "milvus":
        raise ValueError("便携迁移包当前仅支持 Milvus 知识库")

    kb_name = db_info.get("name") or kb_id
    tmp_root = Path(work_dir) / f"export-{kb_id}"
    tmp_root.mkdir(parents=True, exist_ok=True)

    try:
        originals_dir = tmp_root / "files" / "originals"
        parsed_dir = tmp_root / "files" / "parsed"
        chunks_dir = tmp_root / "chunks"
        graph_dir = tmp_root / "graph"
        settings_dir = tmp_root / "settings"
        checksums_dir = tmp_root / "checksums"
        for directory in (originals_dir, parsed_dir, chunks_dir, graph_dir, settings_dir, checksums_dir):
            directory.mkdir(parents=True, exist_ok=True)

        graph_config: dict[str, Any] = {}
        try:
            from yuxi.knowledge.graphs.milvus_graph_service import MilvusGraphService

            graph_config = (await MilvusGraphService(kb_id=kb_id).get_status(kb_id)).get("config") or {}
        except Exception as exc:
            logger.warning(f"读取图谱配置失败，导出将不包含配置: {exc}")
        if graph_config:
            graph_config = _strip_sensitive(graph_config)
            extractor_options = dict(graph_config.get("extractor_options") or {})
            extractor_options["model_spec"] = ""
            graph_config["extractor_options"] = extractor_options
            (graph_dir / "config.json").write_text(
                json.dumps(graph_config, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        file_count = 0
        total_bytes = 0
        file_repo = KnowledgeFileRepository()
        with (tmp_root / "files" / "records.jsonl").open("w", encoding="utf-8") as records_handle:
            after_id = 0
            while batch := await file_repo.list_batch_by_kb_id(
                kb_id,
                after_id=after_id,
                limit=EXPORT_BATCH_SIZE,
            ):
                for file_obj in batch:
                    original_archive_path = None
                    markdown_archive_path = None
                    if not file_obj.is_folder:
                        original_name = _sanitise_filename(file_obj.filename or file_obj.file_id)
                        original_path = originals_dir / f"{file_obj.file_id}__{original_name}"
                        if await _download_minio_file(file_obj.minio_url or file_obj.path, original_path):
                            original_archive_path = original_path.relative_to(tmp_root).as_posix()
                            total_bytes += original_path.stat().st_size

                        markdown_path = parsed_dir / f"{file_obj.file_id}.md"
                        if await _download_minio_file(file_obj.markdown_file, markdown_path):
                            markdown_archive_path = markdown_path.relative_to(tmp_root).as_posix()

                    record = schemas.FileRecord(
                        file_id=file_obj.file_id,
                        parent_id=file_obj.parent_id,
                        filename=file_obj.filename,
                        original_filename=file_obj.original_filename,
                        file_type=file_obj.file_type,
                        content_hash=file_obj.content_hash,
                        file_size=file_obj.file_size,
                        content_type=file_obj.content_type,
                        processing_params=_strip_sensitive(file_obj.processing_params or {}),
                        is_folder=bool(file_obj.is_folder),
                        original_archive_path=original_archive_path,
                        markdown_archive_path=markdown_archive_path,
                    )
                    records_handle.write(record.model_dump_json() + "\n")
                    file_count += 1
                after_id = batch[-1].id

        chunk_count = 0
        chunk_repo = KnowledgeChunkRepository()
        with (chunks_dir / "chunks.jsonl").open("w", encoding="utf-8") as chunks_handle:
            after_id = 0
            while batch := await chunk_repo.list_batch_by_kb_id(
                kb_id,
                after_id=after_id,
                limit=EXPORT_BATCH_SIZE,
            ):
                for chunk in batch:
                    record = schemas.ChunkRecord(
                        chunk_id=chunk.chunk_id,
                        file_id=chunk.file_id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content or "",
                        start_char_pos=chunk.start_char_pos or 0,
                        end_char_pos=chunk.end_char_pos or 0,
                        ent_ids=list(chunk.ent_ids or []),
                        tags=list(chunk.tags or []),
                        extraction_result=chunk.extraction_result,
                        graph_indexed=bool(chunk.graph_indexed),
                    )
                    chunks_handle.write(record.model_dump_json() + "\n")
                    chunk_count += 1
                after_id = batch[-1].id

        graph_repo = KnowledgeGraphRepository()
        entity_count = 0
        with (graph_dir / "entities.jsonl").open("w", encoding="utf-8") as entities_handle:
            after_id = 0
            while batch := await graph_repo.list_entities_batch(
                kb_id,
                after_id=after_id,
                limit=EXPORT_BATCH_SIZE,
            ):
                for entity in batch:
                    entities_handle.write(
                        json.dumps(
                            {
                                "entity_id": entity.entity_id,
                                "name": entity.name,
                                "label": entity.label,
                                "attributes": entity.attributes or [],
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    entity_count += 1
                after_id = batch[-1].id

        relationship_count = 0
        with (graph_dir / "relationships.jsonl").open("w", encoding="utf-8") as relationships_handle:
            after_id = 0
            while batch := await graph_repo.list_triples_batch(
                kb_id,
                after_id=after_id,
                limit=EXPORT_BATCH_SIZE,
            ):
                for triple in batch:
                    relationships_handle.write(
                        json.dumps(
                            {
                                "source_entity_id": triple.source_entity_id,
                                "target_entity_id": triple.target_entity_id,
                                "relation_type": triple.relation_type,
                                "keywords": triple.content,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    relationship_count += 1
                after_id = batch[-1].id

        query_params = _strip_sensitive(db_info.get("query_params") or {})
        if query_params:
            (settings_dir / "query_params.json").write_text(
                json.dumps(query_params, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        package_manifest = manifest.build_manifest(
            database_name=kb_name,
            kb_type="milvus",
            file_count=file_count,
            chunk_count=chunk_count,
            entity_count=entity_count,
            relationship_count=relationship_count,
            total_original_bytes=total_bytes,
        )
        (tmp_root / "manifest.json").write_text(package_manifest.model_dump_json(indent=2), encoding="utf-8")
        safe_additional_params = {
            key: value
            for key, value in _strip_sensitive(db_info.get("additional_params") or {}).items()
            if key in {"chunk_preset_id", "chunk_parser_config", "auto_generate_questions"}
        }
        database_meta = schemas.DatabaseMeta(
            name=kb_name,
            description=db_info.get("description") or "",
            kb_type="milvus",
            additional_params=safe_additional_params,
        )
        (tmp_root / "database.json").write_text(database_meta.model_dump_json(indent=2), encoding="utf-8")

        package_files = [
            (Path(root) / filename).relative_to(tmp_root).as_posix()
            for root, _, filenames in os.walk(tmp_root)
            for filename in filenames
        ]
        checksum_map = checksums.build_checksums(tmp_root, package_files)
        (checksums_dir / "sha256.json").write_text(
            json.dumps(checksum_map, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        zip_path = Path(work_dir) / f"{_sanitise_filename(kb_name)}-{kb_id[:8]}.yuxikb.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for root, _, filenames in os.walk(tmp_root):
                for filename in filenames:
                    source_path = Path(root) / filename
                    archive.write(source_path, source_path.relative_to(tmp_root).as_posix())
        logger.info(f"便携迁移包导出完成: {zip_path}")
        return zip_path
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
