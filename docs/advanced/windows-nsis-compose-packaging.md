# NSIS 安装器与 Docker Compose 封装方案

本文定义地下管网知识模型数据库的 Windows 桌面封装方案。安装器采用 NSIS，运行方式继续保留 Docker Compose；安装器只负责安装、初始化、启动器入口和卸载策略，不把服务改造成原生 Windows 进程。

## 安装目录结构

默认安装到当前用户目录，避免普通用户写入 `Program Files` 失败：

```text
%LOCALAPPDATA%\地下管网知识模型数据库
├── launcher\                 # 启动器 EXE 与运行时依赖
├── app\                      # 后端、前端、Dockerfile、Compose 与配置模板
│   ├── docker-compose.desktop.yml
│   ├── .env.template
│   ├── .env.desktop           # 首次启动生成；重装时保留
│   └── docker\volumes\        # 本机文件型运行数据
├── logs\                     # 启动器与安装诊断日志
├── images\                   # 可选离线镜像包
└── backups\                  # 卸载或升级前的用户备份位置
```

PostgreSQL 等必须使用 Docker 命名卷保存的数据，不放入安装器包内；安装器和启动器不得执行 `docker compose down -v`。

## Compose 命名规范

桌面运行必须使用独立项目名，默认 `COMPOSE_PROJECT_NAME=yuxi-desktop`。允许用户在 `.env.desktop` 中改成 `yuxi-desktop-<短实例号>`，用于同机多实例或避让已有项目。

`docker-compose.desktop.yml` 不应固定 `container_name`。容器、网络和默认命名卷交给 Compose 按项目名前缀生成，例如：

```text
yuxi-desktop-api-1
yuxi-desktop-postgres-1
yuxi-desktop_default
yuxi-desktop_postgres_data
```

如果必须给沙盒容器加前缀，使用 `DOCKER_SANDBOX_PREFIX=yuxi-desktop-sandbox`，不要复用开发栈的 `yuxi-sandbox`。这样可以避免本机已经存在 MinIO、Redis、PostgreSQL、Neo4j、Milvus 或其他 Yuxi 实例时发生容器名、网络名和数据卷冲突。

## 端口检测与自动改配

启动器在首次生成 `.env.desktop` 前检测宿主机端口占用。默认只暴露 Web 入口，其余状态服务不暴露到宿主机。

建议变量：

```env
YUXI_WEB_PORT=80
YUXI_MINERU_PORT=30001
YUXI_PADDLEX_PORT=8080
```

Compose 只引用变量：

```yaml
ports:
  - "${YUXI_WEB_PORT:-80}:80"
```

检测策略：

1. 优先尝试默认端口。
2. 被占用时从保留区间自动选择空闲端口，例如 Web 从 `18080-18100` 选择。
3. 将最终端口写入 `.env.desktop`，并在启动器界面展示访问地址。
4. 重装时不得覆盖已有 `.env.desktop` 里的端口配置。
5. 如果用户选择固定端口且端口被占用，启动器应阻断启动并提示占用进程或容器名。

PostgreSQL、Redis、MinIO、Milvus、Neo4j 默认只在 Compose 网络内访问，不开放 `5432`、`6379`、`9000`、`9001`、`19530`、`7474`、`7687` 到宿主机。

## 外部 MinIO 复用方案

桌面安装默认启动内置 MinIO。若用户本机已有 MinIO，可在启动器高级设置中选择“复用外部 MinIO”。该模式写入：

```env
YUXI_USE_EXTERNAL_MINIO=true
MINIO_URI=http://host.docker.internal:9000
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
```

启用外部 MinIO 时：

- Compose 不启动内置 `minio` 服务，API 和 worker 只读取 `MINIO_URI`。
- 启动器先执行连通性检查和桶权限检查，失败则不启动业务服务。
- 默认桶名必须带实例前缀，例如 `yuxi-desktop-<instance-id>`，避免复用同一个 MinIO 时对象互相覆盖。
- 凭据只写入 `.env.desktop`，不得写入日志、安装日志或审计日志。

Redis 与 PostgreSQL 不建议复用用户已有实例。它们承载任务队列、会话状态和业务数据库，默认必须使用本实例 Compose 网络内服务；需要外部化时应按生产部署文档处理，而不是桌面安装器自动接管。

## 卸载保留数据策略

NSIS 卸载器默认只删除启动器、程序文件、开始菜单项和桌面快捷方式，不删除：

- `.env.desktop`
- `app\docker\volumes`
- Docker 命名卷
- 用户备份目录
- 离线镜像包

卸载界面提供两个明确选项：

- `保留数据`：默认选项，只停止容器并保留数据。
- `删除数据`：二次确认后才允许删除本实例 Compose 项目、文件型数据目录和命名卷。

删除数据必须按 `COMPOSE_PROJECT_NAME` 限定范围，不能按镜像名或通用服务名批量删除，避免误删用户已有 MinIO、Redis、PostgreSQL 或其他项目数据。

## 生产环境 stdio MCP 安全限制

桌面封装继承生产环境 MCP 限制：

- 生产环境只允许代码内置的 stdio MCP 定义；禁止用户创建或修改任意 `command`、`args` 和 `env`。
- 内置 stdio MCP 默认禁用，仅超级管理员显式高风险确认后可启用。
- stdio MCP 依赖必须在镜像构建阶段固定版本，运行时禁止 `npx`、`uvx` 等临时联网下载。
- 子进程只继承最小环境变量，不得继承数据库、对象存储、模型密钥或代理凭据。
- MCP 创建、修改、测试、启停和删除必须写入脱敏审计；审计不得记录 headers、env 或密钥值。

## 验收清单

- 本机已有 `minio`、`redis`、`postgres` 容器时，桌面实例仍可启动。
- Web 默认端口被占用时，启动器能自动选择新端口并展示访问地址。
- `docker compose ps` 中容器、网络、卷都带 `COMPOSE_PROJECT_NAME` 前缀。
- 启用外部 MinIO 时，内置 MinIO 不启动，桶名前缀隔离通过。
- 卸载默认保留 `.env.desktop`、数据目录和命名卷。
- 生产环境无法创建自定义 stdio MCP，启用内置 stdio MCP 必须有超级管理员高风险确认和审计记录。
