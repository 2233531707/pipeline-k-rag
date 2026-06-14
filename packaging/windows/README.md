# Windows 交付

本目录生成 Docker Compose 驱动的 Windows 桌面启动器和 Inno Setup 安装包。

## 目录

- `launcher/`：Tkinter 启动器、Docker 控制、配置初始化和健康检查。
- `bundle/`：Compose/.env 快照、构建时生成的完整应用目录和可选离线镜像。
- `installer/yuxi.iss`：Inno Setup 定义。
- `scripts/`：启动器、镜像、安装包构建与安装验证。
- `tests/`：不依赖 Docker 的启动器单元测试。

## 构建顺序

```powershell
.\scripts\build_launcher.ps1
# 可选：生成离线镜像包
.\scripts\export_images.ps1
.\scripts\build_installer.ps1
.\scripts\test_installer.ps1
```

最终产物为 `dist\Yuxi-Desktop-Setup.exe`。安装程序不会执行 `docker compose down -v`，也不会删除 Docker volume；现有 `.env` 会保留，启动器只补充模板缺失项。
