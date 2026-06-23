from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from yuxi.knowledge.parser import zip_utils


def _write_zip(path: Path, files: dict[str, bytes | str]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content.encode("utf-8") if isinstance(content, str) else content)


def test_ordinary_knowledge_zip_rejects_fake_image(tmp_path: Path) -> None:
    zip_path = tmp_path / "doc.zip"
    _write_zip(zip_path, {"full.md": "![x](images/a.png)", "images/a.png": b"not a png"})

    with pytest.raises(ValueError, match="图片真实类型不匹配"):
        zip_utils.process_zip_file_sync(str(zip_path))


def test_ordinary_knowledge_zip_rejects_too_many_markdown_files(tmp_path: Path) -> None:
    zip_path = tmp_path / "doc.zip"
    files = {f"docs/{i}.md": "content" for i in range(zip_utils.ORDINARY_KB_ZIP_MAX_MARKDOWN_COUNT + 1)}

    _write_zip(zip_path, files)

    with pytest.raises(ValueError, match="Markdown 文件数量超限"):
        zip_utils.process_zip_file_sync(str(zip_path))


def test_ordinary_knowledge_zip_rejects_compression_bomb(tmp_path: Path) -> None:
    zip_path = tmp_path / "doc.zip"
    _write_zip(zip_path, {"full.md": "0" * (1024 * 1024)})

    with pytest.raises(ValueError, match="压缩比过高"):
        zip_utils.process_zip_file_sync(str(zip_path))
