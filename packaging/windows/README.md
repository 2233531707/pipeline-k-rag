# Windows 交付

本目录生成 Docker Compose 驱动的 Windows 桌面启动器和 Inno Setup 安装包。

## 目录

- `launcher/`：Tkinter 启动器、Docker 控制、配置初始化、随机本地密钥生成和健康检查。
- `bundle/`：Compose/.env.template 快照、构建时生成的完整应用目录和可选离线镜像。
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

最终产物为 `dist\地下管网知识模型数据库.exe`。安装程序默认安装到当前用户的 `%LOCALAPPDATA%\地下管网知识模型数据库`，无需管理员权限。安装程序不会执行 `docker compose down -v`，也不会删除 Docker volume；现有 `.env.desktop` 会保留，启动器只补充模板缺失的必填项；桌面 Compose 默认只暴露 Web 入口，状态服务不暴露到宿主机；沙盒容器默认进入 internal sandbox network，Docker socket 仅由 sandbox-provisioner 持有。

安装包只收集运行所需的 `backend`、`docker`、`web` 和根配置文件，并明确排除 `.git`、`.env*`、本地知识库迁移包、数据库文件、Docker 数据卷、日志、缓存和构建产物。面向普通用户的说明见 `地下管网知识模型数据库-使用教程.txt`。
