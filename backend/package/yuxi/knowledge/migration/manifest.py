"""Manifest 构建与校验"""

from __future__ import annotations

from yuxi.knowledge.migration.schemas import PackageManifest


def build_manifest(
    database_name: str,
    kb_type: str,
    *,
    group_name: str | None = None,
    file_count: int = 0,
    chunk_count: int = 0,
    entity_count: int = 0,
    relationship_count: int = 0,
    total_original_bytes: int = 0,
) -> PackageManifest:
    return PackageManifest(
        database_name=database_name,
        kb_type=kb_type,
        group_name=group_name,
        stats={
            "files": file_count,
            "chunks": chunk_count,
            "entities": entity_count,
            "relationships": relationship_count,
            "total_original_bytes": total_original_bytes,
        },
    )


def validate_manifest(manifest: PackageManifest) -> None:
    if manifest.package_version != "1":
        raise ValueError(f"不支持的包版本: {manifest.package_version}，仅支持版本 1")
    stats = manifest.stats or {}
    if stats.get("files", 0) < 0:
        raise ValueError("manifest.stats.files 必须为非负整数")
    if stats.get("chunks", 0) < 0:
        raise ValueError("manifest.stats.chunks 必须为非负整数")
