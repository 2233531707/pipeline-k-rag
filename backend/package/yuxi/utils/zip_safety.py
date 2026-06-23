"""Shared ZIP safety scanning helpers."""

from __future__ import annotations

import re
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class ZipSafetyPolicy:
    max_archive_bytes: int | None = None
    max_file_count: int | None = None
    max_single_file_bytes: int | None = None
    max_total_uncompressed_bytes: int | None = None
    max_compression_ratio: float | None = None
    max_depth: int | None = None
    forbidden_extensions: frozenset[str] = field(default_factory=frozenset)
    forbidden_names: frozenset[str] = field(default_factory=frozenset)
    warning_extensions: frozenset[str] = field(default_factory=frozenset)
    text_extensions: frozenset[str] = field(default_factory=frozenset)
    allowed_binary_extensions: frozenset[str] = field(default_factory=frozenset)
    max_unknown_binary_bytes: int | None = None
    forbidden_extension_label: str = "禁止的文件类型"
    forbidden_name_label: str = "禁止的文件名"
    warning_extension_label: str = "风险文件"
    unknown_binary_label: str = "未知大二进制文件"


@dataclass(frozen=True)
class ZipSafetyEntry:
    filename: str
    file_size: int
    compress_size: int
    suffix: str
    is_dir: bool = False


@dataclass(frozen=True)
class ZipSafetyReport:
    entries: list[ZipSafetyEntry]
    file_count: int
    archive_size_bytes: int | None
    total_uncompressed_bytes: int
    total_compressed_bytes: int
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "file_count": self.file_count,
            "archive_size_bytes": self.archive_size_bytes,
            "total_uncompressed_bytes": self.total_uncompressed_bytes,
            "warnings": list(self.warnings),
        }


def normalize_zip_entry_path(name: str, *, max_depth: int | None = None) -> PurePosixPath:
    if not name or "\x00" in name:
        raise ValueError("ZIP 包含非法路径")
    if "\\" in name:
        raise ValueError(f"ZIP 包含不安全路径分隔符: {name}")
    if re.match(r"^[A-Za-z]:", name):
        raise ValueError(f"ZIP 包含不安全绝对路径: {name}")
    pure = PurePosixPath(name)
    if pure.is_absolute():
        raise ValueError(f"ZIP 包含不安全绝对路径: {name}")
    if ".." in pure.parts:
        raise ValueError(f"ZIP 包含路径穿越片段: {name}")
    if max_depth is not None and len(pure.parts) > max_depth:
        raise ValueError(f"ZIP 目录层级过深: {name}")
    return pure


def scan_zip_file(
    zip_file: zipfile.ZipFile,
    policy: ZipSafetyPolicy,
    *,
    archive_size_bytes: int | None = None,
) -> ZipSafetyReport:
    if (
        archive_size_bytes is not None
        and policy.max_archive_bytes is not None
        and archive_size_bytes > policy.max_archive_bytes
    ):
        raise ValueError(f"ZIP 文件过大: {archive_size_bytes} bytes")

    entries: list[ZipSafetyEntry] = []
    warnings: list[str] = []
    file_count = 0
    total_uncompressed = 0
    total_compressed = 0

    for entry in zip_file.infolist():
        pure = normalize_zip_entry_path(entry.filename, max_depth=policy.max_depth)
        suffix = Path(entry.filename).suffix.lower()
        entries.append(
            ZipSafetyEntry(
                filename=entry.filename,
                file_size=entry.file_size,
                compress_size=max(entry.compress_size, 0),
                suffix=suffix,
                is_dir=entry.is_dir(),
            )
        )
        if entry.is_dir():
            continue

        file_count += 1
        if policy.max_file_count is not None and file_count > policy.max_file_count:
            raise ValueError(f"ZIP 文件数量超限: {file_count} > {policy.max_file_count}")
        if policy.max_single_file_bytes is not None and entry.file_size > policy.max_single_file_bytes:
            raise ValueError(f"ZIP 单文件过大: {entry.filename} ({entry.file_size} bytes)")

        total_uncompressed += entry.file_size
        total_compressed += max(entry.compress_size, 0)
        if policy.max_total_uncompressed_bytes is not None and total_uncompressed > policy.max_total_uncompressed_bytes:
            raise ValueError(f"ZIP 解压总大小超限: {total_uncompressed} > {policy.max_total_uncompressed_bytes}")

        if policy.max_compression_ratio is not None:
            if entry.file_size > 0 and entry.compress_size == 0:
                raise ValueError(f"ZIP 压缩比过高: {entry.filename}")
            if entry.file_size >= 1024 and entry.compress_size > 0:
                ratio = entry.file_size / entry.compress_size
                if ratio > policy.max_compression_ratio:
                    raise ValueError(f"ZIP 压缩比过高: {entry.filename}")

        parts_lower = [part.lower() for part in pure.parts]
        filename_lower = Path(entry.filename).name.lower()
        for forbidden in policy.forbidden_names:
            forbidden_lower = forbidden.lower()
            if any(forbidden_lower in part for part in parts_lower) or forbidden_lower in filename_lower:
                raise ValueError(f"ZIP 包含{policy.forbidden_name_label}: {entry.filename}")

        if suffix in policy.forbidden_extensions:
            raise ValueError(f"ZIP 包含{policy.forbidden_extension_label}: {entry.filename}")
        if suffix in policy.warning_extensions:
            warnings.append(f"{policy.warning_extension_label}: {entry.filename}")
            continue
        if (
            policy.max_unknown_binary_bytes is not None
            and suffix not in policy.text_extensions
            and suffix not in policy.allowed_binary_extensions
            and entry.file_size > policy.max_unknown_binary_bytes
        ):
            raise ValueError(f"ZIP 包含{policy.unknown_binary_label}: {entry.filename}")

    if policy.max_compression_ratio is not None and total_compressed > 0 and total_uncompressed >= 1024:
        ratio = total_uncompressed / total_compressed
        if ratio > policy.max_compression_ratio:
            raise ValueError("ZIP 压缩比过高")

    return ZipSafetyReport(
        entries=entries,
        file_count=file_count,
        archive_size_bytes=archive_size_bytes,
        total_uncompressed_bytes=total_uncompressed,
        total_compressed_bytes=total_compressed,
        warnings=warnings,
    )


def safe_extract_zip(zip_file: zipfile.ZipFile, extract_dir: Path) -> None:
    extract_root = extract_dir.resolve()
    for entry in zip_file.infolist():
        pure = normalize_zip_entry_path(entry.filename)
        target_path = (extract_root / pure).resolve()
        try:
            target_path.relative_to(extract_root)
        except ValueError:
            raise ValueError(f"ZIP 包含路径穿越片段: {entry.filename}") from None
        if entry.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with zip_file.open(entry, "r") as source, target_path.open("wb") as target:
            shutil.copyfileobj(source, target)
