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


class ConfigManagerTests(unittest.TestCase):
    def test_initialize_env_preserves_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env.template").write_text("A=template\nB=two\n", encoding="utf-8")
            (root / ".env").write_text("A=custom\n", encoding="utf-8")

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
        self.assertEqual(run.call_args.args[0], ["docker", "compose", "up", "-d", "--build"])

    @patch("docker_manager.subprocess.run")
    def test_start_skips_build_for_bundled_images(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        manager = DockerManager(Path.cwd(), lambda _: None)
        manager.start(build=False)
        self.assertEqual(run.call_args.args[0], ["docker", "compose", "up", "-d", "--no-build"])


if __name__ == "__main__":
    unittest.main()
