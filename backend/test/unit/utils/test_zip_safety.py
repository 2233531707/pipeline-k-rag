from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from yuxi.utils.zip_safety import ZipSafetyPolicy, safe_extract_zip, scan_zip_file


def _zip_bytes(files: dict[str, bytes | str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content.encode("utf-8") if isinstance(content, str) else content)
    return buf.getvalue()


def _scan(files: dict[str, bytes | str], policy: ZipSafetyPolicy):
    data = _zip_bytes(files)
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        return scan_zip_file(zf, policy, archive_size_bytes=len(data))


def test_shared_zip_scan_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="路径穿越"):
        _scan({"../x.md": "bad"}, ZipSafetyPolicy())


def test_shared_zip_scan_rejects_file_count_and_single_file_size() -> None:
    with pytest.raises(ValueError, match="文件数量超限"):
        _scan({"a.md": "a", "b.md": "b"}, ZipSafetyPolicy(max_file_count=1))

    with pytest.raises(ValueError, match="单文件过大"):
        _scan({"a.md": "abcd"}, ZipSafetyPolicy(max_single_file_bytes=3))


def test_shared_zip_scan_reports_warning_extensions() -> None:
    report = _scan(
        {"SKILL.md": "ok", "scripts/run.py": "print(1)"},
        ZipSafetyPolicy(warning_extensions=frozenset({".py"}), warning_extension_label="脚本风险"),
    )

    assert report.warnings == ["脚本风险: scripts/run.py"]


def test_shared_zip_scan_accepts_windows_separators_for_normal_entries() -> None:
    report = _scan(
        {"scripts\\audit_uploaded_plan.py": "print(1)"},
        ZipSafetyPolicy(warning_extensions=frozenset({".py"}), warning_extension_label="脚本风险"),
    )

    assert report.file_count == 1
    assert report.warnings == ["脚本风险: scripts\\audit_uploaded_plan.py"]


def test_safe_extract_zip_accepts_windows_directory_entries(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("backend\\configs\\", b"")
        zf.writestr("backend\\configs\\rule_profiles\\urban.yaml", "name: urban\n")

    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    with zipfile.ZipFile(io.BytesIO(buf.getvalue()), "r") as zf:
        safe_extract_zip(zf, extract_dir)

    assert (extract_dir / "backend" / "configs").is_dir()
    assert (extract_dir / "backend" / "configs" / "rule_profiles" / "urban.yaml").read_text(
        encoding="utf-8"
    ) == "name: urban\n"
