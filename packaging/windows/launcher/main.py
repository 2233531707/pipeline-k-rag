from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from config_manager import initialize_env
from docker_manager import DockerManager
from healthcheck import check_url, wait_for_health

WEB_URL = "http://localhost:5173"
API_HEALTH_URL = "http://localhost:5050/api/system/health"


def default_project_dir() -> Path:
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    bundled = base / "app"
    return bundled if bundled.exists() else base


class LauncherApp:
    def __init__(self, root: tk.Tk, project_dir: Path) -> None:
        self.root = root
        self.root.title("地下管网知识模型数据库 Docker 启动器")
        self.root.geometry("860x560")
        self.project_dir = project_dir
        self.manager = DockerManager(project_dir, self.write_log)
        self.status_text = tk.StringVar(value="尚未检查")
        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="地下管网知识模型数据库", font=("Microsoft YaHei UI", 18, "bold")).pack(anchor=tk.W)
        ttk.Label(frame, text=f"项目目录：{self.project_dir}").pack(anchor=tk.W, pady=(2, 10))
        ttk.Label(frame, textvariable=self.status_text).pack(anchor=tk.W, pady=(0, 10))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(0, 10))
        actions = [
            ("环境检查", self.check_environment),
            ("初始化配置", self.initialize_config),
            ("启动", self.start_services),
            ("停止", self.stop_services),
            ("重启", self.restart_services),
            ("服务状态", self.show_status),
            ("查看日志", self.show_logs),
            ("打开 Web", lambda: webbrowser.open(WEB_URL)),
        ]
        for index, (label, command) in enumerate(actions):
            ttk.Button(buttons, text=label, command=command).grid(
                row=index // 4, column=index % 4, padx=4, pady=4, sticky=tk.EW
            )
        for column in range(4):
            buttons.columnconfigure(column, weight=1)

        self.log_box = scrolledtext.ScrolledText(frame, height=22, wrap=tk.WORD)
        self.log_box.pack(fill=tk.BOTH, expand=True)

    def write_log(self, message: str) -> None:
        def append() -> None:
            self.log_box.insert(tk.END, message + "\n")
            self.log_box.see(tk.END)

        self.root.after(0, append)

    def run_async(self, label: str, action) -> None:
        self.status_text.set(f"{label}中...")

        def worker() -> None:
            try:
                action()
                self.root.after(0, self.status_text.set, f"{label}完成")
            except Exception as exc:
                self.write_log(f"错误：{exc}")
                self.root.after(0, self.status_text.set, f"{label}失败")
                self.root.after(0, messagebox.showerror, "地下管网知识模型数据库", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def check_environment(self) -> None:
        def action() -> None:
            problems = self.manager.prerequisites()
            if problems:
                raise RuntimeError("\n".join(problems))
            self.write_log("Docker Desktop、daemon 与 Compose 检查通过。")

        self.run_async("环境检查", action)

    def initialize_config(self) -> None:
        def action() -> None:
            path, added = initialize_env(self.project_dir)
            self.write_log(f"配置文件：{path}，新增 {added} 个配置项。")

        self.run_async("配置初始化", action)

    def start_services(self) -> None:
        def action() -> None:
            problems = self.manager.prerequisites()
            if problems:
                raise RuntimeError("\n".join(problems))
            initialize_env(self.project_dir)
            images_loaded = self.manager.load_images()
            self.manager.start(build=not images_loaded)
            api = wait_for_health(API_HEALTH_URL)
            web = check_url(WEB_URL, timeout=8)
            if not api.ok or not web.ok:
                raise RuntimeError(f"健康检查失败：API={api.detail}; Web={web.detail}")
            self.write_log("API 与 Web 健康检查通过。")

        self.run_async("服务启动", action)

    def stop_services(self) -> None:
        self.run_async("服务停止", self.manager.stop)

    def restart_services(self) -> None:
        self.run_async("服务重启", self.manager.restart)

    def show_status(self) -> None:
        self.run_async("状态查询", lambda: self.write_log(self.manager.status()))

    def show_logs(self) -> None:
        self.run_async("日志读取", lambda: self.write_log(self.manager.logs()))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="地下管网知识模型数据库 Docker 启动器")
    parser.add_argument("--project-dir", type=Path, default=default_project_dir())
    parser.add_argument("--check", action="store_true", help="仅执行环境检查")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manager = DockerManager(args.project_dir)
    if args.check:
        problems = manager.prerequisites()
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        print("environment ok")
        return 0

    root = tk.Tk()
    LauncherApp(root, args.project_dir)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
