# Windows 桌面前端客户端

Windows 首版交付目标是生成 Electron 桌面前端客户端。客户端只承载地下管网知识模型数据库的前端界面和后端地址配置，不安装、不启动、不停止后端程序，也不管理 PostgreSQL/PostGIS、Redis、MinIO、Milvus、Neo4j、Worker 或智能体沙盒。

## 交付边界

- 客户端连接独立后端服务器，例如 `https://yuxi.example.com`。
- 客户端不得携带数据库、对象存储、向量库、图数据库或后端运行时。
- 客户端不管理任何本地 Compose 或服务端运行配置。
- 后端部署、升级、备份、日志、监控和沙盒运行由服务器部署链路负责。
- 开发栈和 isolated 验收栈继续使用 Docker Compose，不作为桌面客户端运行方式。

## 客户端职责

桌面客户端应只覆盖以下能力：

1. 首次启动配置后端服务器地址。
2. 对配置地址执行健康检查。
3. 加载前端应用并通过后端 API 完成用户名密码登录、独立后端服务器首启初始化和主智能体对话。
4. 保存客户端侧非敏感偏好，例如最近使用的后端地址。
5. 通过桌面端安全存储保存认证 token。
6. 为第三方系统提供可启动的 `portable exe` 入口。

## 首版构建入口

首版 Electron 客户端工程位于 `packaging/windows/electron/`，Windows `portable exe` 构建脚本位于 `packaging/windows/scripts/build_electron_portable.ps1`。

构建前提：

- 已完成 `web/` 前端依赖安装与可构建状态；
- Windows 构建机具备 Node.js、pnpm 和 Electron Builder 运行环境；
- 独立后端服务器地址可在运行时配置，或通过 `YUXI_DESKTOP_DEFAULT_BACKEND_URL` 预置默认值。

## 服务端要求

独立后端服务器需要按生产部署文档准备，并显式允许桌面客户端来源：

- Web/API 推荐使用 HTTPS。
- 桌面首版使用 `kb-desktop://app` 自定义协议，需要在服务端 `CORS_ALLOW_ORIGINS` 中显式配置。
- 文件下载、SSE/流式事件和桌面端登录链路需要在客户端壳内完成端到端验证。
- 桌面首版不支持 OIDC 登录。

## 范围约束

Windows 桌面客户端只承载前端入口、连接配置和桌面端认证存储。不要向该目录继续加入服务端部署、运行时编排或本地基础设施管理能力。
