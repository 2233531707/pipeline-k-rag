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


class ValidationError(Exception):
    """校验失败"""


def validate_zip_safety(zip_path: Path, extract_dir: Path) -> list[str]:
    """安全解压 ZIP 文件，返回解压的文件相对路径列表。

    执行：
    - Zip Slip 防护（每个条目规范化路径必须在 extract_dir 内）
    - 文件数量上限检查
    - 单文件大小上限检查
    - 禁止文件扩展名检查
    """
    file_count = 0
    total_size = 0
    extracted: list[str] = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for entry in zf.infolist():
            if entry.is_dir():
                continue

            # Zip Slip 防护
            target_path = (extract_dir / entry.filename).resolve()
            extract_dir_resolved = extract_dir.resolve()
            if not str(target_path).startswith(str(extract_dir_resolved) + os.sep) and target_path != extract_dir_resolved:
                raise ValidationError(f"Zip Slip 检测: {entry.filename}")

            # 文件数量限制
            file_count += 1
            if file_count > schemas.MAX_FILE_COUNT:
                raise ValidationError(f"文件数量超限: {file_count} > {schemas.MAX_FILE_COUNT}")

            # 单文件大小限制
            if entry.file_size > schemas.MAX_SINGLE_FILE_BYTES:
                raise ValidationError(f"单文件过大: {entry.filename} ({entry.file_size} bytes)")

            # 禁止扩展名
            ext = Path(entry.filename).suffix.lower()
            if ext in schemas.FORBIDDEN_EXTENSIONS:
                raise ValidationError(f"禁止的文件类型: {entry.filename} ({ext})")

            # 禁止文件名含敏感词
            name_lower = Path(entry.filename).name.lower()
            for forbidden in schemas.FORBIDDEN_NAMES:
                if forbidden in name_lower:
                    raise ValidationError(f"禁止的文件名: {entry.filename} (含 '{forbidden}')")

            total_size += entry.file_size
            if total_size > schemas.MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise ValidationError(f"解压总大小超限: {total_size} > {schemas.MAX_TOTAL_UNCOMPRESSED_BYTES}")

            # 解压
            target_path.parent.mkdir(parents=True, exist_ok=True)
            zf.extract(entry, extract_dir)
            extracted.append(entry.filename)

    logger.info(f"ZIP 安全校验通过: {file_count} 个文件, {total_size} bytes")
    return extracted


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
