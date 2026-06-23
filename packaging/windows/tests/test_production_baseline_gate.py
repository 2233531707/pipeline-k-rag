from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATE_PATH = ROOT / "scripts" / "production_baseline_gate.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("production_baseline_gate", GATE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load production baseline gate script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProductionBaselineGateTests(unittest.TestCase):
    def test_gate_includes_first_batch_test_targets(self) -> None:
        gate = load_gate()
        targets = set(gate.BACKEND_PYTEST_TARGETS)

        required = {
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
        }
        self.assertTrue(required.issubset(targets), required - targets)
        self.assertIn("packaging/windows/tests/test_security_policy.py", gate.HOST_UNITTEST_TARGETS)

    def test_gate_uses_docker_compose_for_local_backend_commands(self) -> None:
        gate = load_gate()

        command, cwd = gate.build_backend_uv_command("docker", ["--group", "test", "pytest"])

        self.assertEqual(command[:7], ["docker", "compose", "run", "--rm", "--no-deps", "api", "uv"])
        self.assertEqual(cwd, gate.ROOT)

    def test_gate_uses_direct_uv_for_ci_backend_commands(self) -> None:
        gate = load_gate()

        command, cwd = gate.build_backend_uv_command("direct", ["--group", "test", "pytest"])

        self.assertEqual(command, ["uv", "run", "--group", "test", "pytest"])
        self.assertEqual(cwd, gate.BACKEND)


if __name__ == "__main__":
    unittest.main()
