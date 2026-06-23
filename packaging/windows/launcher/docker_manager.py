from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable

LogWriter = Callable[[str], None]
DESKTOP_COMPOSE_FILE = "docker-compose.desktop.yml"
DESKTOP_ENV_FILE = ".env.desktop"


class DockerManager:
    def __init__(self, project_dir: Path, log: LogWriter = print) -> None:
        self.project_dir = project_dir.resolve()
        self.log = log
        self.docker_executable = self._find_docker_executable()

    @staticmethod
    def _find_docker_executable() -> str | None:
        if shutil.which("docker"):
            return "docker"
        if shutil.which("docker.exe"):
            return "docker.exe"
        if os.name == "nt":
            program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            candidate = program_files / "Docker" / "Docker" / "resources" / "bin" / "docker.exe"
            if candidate.is_file():
                return str(candidate)
        return None

    def _docker_args(self, *args: str) -> list[str]:
        if not self.docker_executable:
            raise RuntimeError("未找到 docker 命令，请安装并启动 Docker Desktop。")
        return [self.docker_executable, *args]

    def _compose_args(self, *args: str) -> list[str]:
        return self._docker_args("compose", "--env-file", DESKTOP_ENV_FILE, "-f", DESKTOP_COMPOSE_FILE, *args)

    def _run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        command = " ".join(args)
        self.log(f"> {command}")
        result = subprocess.run(
            args,
            cwd=self.project_dir,
            check=False,
            text=True,
            encoding=(
                "utf-16-le"
                if os.name == "nt" and Path(args[0]).name.lower() == "wsl.exe"
                else "mbcs" if os.name == "nt" else "utf-8"
            ),
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.stdout:
            self.log(result.stdout.rstrip())
        if check and result.returncode:
            raise RuntimeError(f"命令执行失败 ({result.returncode}): {command}")
        return result

    def prerequisites(self) -> list[str]:
        problems: list[str] = []
        if not self.docker_executable:
            return ["未找到 docker 命令，请安装并启动 Docker Desktop。"]
        if self._run(self._docker_args("info"), check=False).returncode:
            problems.append("Docker daemon 不可用，请启动 Docker Desktop。")
        if self._run(self._docker_args("compose", "version"), check=False).returncode:
            problems.append("Docker Compose v2 不可用。")
        if shutil.which("wsl.exe") and self._run(["wsl.exe", "--status"], check=False).returncode:
            problems.append("WSL2 状态检查失败；Docker Desktop Linux 容器可能无法运行。")
        if not (self.project_dir / DESKTOP_COMPOSE_FILE).exists():
            problems.append(f"缺少 {DESKTOP_COMPOSE_FILE}: {self.project_dir}")
        return problems

    def load_images(self) -> bool:
        archive = self.project_dir.parent / "images" / "yuxi-images.tar"
        if not archive.exists():
            self.log("未发现离线镜像包，将使用本地镜像或由 Docker 拉取。")
            return False
        self._run(self._docker_args("load", "-i", str(archive)))
        return True

    def start(self, *, build: bool = True) -> None:
        args = self._compose_args("up", "-d")
        args.append("--build" if build else "--no-build")
        self._run(args)

    def stop(self) -> None:
        self._run(self._compose_args("stop"))

    def restart(self) -> None:
        self.stop()
        self.start()

    def logs(self, lines: int = 200) -> str:
        return self._run(self._compose_args("logs", "--tail", str(lines)), check=False).stdout

    def status(self) -> str:
        return self._run(self._compose_args("ps"), check=False).stdout
