from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from yuxi.agents.base import BaseAgent


class _DummyAgent(BaseAgent):
    @property
    def module_name(self) -> str:
        return "dummy-agent"

    async def get_graph(self, **kwargs):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_get_async_conn_quarantines_malformed_checkpoint(tmp_path: Path) -> None:
    agent = _DummyAgent()
    agent.workdir = tmp_path

    checkpoint = tmp_path / "aio_history.db"
    checkpoint.write_bytes(b"not-a-sqlite-database")
    (tmp_path / "aio_history.db-wal").write_bytes(b"stale-wal")
    (tmp_path / "aio_history.db-shm").write_bytes(b"stale-shm")

    conn = await agent.get_async_conn()
    try:
        result = await conn.execute_fetchall("PRAGMA integrity_check;")
        assert result == [("ok",)]
    finally:
        await conn.close()

    quarantined = sorted(tmp_path.glob("aio_history.db.corrupt-*"))
    assert len(quarantined) == 1
    assert quarantined[0].read_bytes() == b"not-a-sqlite-database"
    assert list(tmp_path.glob("aio_history.db-wal.corrupt-*"))
    assert list(tmp_path.glob("aio_history.db-shm.corrupt-*"))

    sqlite3.connect(checkpoint).close()
    assert checkpoint.exists()
