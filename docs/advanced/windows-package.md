# Windows 启动器与安装包

Windows 交付源码位于 `packaging/windows`。启动器负责检查 Docker Desktop、WSL2、Docker daemon 与 Compose，初始化 `.env`，并提供启动、停止、重启、日志、打开 Web 和健康检查操作。

## 构建

在 Windows PowerShell 中执行：

```powershell
cd packaging/windows
.\scripts\build_launcher.ps1
.\scripts\build_installer.ps1
.\scripts\test_installer.ps1
```

`build_launcher.ps1` 使用 PyInstaller 生成启动器；`build_installer.ps1` 调用 Inno Setup 生成 `dist\Yuxi-Desktop-Setup.exe`。构建机需要 Python 3.12+、Docker Desktop 和 Inno Setup 6。

## 数据保护

安装包不会删除或覆盖已有 Docker volume。卸载默认只移除启动器和随附配置，不执行 `docker compose down -v`。重新安装时若目标目录已有 `.env`，启动器保留原文件，仅补充模板中缺失的键。

## 离线镜像

`scripts/export_images.ps1` 可按 bundle 中的 Compose 配置导出镜像。大体积镜像归档不提交到 Git；发布时与安装包一同分发或由安装器按需下载。
