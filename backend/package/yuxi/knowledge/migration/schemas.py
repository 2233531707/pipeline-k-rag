"""迁移包数据模型"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class PackageManifest(BaseModel):
    package_version: str = Field(default="1", description="包格式版本")
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    generator: str = Field(default="yuxi-kb-export/1.0")
    database_name: str = Field(description="知识库名称")
    kb_type: str = Field(description="知识库类型")
    group_name: str | None = Field(default=None, description="知识库分组名称")
    stats: dict[str, int] = Field(default_factory=dict, description="统计信息")


class DatabaseMeta(BaseModel):
    name: str
    description: str = ""
    kb_type: str = "milvus"
    additional_params: dict[str, Any] = Field(default_factory=dict)


class FileRecord(BaseModel):
    file_id: str
    parent_id: str | None = None
    filename: str
    original_filename: str | None = None
    file_type: str | None = None
    content_hash: str | None = None
    file_size: int | None = None
    content_type: str | None = None
    processing_params: dict[str, Any] = Field(default_factory=dict)
    is_folder: bool = False
    original_archive_path: str | None = None
    markdown_archive_path: str | None = None


class ChunkRecord(BaseModel):
    chunk_id: str
    file_id: str
    chunk_index: int = 0
    content: str = ""
    start_char_pos: int = 0
    end_char_pos: int = 0
    ent_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    extraction_result: dict[str, Any] | None = None
    graph_indexed: bool = False


class EntityRecord(BaseModel):
    entity_id: str
    name: str
    label: str = "Entity"
    attributes: list[dict[str, Any]] = Field(default_factory=list)
    entity_type: str = ""


class RelationshipRecord(BaseModel):
    source_entity_id: str
    target_entity_id: str
    relation_type: str = "RELATED_TO"
    keywords: str = ""


class ExportTaskPayload(BaseModel):
    kb_id: str
    created_by: str


EXPORT_TASK_TYPE = "knowledge_base_portable_export"

# 安全限制
MAX_FILE_COUNT = 10_000
MAX_SINGLE_FILE_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_TOTAL_UNCOMPRESSED_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB
MAX_PACKAGE_UPLOAD_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB，上传过程写入磁盘
FORBIDDEN_EXTENSIONS = {".py", ".js", ".sh", ".bat", ".exe", ".dll", ".so", ".cmd", ".ps1"}
FORBIDDEN_NAMES = {"api_key", ".env", "secrets", "credentials", "token"}
