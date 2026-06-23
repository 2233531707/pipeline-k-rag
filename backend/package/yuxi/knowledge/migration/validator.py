"""迁移包安全校验器

负责：
- Zip Slip 防护
- 文件大小/数量限制
- 禁止可执行文件
- Manifest 版本校验
- SHA-256 完整性校验
"""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path
from typing import Any

from yuxi.knowledge.migration import checksums as cs, manifest, schemas
from yuxi.utils import logger
from yuxi.utils.zip_safety import ZipSafetyPolicy, safe_extract_zip, scan_zip_file


class ValidationError(Exception):
    """校验失败"""


PORTABLE_KB_ZIP_POLICY = ZipSafetyPolicy(
    max_file_count=schemas.MAX_FILE_COUNT,
    max_single_file_bytes=schemas.MAX_SINGLE_FILE_BYTES,
    max_total_uncompressed_bytes=schemas.MAX_TOTAL_UNCOMPRESSED_BYTES,
    max_archive_bytes=schemas.MAX_PACKAGE_UPLOAD_BYTES,
    max_compression_ratio=100,
    max_depth=32,
    forbidden_extensions=frozenset(schemas.FORBIDDEN_EXTENSIONS),
    forbidden_names=frozenset(schemas.FORBIDDEN_NAMES),
)


def validate_zip_safety(zip_path: Path, extract_dir: Path) -> list[str]:
    """安全解压 ZIP 文件，返回解压的文件相对路径列表。"""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            report = scan_zip_file(
                zf,
                PORTABLE_KB_ZIP_POLICY,
                archive_size_bytes=zip_path.stat().st_size,
            )
            safe_extract_zip(zf, extract_dir)
    except ValueError as e:
        message = str(e)
        if "路径穿越" in message or "绝对路径" in message or "路径分隔符" in message:
            raise ValidationError(f"Zip Slip 检测: {message}") from e
        raise ValidationError(message) from e

    logger.info(f"ZIP 安全校验通过: {report.file_count} 个文件, {report.total_uncompressed_bytes} bytes")
    return [entry.filename for entry in report.entries if not entry.is_dir]


def validate_manifest_file(root_dir: Path) -> schemas.PackageManifest:
    """读取并校验 manifest.json"""
    manifest_path = root_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ValidationError("缺少 manifest.json")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    pkg = schemas.PackageManifest(**data)
    manifest.validate_manifest(pkg)
    return pkg


def validate_checksums(root_dir: Path, manifest_obj: schemas.PackageManifest) -> None:
    """读取并校验 SHA-256 校验和"""
    checksum_path = root_dir / "checksums" / "sha256.json"
    if not checksum_path.is_file():
        raise ValidationError("缺少 checksums/sha256.json")

    stored = json.loads(checksum_path.read_text(encoding="utf-8"))
    all_files: list[str] = []
    for root, _, filenames in os.walk(root_dir):
        for fn in filenames:
            abs_path = Path(root) / fn
            rel = abs_path.relative_to(root_dir).as_posix()
            all_files.append(rel)

    actual = cs.build_checksums(root_dir, all_files)
    unchecked_files = sorted(set(actual) - set(stored) - {"checksums/sha256.json"})
    if unchecked_files:
        raise ValidationError(f"校验和清单存在未列出的额外文件: {unchecked_files[0]}")

    for rel_path, stored_hash in stored.items():
        if rel_path.startswith("checksums/"):
            continue
        actual_hash = actual.get(rel_path)
        if actual_hash is None:
            raise ValidationError(f"文件缺失: {rel_path}")
        if actual_hash != stored_hash:
            raise ValidationError(f"校验和不匹配: {rel_path}")


def build_preflight_report(root_dir: Path, manifest_obj: schemas.PackageManifest) -> dict[str, Any]:
    """构建预检报告"""
    entities_count = 0
    relationships_count = 0

    entities_file = root_dir / "graph" / "entities.jsonl"
    if entities_file.is_file():
        entities_count = sum(1 for _ in entities_file.open("r", encoding="utf-8"))

    rel_file = root_dir / "graph" / "relationships.jsonl"
    if rel_file.is_file():
        relationships_count = sum(1 for _ in rel_file.open("r", encoding="utf-8"))

    config_file = root_dir / "graph" / "config.json"
    has_graph_config = config_file.is_file()

    chunks_file = root_dir / "chunks" / "chunks.jsonl"
    has_graph_extraction_results = False
    if chunks_file.is_file():
        with chunks_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                if json.loads(line).get("extraction_result"):
                    has_graph_extraction_results = True
                    break

    return {
        "package_version": manifest_obj.package_version,
        "database_name": manifest_obj.database_name,
        "files": manifest_obj.stats.get("files", 0),
        "chunks": manifest_obj.stats.get("chunks", 0),
        "entities": entities_count,
        "relationships": relationships_count,
        "requires_embedding_model": manifest_obj.kb_type.lower() == "milvus",
        "requires_graph_chat_model": has_graph_config and has_graph_extraction_results,
        "warnings": [],
    }
