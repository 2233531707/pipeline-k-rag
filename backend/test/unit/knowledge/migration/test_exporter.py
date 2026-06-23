"""测试 .yuxikb.zip 导出服务"""

from __future__ import annotations

from pathlib import Path

import pytest

from yuxi.knowledge.migration import checksums, exporter, manifest, schemas


class TestSanitiseFilename:
    def test_removes_path_separators(self):
        result = exporter._sanitise_filename("a/b/c.txt")
        assert "/" not in result
        assert "\\" not in result

    def test_removes_dotdot(self):
        result = exporter._sanitise_filename("../../etc/passwd")
        assert ".." not in result

    def test_keeps_normal_name(self):
        result = exporter._sanitise_filename("report.pdf")
        assert result == "report.pdf"


class TestManifest:
    def test_build_manifest(self):
        m = manifest.build_manifest(
            database_name="测试库",
            kb_type="milvus",
            group_name="项目资料",
            file_count=5,
            chunk_count=100,
            entity_count=50,
            relationship_count=80,
        )
        assert m.package_version == "1"
        assert m.group_name == "项目资料"
        assert m.stats["files"] == 5
        assert m.stats["chunks"] == 100

    def test_validate_manifest_ok(self):
        m = manifest.build_manifest("test", "milvus", file_count=1, chunk_count=1)
        manifest.validate_manifest(m)  # 不应抛异常

    def test_validate_manifest_bad_version(self):
        m = manifest.build_manifest("test", "milvus")
        m.package_version = "2"
        with pytest.raises(ValueError, match="版本"):
            manifest.validate_manifest(m)


class TestChecksums:
    def test_compute_and_build(self, tmp_path: Path):
        (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
        (tmp_path / "b.txt").write_text("world", encoding="utf-8")

        result = checksums.build_checksums(tmp_path, ["a.txt", "b.txt"])
        assert "a.txt" in result
        assert "b.txt" in result
        assert len(result["a.txt"]) == 64  # SHA-256 hex

    def test_missing_file_skipped(self, tmp_path: Path):
        (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
        result = checksums.build_checksums(tmp_path, ["a.txt", "nope.txt"])
        assert "a.txt" in result
        assert "nope.txt" not in result


class TestSchemas:
    def test_chunk_record_excludes_vectors(self):
        """确保 ChunkRecord 不包含 embedding 字段"""
        fields = schemas.ChunkRecord.model_fields
        assert "embedding" not in fields
        assert "vector" not in fields

    def test_database_meta_excludes_sensitive(self):
        """DatabaseMeta 不应包含 kb_id、用户信息等敏感字段"""
        fields = schemas.DatabaseMeta.model_fields
        assert "kb_id" not in fields
        assert "created_by" not in fields
        assert "embedding_model_spec" not in fields
        assert "llm_model_spec" not in fields

    def test_forbidden_extensions(self):
        assert ".py" in schemas.FORBIDDEN_EXTENSIONS
        assert ".exe" in schemas.FORBIDDEN_EXTENSIONS
        assert ".sh" in schemas.FORBIDDEN_EXTENSIONS
