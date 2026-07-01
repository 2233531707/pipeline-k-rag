# Windows 桌面客户端交付

本目录用于 Windows 桌面前端客户端打包。首版实现采用 Electron，客户端只承载前端界面和后端地址配置，连接独立部署的后端服务器；不安装、不启动、不停止后端程序，也不管理数据库、对象存储、向量库、图数据库、Worker 或智能体沙盒。

## 目录

- `electron/`：首版 Electron 客户端工程、打包配置和主进程代码。
- `scripts/`：Electron 构建脚本。
- `dist/`：构建产物；不提交到 Git。

## 新交付边界

首版 Electron 客户端应满足：

- 客户端首次启动可配置后端服务器地址。
- 客户端可对后端 `/api/system/health` 做健康检查。
- 客户端通过 `kb-desktop://app` 自定义协议加载前端。
- 客户端通过桌面端安全存储保存认证 token。
- 客户端支持用户名密码登录、独立后端服务器首启初始化和主智能体对话 SSE 主链路。
- 客户端不管理本地 Compose 或服务端运行配置。
- 客户端包不包含 PostgreSQL、Redis、MinIO、Milvus、Neo4j、后端 Python 运行时或 Docker 镜像。
- 后端部署、升级、备份和日志查看全部走服务器部署链路。

## 构建入口

- Electron 工程：`packaging/windows/electron/`
- Windows `portable exe` 构建脚本：`packaging/windows/scripts/build_electron_portable.ps1`
