from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable

LogWriter = Callable[[str], None]


class DockerManager:
    def __init__(self, project_dir: Path, log: LogWriter = print) -> None:
        self.project_dir = project_dir.resolve()
        self.log = log

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
        if not shutil.which("docker"):
            return ["未找到 docker 命令，请安装并启动 Docker Desktop。"]
        if self._run(["docker", "info"], check=False).returncode:
            problems.append("Docker daemon 不可用，请启动 Docker Desktop。")
        if self._run(["docker", "compose", "version"], check=False).returncode:
            problems.append("Docker Compose v2 不可用。")
        if shutil.which("wsl.exe") and self._run(["wsl.exe", "--status"], check=False).returncode:
            problems.append("WSL2 状态检查失败；Docker Desktop Linux 容器可能无法运行。")
        if not (self.project_dir / "docker-compose.yml").exists():
            problems.append(f"缺少 docker-compose.yml: {self.project_dir}")
        return problems

    def load_images(self) -> bool:
        archive = self.project_dir.parent / "images" / "yuxi-images.tar"
        if not archive.exists():
            self.log("未发现离线镜像包，将使用本地镜像或由 Docker 拉取。")
            return False
        self._run(["docker", "load", "-i", str(archive)])
        return True

    def start(self, *, build: bool = True) -> None:
        args = ["docker", "compose", "up", "-d"]
        args.append("--build" if build else "--no-build")
        self._run(args)

    def stop(self) -> None:
        self._run(["docker", "compose", "stop"])

    def restart(self) -> None:
        self.stop()
        self.start()

    def logs(self, lines: int = 200) -> str:
        return self._run(["docker", "compose", "logs", "--tail", str(lines)], check=False).stdout

    def status(self) -> str:
        return self._run(["docker", "compose", "ps"], check=False).stdout
