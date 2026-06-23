from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

LAUNCHER_DIR = Path(__file__).resolve().parents[1] / "launcher"
sys.path.insert(0, str(LAUNCHER_DIR))

from config_manager import initialize_env

ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILES = ("docker-compose.desktop.yml", "docker-compose.prod.yml")
REQUIRED_DESKTOP_KEYS = {
    "YUXI_ENV",
    "JWT_SECRET_KEY",
    "YUXI_INSTANCE_ID",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "NEO4J_USERNAME",
    "NEO4J_PASSWORD",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
}
WEAK_SECRET_SNIPPETS = (
    "POSTGRES_PASSWORD:-postgres",
    "NEO4J_PASSWORD:-0123456789",
    "MINIO_ACCESS_KEY:-minioadmin",
    "MINIO_SECRET_KEY:-minioadmin",
)
STATE_SERVICES = ("postgres", "redis", "minio", "milvus", "graph", "etcd")
NON_PROVISIONER_SERVICES = ("api", "worker", "web", *STATE_SERVICES)


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def service_block(compose_text: str, service_name: str) -> str:
    marker = f"\n  {service_name}:\n"
    start = compose_text.find(marker)
    if start == -1:
        marker = f"services:\n  {service_name}:\n"
        start = compose_text.find(marker)
    if start == -1:
        raise AssertionError(f"Service missing from compose: {service_name}")
    next_service = compose_text.find("\n  ", start + len(marker))
    while next_service != -1 and compose_text[next_service + 3 : next_service + 4] == " ":
        next_service = compose_text.find("\n  ", next_service + 1)
    return compose_text[start:] if next_service == -1 else compose_text[start:next_service]


class DesktopEnvSecurityTests(unittest.TestCase):
    def test_initialize_env_generates_random_desktop_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env.template").write_text(
                "YUXI_ENV=development\n"
                "JWT_SECRET_KEY=\n"
                "YUXI_INSTANCE_ID=\n"
                "POSTGRES_USER=\n"
                "POSTGRES_PASSWORD=\n"
                "POSTGRES_DB=\n"
                "NEO4J_USERNAME=\n"
                "NEO4J_PASSWORD=\n"
                "MINIO_ACCESS_KEY=\n"
                "MINIO_SECRET_KEY=\n",
                encoding="utf-8",
            )

            path, added = initialize_env(root)
            values = parse_env(path.read_text(encoding="utf-8"))

            self.assertEqual(added, len(REQUIRED_DESKTOP_KEYS))
            self.assertEqual(values["YUXI_ENV"], "production")
            for key in REQUIRED_DESKTOP_KEYS - {"YUXI_ENV"}:
                self.assertTrue(values[key], key)
            self.assertEqual(len(values["JWT_SECRET_KEY"]), 64)
            self.assertTrue(values["YUXI_INSTANCE_ID"].startswith("instance-"))
            self.assertNotEqual(values["POSTGRES_PASSWORD"], "postgres")
            self.assertNotEqual(values["NEO4J_PASSWORD"], "0123456789")
            self.assertNotEqual(values["MINIO_ACCESS_KEY"], "minioadmin")
            self.assertNotEqual(values["MINIO_SECRET_KEY"], "minioadmin")

    def test_initialize_env_preserves_existing_desktop_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env.template").write_text("POSTGRES_PASSWORD=\nJWT_SECRET_KEY=\n", encoding="utf-8")
            (root / ".env.desktop").write_text("POSTGRES_PASSWORD=custom-secret\n", encoding="utf-8")

            path, added = initialize_env(root)
            values = parse_env(path.read_text(encoding="utf-8"))

            self.assertEqual(added, len(REQUIRED_DESKTOP_KEYS) - 1)
            self.assertEqual(values["POSTGRES_PASSWORD"], "custom-secret")
            self.assertEqual(len(values["JWT_SECRET_KEY"]), 64)


class ComposeSecurityPolicyTests(unittest.TestCase):
    def test_desktop_and_production_compose_require_secrets(self) -> None:
        for filename in COMPOSE_FILES:
            text = (ROOT / filename).read_text(encoding="utf-8")
            for snippet in WEAK_SECRET_SNIPPETS:
                self.assertNotIn(snippet, text, filename)
            for key in ("POSTGRES_PASSWORD", "NEO4J_PASSWORD", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"):
                self.assertIn(f"${{{key}:", text, filename)
                self.assertIn(" is required", text, filename)

    def test_desktop_and_production_do_not_expose_state_service_ports(self) -> None:
        for filename in COMPOSE_FILES:
            text = (ROOT / filename).read_text(encoding="utf-8")
            for service in STATE_SERVICES:
                self.assertNotIn("\n    ports:\n", service_block(text, service), f"{filename}:{service}")

    def test_only_sandbox_provisioner_mounts_docker_socket(self) -> None:
        for filename in COMPOSE_FILES:
            text = (ROOT / filename).read_text(encoding="utf-8")
            self.assertIn("/var/run/docker.sock:/var/run/docker.sock", service_block(text, "sandbox-provisioner"))
            for service in NON_PROVISIONER_SERVICES:
                self.assertNotIn("/var/run/docker.sock", service_block(text, service), f"{filename}:{service}")

    def test_api_worker_are_pinned_to_sandbox_provisioner(self) -> None:
        for filename in COMPOSE_FILES:
            text = (ROOT / filename).read_text(encoding="utf-8")
            anchor = text.split("services:", 1)[0]
            self.assertIn("SANDBOX_PROVIDER: provisioner", anchor, filename)
            self.assertNotIn("SANDBOX_PROVIDER:-", anchor, filename)

    def test_desktop_sandbox_network_is_internal_by_default(self) -> None:
        text = (ROOT / "docker-compose.desktop.yml").read_text(encoding="utf-8")
        provisioner = service_block(text, "sandbox-provisioner")
        self.assertIn("- sandbox-network", provisioner)
        self.assertIn("DOCKER_NETWORK=${SANDBOX_DOCKER_NETWORK:-yuxi-know_sandbox-network}", provisioner)
        self.assertIn("  sandbox-network:\n", text)
        sandbox_network = text.split("  sandbox-network:\n", 1)[1]
        self.assertIn("internal: true", sandbox_network)


    def test_frontend_api_error_logging_does_not_emit_sensitive_request_data(self) -> None:
        text = (ROOT / "web/src/apis/base.js").read_text(encoding="utf-8")
        self.assertNotIn("requestHeaders", text)
        self.assertNotIn("requestBody", text)
        self.assertNotIn("Object.fromEntries(response.headers.entries())", text)

    def test_dockerignore_excludes_sensitive_and_runtime_artifacts(self) -> None:
        lines = {
            line.strip()
            for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        required = {
            ".env*",
            "docker/volumes/",
            "saves/",
            "uploads/",
            "outputs/",
            "*.db",
            "*.sqlite",
            "*.sqlite3",
            "*.log",
            "*.yuxikb.zip",
            "packaging/windows/dist/",
            "packaging/windows/bundle/",
        }
        self.assertTrue(required.issubset(lines), required - lines)


if __name__ == "__main__":
    unittest.main()
