from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

LAUNCHER_DIR = Path(__file__).resolve().parents[1] / "launcher"
sys.path.insert(0, str(LAUNCHER_DIR))

from config_manager import initialize_env
from docker_manager import DockerManager
import main as launcher_main


class ConfigManagerTests(unittest.TestCase):
    def test_initialize_env_preserves_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env.template").write_text("A=template\nB=two\n", encoding="utf-8")
            (root / ".env.desktop").write_text("A=custom\n", encoding="utf-8")

            path, added = initialize_env(root)

            self.assertEqual(added, 1)
            self.assertIn("A=custom", path.read_text(encoding="utf-8"))
            self.assertIn("B=two", path.read_text(encoding="utf-8"))

    def test_initialize_env_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env.template").write_text("A=one\n", encoding="utf-8")
            path, added = initialize_env(root)
            self.assertEqual(path.read_text(encoding="utf-8"), "A=one\n")
            self.assertEqual(added, 1)


class DockerManagerTests(unittest.TestCase):
    @patch("docker_manager.subprocess.run")
    def test_start_builds_when_images_are_not_bundled(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        manager = DockerManager(Path.cwd(), lambda _: None)
        manager.start()
        self.assertEqual(run.call_args.args[0], ["docker", "compose", "--env-file", ".env.desktop", "-f", "docker-compose.desktop.yml", "up", "-d", "--build"])

    @patch("docker_manager.subprocess.run")
    def test_start_skips_build_for_bundled_images(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        manager = DockerManager(Path.cwd(), lambda _: None)
        manager.start(build=False)
        self.assertEqual(run.call_args.args[0], ["docker", "compose", "--env-file", ".env.desktop", "-f", "docker-compose.desktop.yml", "up", "-d", "--no-build"])

    @patch("docker_manager.shutil.which")
    def test_falls_back_to_windows_docker_executable(self, which) -> None:
        which.side_effect = [None, r"C:\Program Files\Docker\Docker\resources\bin\docker.exe"]

        manager = DockerManager(Path.cwd(), lambda _: None)

        self.assertEqual(manager.docker_executable, "docker.exe")


class DesktopPackagingTests(unittest.TestCase):
    def test_desktop_compose_uses_production_web_stack(self) -> None:
        root = Path(__file__).resolve().parents[3]
        text = (root / "docker-compose.desktop.yml").read_text(encoding="utf-8")
        self.assertIn("target: production", text)
        self.assertNotIn("web-dev", text)
        self.assertNotIn("5173:5173", text)
        self.assertIn(".env.desktop", text)

    def test_launcher_uses_desktop_web_entrypoint(self) -> None:
        self.assertEqual(launcher_main.WEB_URL, "http://localhost")
        self.assertEqual(launcher_main.API_HEALTH_URL, "http://localhost/api/system/health")

    def test_installer_packages_desktop_compose(self) -> None:
        script = (Path(__file__).resolve().parents[1] / "scripts" / "build_installer.ps1").read_text(encoding="utf-8")
        runtime_files_line = next(line for line in script.splitlines() if line.startswith(chr(36) + "RuntimeFiles ="))
        self.assertIn("docker-compose.desktop.yml", runtime_files_line)
        self.assertNotIn("docker-compose.yml", runtime_files_line)

    def test_image_export_uses_desktop_compose(self) -> None:
        script = (Path(__file__).resolve().parents[1] / "scripts" / "export_images.ps1").read_text(encoding="utf-8")
        self.assertIn("docker compose --env-file .env.desktop -f docker-compose.desktop.yml config --images", script)


if __name__ == "__main__":
    unittest.main()
