"""测试 .yuxikb.zip 导入预检与校验"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from yuxi.knowledge.migration import schemas, validator


class TestZipSlipProtection:
    def test_normal_zip_passes(self, tmp_path: Path):
        zip_path = tmp_path / "good.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("manifest.json", json.dumps({"package_version": "1", "database_name": "test", "kb_type": "milvus", "stats": {}}))
            zf.writestr("chunks/chunks.jsonl", "{}")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        files = validator.validate_zip_safety(zip_path, extract_dir)
        assert len(files) == 2

    def test_dotdot_path_rejected(self, tmp_path: Path):
        zip_path = tmp_path / "bad.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../etc/passwd", "malicious")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        with pytest.raises(validator.ValidationError, match="Zip Slip"):
            validator.validate_zip_safety(zip_path, extract_dir)

    def test_forbidden_extension_rejected(self, tmp_path: Path):
        zip_path = tmp_path / "bad.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("manifest.json", json.dumps({"package_version": "1", "database_name": "test", "kb_type": "milvus", "stats": {}}))
            zf.writestr("script.py", "print('bad')")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        with pytest.raises(validator.ValidationError, match="禁止的文件类型"):
            validator.validate_zip_safety(zip_path, extract_dir)

    def test_forbidden_name_rejected(self, tmp_path: Path):
        zip_path = tmp_path / "bad.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("manifest.json", json.dumps({"package_version": "1", "database_name": "test", "kb_type": "milvus", "stats": {}}))
            zf.writestr(".env", "SECRET=xxx")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        with pytest.raises(validator.ValidationError, match="禁止的文件名"):
            validator.validate_zip_safety(zip_path, extract_dir)


class TestValidateManifest:
    def test_valid_manifest(self, tmp_path: Path):
        (tmp_path / "manifest.json").write_text(
            json.dumps({"package_version": "1", "database_name": "test", "kb_type": "milvus", "stats": {"files": 1, "chunks": 10}}),
            encoding="utf-8",
        )
        pkg = validator.validate_manifest_file(tmp_path)
        assert pkg.package_version == "1"

    def test_missing_manifest(self, tmp_path: Path):
        with pytest.raises(validator.ValidationError, match="manifest"):
            validator.validate_manifest_file(tmp_path)

    def test_bad_version_rejected(self, tmp_path: Path):
        (tmp_path / "manifest.json").write_text(
            json.dumps({"package_version": "2", "database_name": "test", "kb_type": "milvus", "stats": {}}),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="版本"):
            validator.validate_manifest_file(tmp_path)


class TestValidateChecksums:
    def test_matching_checksums(self, tmp_path: Path):
        # 写入测试文件
        (tmp_path / "chunks").mkdir()
        (tmp_path / "chunks" / "chunks.jsonl").write_text("hello", encoding="utf-8")
        (tmp_path / "checksums").mkdir()

        import hashlib
        hash_val = hashlib.sha256(b"hello").hexdigest()
        (tmp_path / "checksums" / "sha256.json").write_text(
            json.dumps({"chunks/chunks.jsonl": hash_val}), encoding="utf-8"
        )

        from yuxi.knowledge.migration import schemas as s
        pkg = s.PackageManifest(database_name="test", kb_type="milvus", stats={})
        validator.validate_checksums(tmp_path, pkg)  # 不抛异常

    def test_mismatch_rejected(self, tmp_path: Path):
        (tmp_path / "chunks").mkdir()
        (tmp_path / "chunks" / "chunks.jsonl").write_text("hello", encoding="utf-8")
        (tmp_path / "checksums").mkdir()

        (tmp_path / "checksums" / "sha256.json").write_text(
            json.dumps({"chunks/chunks.jsonl": "deadbeef" * 8}), encoding="utf-8"
        )

        from yuxi.knowledge.migration import schemas as s
        pkg = s.PackageManifest(database_name="test", kb_type="milvus", stats={})
        with pytest.raises(validator.ValidationError, match="校验和"):
            validator.validate_checksums(tmp_path, pkg)


class TestPreflightReport:
    def test_build_report(self, tmp_path: Path):
        (tmp_path / "manifest.json").write_text(
            json.dumps({"package_version": "1", "database_name": "test_kb", "kb_type": "milvus", "stats": {"files": 3, "chunks": 42}}),
            encoding="utf-8",
        )
        (tmp_path / "graph").mkdir(parents=True)
        (tmp_path / "graph" / "entities.jsonl").write_text(
            json.dumps({"entity_id": "e1", "name": "A", "label": "Entity", "attributes": [], "entity_type": ""}) + "\n",
            encoding="utf-8",
        )
        (tmp_path / "chunks").mkdir(parents=True)
        (tmp_path / "chunks" / "chunks.jsonl").write_text("{}", encoding="utf-8")

        from yuxi.knowledge.migration import schemas as s
        pkg = s.PackageManifest(database_name="test_kb", kb_type="milvus", stats={"files": 3, "chunks": 42})
        report = validator.build_preflight_report(tmp_path, pkg)

        assert report["database_name"] == "test_kb"
        assert report["entities"] == 1
        assert report["chunks"] == 42
        assert report["requires_embedding_model"] is True
