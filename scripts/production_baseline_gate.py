from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

BACKEND_PYTEST_TARGETS = [
    "test/unit/agents/skills/test_remote_install.py",
    "test/unit/routers/test_skill_router.py",
    "test/unit/services/test_skill_service.py",
    "test/unit/agents/skills/test_skill_zip_safety.py",
    "test/unit/utils/test_zip_safety.py",
    "test/unit/knowledge/test_ordinary_zip_safety.py",
    "test/unit/knowledge/migration/test_validator.py",
    "test/unit/services/test_task_service.py",
    "test/unit/routers/test_system_task_router.py",
    "test/unit/graphs/test_milvus_graph_build.py",
    "test/unit/plugins/test_milvus_kb.py",
    "test/unit/toolkits/test_kbs_tools.py",
    "test/unit/server/test_security_baseline.py",
]

BACKEND_RUFF_TARGETS = [
    "package/yuxi/agents/skills/remote_install.py",
    "package/yuxi/agents/skills/service.py",
    "package/yuxi/agents/toolkits/kbs/tools.py",
    "package/yuxi/config/app.py",
    "package/yuxi/knowledge/base.py",
    "package/yuxi/knowledge/graphs/milvus_graph_service.py",
    "package/yuxi/knowledge/implementations/milvus.py",
    "package/yuxi/knowledge/implementations/read_only_connectors.py",
    "package/yuxi/knowledge/manager.py",
    "package/yuxi/knowledge/migration/validator.py",
    "package/yuxi/knowledge/parser/zip_utils.py",
    "package/yuxi/knowledge/schemas.py",
    "package/yuxi/services/task_service.py",
    "package/yuxi/utils/zip_safety.py",
    "server/main.py",
    "server/routers/auth_router.py",
    "server/routers/knowledge_router.py",
    "server/routers/skill_router.py",
    "server/routers/system_task_router.py",
    "server/utils/access_log_middleware.py",
    "server/utils/cors.py",
    *BACKEND_PYTEST_TARGETS,
]

HOST_UNITTEST_TARGETS = [
    "packaging/windows/tests/test_security_policy.py",
    "packaging/windows/tests/test_production_baseline_gate.py",
]


def resolve_runner(runner: str) -> str:
    if runner != "auto":
        return runner
    return "direct" if os.getenv("CI") else "docker"


def build_backend_uv_command(runner: str, uv_args: list[str]) -> tuple[list[str], Path]:
    if runner == "docker":
        return ["docker", "compose", "run", "--rm", "--no-deps", "api", "uv", "run", *uv_args], ROOT
    if runner == "direct":
        return ["uv", "run", *uv_args], BACKEND
    raise ValueError(f"Unknown runner: {runner}")


def run_command(command: list[str], *, cwd: Path) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def run_backend_pytest(runner: str) -> None:
    command, cwd = build_backend_uv_command(runner, ["--group", "test", "pytest", *BACKEND_PYTEST_TARGETS])
    run_command(command, cwd=cwd)


def run_backend_ruff(runner: str) -> None:
    command, cwd = build_backend_uv_command(runner, ["--group", "dev", "ruff", "check", *BACKEND_RUFF_TARGETS])
    run_command(command, cwd=cwd)


def run_host_unittests() -> None:
    for target in HOST_UNITTEST_TARGETS:
        run_command([sys.executable, str(ROOT / target)], cwd=ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the first-batch productionization baseline test gate.")
    parser.add_argument(
        "--runner",
        choices=["auto", "docker", "direct"],
        default="auto",
        help="Use docker compose for local verification, or direct uv commands in CI.",
    )
    parser.add_argument("--skip-ruff", action="store_true", help="Skip backend ruff checks.")
    parser.add_argument("--skip-host-tests", action="store_true", help="Skip host-side unittest policy checks.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runner = resolve_runner(args.runner)
    run_backend_pytest(runner)
    if not args.skip_ruff:
        run_backend_ruff(runner)
    if not args.skip_host_tests:
        run_host_unittests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
