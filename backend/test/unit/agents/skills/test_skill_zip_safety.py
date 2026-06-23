from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

import pytest

from yuxi.agents.skills import service as svc
from yuxi.storage.postgres.models_business import Skill, User


def _build_zip(files: dict[str, bytes | str], *, compression: int = zipfile.ZIP_DEFLATED) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=compression) as zf:
        for path, content in files.items():
            data = content.encode("utf-8") if isinstance(content, str) else content
            zf.writestr(path, data)
    return buf.getvalue()


def _skill_md(slug: str = "demo") -> str:
    return f"---\nname: {slug}\ndescription: demo skill\n---\n# Demo\n"


def _user(uid: str = "normal-user", role: str = "user") -> User:
    return User(username=uid, uid=uid, password_hash="x", role=role, department_id=1)


class FakeRepo:
    created_item: Skill | None = None

    def __init__(self, _db):
        pass

    async def exists_slug(self, _slug: str) -> bool:
        return False

    async def create(self, **kwargs) -> Skill:
        item = Skill(**kwargs, updated_by=kwargs["created_by"])
        self.__class__.created_item = item
        return item


@pytest.mark.asyncio
async def test_regular_user_zip_upload_defaults_private_and_logs_script_risk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(svc.sys_config, "save_dir", str(tmp_path))
    monkeypatch.setattr(svc, "SkillRepository", FakeRepo)
    logs: list[dict] = []

    async def fake_log_operation(_db, user_id, operation, details=None, request=None):
        logs.append({"user_id": user_id, "operation": operation, "details": json.loads(details or "{}")})

    monkeypatch.setattr(svc, "log_operation", fake_log_operation)
    operator = _user()
    zip_bytes = _build_zip(
        {
            "demo/SKILL.md": _skill_md("demo"),
            "demo/scripts/run.py": "print('allowed script')\n",
        }
    )

    draft = await svc.prepare_skill_upload(None, filename="demo.zip", file_bytes=zip_bytes, operator=operator)
    results = await svc.confirm_skill_install_draft(
        None,
        draft_id=draft["draft_id"],
        share_config=draft["default_share_config"],
        operator=operator,
    )

    assert draft["default_share_config"] == {
        "access_level": "user",
        "department_ids": [],
        "user_uids": ["normal-user"],
    }
    warnings = draft["items"][0]["warnings"]
    assert any("脚本" in warning for warning in warnings)
    assert results[0]["success"] is True
    assert FakeRepo.created_item is not None
    assert svc.user_can_access_skill(operator, FakeRepo.created_item) is True

    upload_logs = [entry for entry in logs if entry["operation"] == "skill_upload_prepare"]
    assert upload_logs
    details = upload_logs[-1]["details"]
    assert details["operator_uid"] == "normal-user"
    assert details["filename"] == "demo.zip"
    assert details["file_size_bytes"] == len(zip_bytes)
    assert details["content_hash"] == hashlib.sha256(zip_bytes).hexdigest()
    assert details["slugs"] == ["demo"]
    assert details["visibility"] == draft["default_share_config"]
    assert details["scan_result"]["warnings"] == warnings
    assert details["result"] == {"status": "success"}


@pytest.mark.asyncio
async def test_skill_zip_scan_failure_cleans_draft_and_logs_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(svc.sys_config, "save_dir", str(tmp_path))
    monkeypatch.setattr(svc, "SkillRepository", FakeRepo)
    logs: list[dict] = []

    async def fake_log_operation(_db, user_id, operation, details=None, request=None):
        logs.append({"operation": operation, "details": json.loads(details or "{}")})

    monkeypatch.setattr(svc, "log_operation", fake_log_operation)
    zip_bytes = _build_zip({"demo/SKILL.md": _skill_md("demo"), "demo/.env": "SECRET=1\n"})

    with pytest.raises(ValueError, match="隐藏敏感文件"):
        await svc.prepare_skill_upload(None, filename="demo.zip", file_bytes=zip_bytes, operator=_user())

    drafts_root = tmp_path / "skill_import_drafts"
    assert not drafts_root.exists() or list(drafts_root.iterdir()) == []
    assert not (tmp_path / "skills" / "demo").exists()
    upload_logs = [entry for entry in logs if entry["operation"] == "skill_upload_prepare"]
    assert upload_logs
    assert upload_logs[-1]["details"]["operator_uid"] == "normal-user"
    assert upload_logs[-1]["details"]["result"]["status"] == "failed"
    assert "隐藏敏感文件" in upload_logs[-1]["details"]["result"]["reason"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("files", "match"),
    [
        ({"../evil/SKILL.md": _skill_md("demo")}, "路径穿越"),
        ({"/abs/SKILL.md": _skill_md("demo")}, "绝对路径"),
        ({"demo/SKILL.md": _skill_md("demo"), "demo/tool.exe": b"MZ"}, "可执行二进制"),
        ({"demo/SKILL.md": _skill_md("demo"), "demo/blob.dat": os.urandom(256 * 1024 + 1)}, "未知大二进制"),
    ],
)
async def test_skill_zip_scan_rejects_unsafe_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, files: dict[str, bytes | str], match: str
):
    monkeypatch.setattr(svc.sys_config, "save_dir", str(tmp_path))
    monkeypatch.setattr(svc, "SkillRepository", FakeRepo)

    with pytest.raises(ValueError, match=match):
        await svc.prepare_skill_upload(None, filename="demo.zip", file_bytes=_build_zip(files), operator=_user())


@pytest.mark.asyncio
async def test_skill_zip_scan_rejects_excessive_file_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(svc.sys_config, "save_dir", str(tmp_path))
    monkeypatch.setattr(svc, "SkillRepository", FakeRepo)
    max_count = getattr(svc, "SKILL_ZIP_MAX_FILE_COUNT", 200)
    files = {"demo/SKILL.md": _skill_md("demo")}
    files.update({f"demo/prompts/{i}.md": "x" for i in range(max_count)})

    with pytest.raises(ValueError, match="文件数量超限"):
        await svc.prepare_skill_upload(None, filename="demo.zip", file_bytes=_build_zip(files), operator=_user())


@pytest.mark.asyncio
async def test_skill_zip_scan_rejects_size_and_compression_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(svc.sys_config, "save_dir", str(tmp_path))
    monkeypatch.setattr(svc, "SkillRepository", FakeRepo)
    single_file_limit = getattr(svc, "SKILL_ZIP_MAX_SINGLE_FILE_BYTES", 5 * 1024 * 1024)
    zip_bytes = _build_zip(
        {
            "demo/SKILL.md": _skill_md("demo"),
            "demo/prompts/huge.md": "x" * (single_file_limit + 1),
        }
    )

    with pytest.raises(ValueError, match="单文件过大"):
        await svc.prepare_skill_upload(None, filename="demo.zip", file_bytes=zip_bytes, operator=_user())

    bomb_bytes = _build_zip(
        {
            "demo/SKILL.md": _skill_md("demo"),
            "demo/prompts/bomb.md": "0" * (1024 * 1024),
        }
    )
    with pytest.raises(ValueError, match="压缩比过高"):
        await svc.prepare_skill_upload(None, filename="demo.zip", file_bytes=bomb_bytes, operator=_user())
