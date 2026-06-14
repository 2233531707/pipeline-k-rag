"""SHA-256 校验和计算"""

from __future__ import annotations

import hashlib
from pathlib import Path


def compute_sha256_hex(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def build_checksums(root_dir: Path, files: list[str]) -> dict[str, str]:
    """对 root_dir 下的每个相对文件路径计算 SHA-256。

    files 中的路径相对于 root_dir。
    """
    checksums: dict[str, str] = {}
    for rel_path in sorted(files):
        abs_path = root_dir / rel_path
        if abs_path.is_file():
            checksums[rel_path.replace("\\", "/")] = compute_sha256_hex(abs_path)
    return checksums
