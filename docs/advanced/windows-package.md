# Windows 启动器与安装包

Windows 交付源码位于 `packaging/windows`。启动器负责检查 Docker Desktop、WSL2、Docker daemon 与 Compose，初始化 `.env.desktop`，为桌面本地服务生成随机密钥，并提供启动、停止、重启、日志、打开 Web 和健康检查操作。

## 构建

在 Windows PowerShell 中执行：

```powershell
cd packaging/windows
.\scripts\build_launcher.ps1
.\scripts\build_installer.ps1
.\scripts\test_installer.ps1
```

`build_launcher.ps1` 使用 PyInstaller 生成启动器；`build_installer.ps1` 调用 NSIS `makensis` 生成 `dist\地下管网知识模型数据库.exe`。构建机需要 Python 3.12+、Docker Desktop 和 NSIS 3。若启动器 EXE 已存在，只重建安装器时不需要重新安装 Python。

安装包使用运行时白名单，只包含后端、Docker、Web 源码及必要根配置，不包含 `.git`、`.env*`、迁移包、数据库文件、Docker 数据卷、日志或缓存。安装路径默认为：

```text
%LOCALAPPDATA%\地下管网知识模型数据库
```

该路径对当前用户可写，启动器可以正常初始化 `.env.desktop`、生成本地随机密钥并保存运行数据。桌面 Compose 默认只暴露 Web 入口，数据库、Redis、MinIO、Milvus 与 Neo4j 不暴露到宿主机；沙盒容器默认进入 internal sandbox network，Docker socket 仅由 sandbox-provisioner 持有。安装包内同时提供“使用教程”开始菜单入口。

## 数据保护

安装包不会执行 `docker compose down -v`。重新安装时若目标目录已有 `.env.desktop`，启动器保留原文件，仅补充模板中缺失的必填键。卸载前应先在启动器中停止服务；如需长期保留数据，请备份安装目录下的 `app\docker\volumes`，并保留 Docker 的 `postgres_data` 命名卷。

## 离线镜像

`scripts/export_images.ps1` 可按 bundle 中的 Compose 配置导出镜像。大体积镜像归档不提交到 Git；发布时与安装包一同分发或由安装器按需下载。
