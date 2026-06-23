# NSIS 安装器与 Docker Compose 封装方案

本文定义地下管网知识模型数据库的 Windows 桌面封装方案。安装器采用 NSIS，运行方式继续保留 Docker Compose；安装器只负责安装、初始化、启动器入口和卸载策略，不把服务改造成原生 Windows 进程。

## 决策边界

- 使用 NSIS 替换 Inno Setup；不并行维护两套安装器。
- 只支持当前用户安装，不提供管理员安装或所有用户安装。
- 安装器不内置 Docker 镜像；发布产物必须同时准备离线镜像包。
- 安装完成后不直接启动 Docker 服务，只打开启动器。
- Web 端口冲突时默认自动改配并继续启动；用户锁定端口时阻断启动。
- MinIO 默认使用内置服务，外部 MinIO 只能由用户显式选择。
- Redis 与 PostgreSQL 不提供桌面外部复用入口。
- 卸载默认保留全部数据；删除数据必须二次确认并限定在当前 Compose 项目名范围内。

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

PostgreSQL 等必须使用 Docker 命名卷保存的数据，不放入安装器包内；安装器和启动器不得执行默认 `docker compose down -v`。

NSIS 安装器使用 `RequestExecutionLevel user`，默认安装路径固定为 `%LOCALAPPDATA%\地下管网知识模型数据库`。每个 Windows 用户各自维护安装目录、`.env.desktop`、Compose 项目名和数据目录。

## 发布产物

安装器和离线镜像包分离发布：

```text
packaging/windows/dist/地下管网知识模型数据库.exe
packaging/windows/dist/images/yuxi-images.tar
```

`build_installer.ps1` 负责调用 NSIS `makensis` 生成安装器，不把 `yuxi-images.tar` 打进安装器。`export_images.ps1` 负责准备离线镜像包。

镜像导出脚本默认本地构建后保存镜像，确保安装器源码与镜像一致；也允许复用已有镜像：

```powershell
.\scripts\export_images.ps1 -Version 0.7.0.beta2
.\scripts\export_images.ps1 -Version 0.7.0.beta2 -UseExistingImages
```

默认模式构建并保存 `yuxi-api:<version>`、`yuxi-web:<version>`、`yuxi-sandbox-provisioner:<version>` 以及 desktop Compose 依赖的第三方基础镜像。`-UseExistingImages` 只检查本地镜像是否齐全并执行 `docker save`。

## 安装完成流程

NSIS 安装完成页可提供勾选项：

```text
[x] 启动地下管网知识模型数据库
```

勾选后只运行启动器。NSIS 本身不直接执行 `docker compose up -d`。

启动器首次启动流程：

1. 初始化 `.env.desktop`。
2. 检查 Docker Desktop、WSL2、Docker daemon 和 Docker Compose。
3. 检测宿主机端口并写入 `.env.desktop`。
4. 如发现 `images/yuxi-images.tar`，执行 `docker load -i`。
5. 用户点击“启动服务”后执行 `docker compose up -d`。

未发现离线镜像包时，启动器提示“未发现离线镜像包，将使用本地镜像或联网拉取/构建”。

## Compose 命名规范

桌面运行必须使用独立项目名，默认 `COMPOSE_PROJECT_NAME=yuxi-desktop`。允许用户在 `.env.desktop` 中改成 `yuxi-desktop-<短实例号>`，用于同机多实例或避让已有项目。

`docker-compose.desktop.yml` 不应固定 `container_name`。容器、网络和默认命名卷交给 Compose 按项目名前缀生成，例如：

```text
yuxi-desktop-api-1
yuxi-desktop-postgres-1
yuxi-desktop_default
yuxi-desktop_postgres_data
```

如果必须给沙盒容器加前缀，使用 `DOCKER_SANDBOX_PREFIX=yuxi-desktop-sandbox`，不要复用开发栈的 `yuxi-sandbox`。这样可以避免本机已经存在 MinIO、Redis、PostgreSQL、Neo4j、Milvus 或其他地下管网知识模型数据库实例时发生容器名、网络名和数据卷冲突。

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

1. Web 默认优先使用 `80`。
2. `80` 被占用时，从 `18080-18100` 自动选择第一个空闲端口。
3. 将最终端口写入 `.env.desktop`，并在启动器首页展示访问地址。
4. 重装时不得覆盖已有 `.env.desktop` 里的端口配置。
5. 如果用户在高级设置中锁定端口且端口被占用，启动器阻断启动并提示占用端口。

PostgreSQL、Redis、MinIO、Milvus、Neo4j 默认只在 Compose 网络内访问，不开放 `5432`、`6379`、`9000`、`9001`、`19530`、`7474`、`7687` 到宿主机。MinerU 和 PaddleX 等可选 profile 若暴露端口，按同样策略检测和写入 `.env.desktop`。

## 外部 MinIO 复用方案

桌面安装默认启动内置 MinIO。若用户本机已有 MinIO，可在启动器高级设置中显式选择“复用外部 MinIO”。该模式写入：

```env
YUXI_USE_EXTERNAL_MINIO=true
MINIO_URI=http://host.docker.internal:9000
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
```

启用外部 MinIO 时：

- Compose 不启动内置 `minio` 服务，API 和 worker 只读取 `MINIO_URI`。
- 启动器先执行 MinIO health、凭据和桶读写权限检查，失败则不启动业务服务。
- 默认桶名必须带实例前缀，例如 `yuxi-desktop-<instance-id>`，避免复用同一个 MinIO 时对象互相覆盖。
- 凭据只写入 `.env.desktop`，不得写入日志、安装日志或审计日志。

Redis 与 PostgreSQL 不提供桌面外部复用入口。它们承载任务队列、运行状态和业务数据库，默认必须使用本实例 Compose 网络内服务；需要外部化时应按服务端生产部署文档处理。

## 卸载保留数据策略

NSIS 卸载器默认只删除启动器、程序文件、开始菜单项和桌面快捷方式，不删除：

- `.env.desktop`
- `app\docker\volumes`
- Docker 命名卷
- 用户备份目录
- 离线镜像包

卸载界面提供两个明确选项：

- `保留数据`：默认选项，只停止本实例容器并保留数据。
- `删除数据`：二次确认后才允许删除本实例 Compose 项目、文件型数据目录和命名卷。

删除数据必须按 `COMPOSE_PROJECT_NAME` 限定范围，可执行等价于以下范围的操作：

```powershell
docker compose --env-file .env.desktop -f docker-compose.desktop.yml down -v
```

不得按镜像名、容器通用名、`minio`、`postgres`、`redis` 等裸名删除任何资源，避免误删用户已有服务或其他项目数据。离线镜像包默认保留；如需删除，应提供独立的“删除离线镜像包”选项。

## 生产环境 stdio MCP 安全限制

桌面封装继承生产环境 MCP 限制：

- 生产环境只允许代码内置的 stdio MCP 定义；禁止用户创建或修改任意 `command`、`args` 和 `env`。
- 内置 stdio MCP 默认禁用，仅超级管理员显式高风险确认后可启用。
- stdio MCP 依赖必须在镜像构建阶段固定版本，运行时禁止 `npx`、`uvx` 等临时联网下载。
- 子进程只继承最小环境变量，不得继承数据库、对象存储、模型密钥或代理凭据。
- MCP 创建、修改、测试、启停和删除必须写入脱敏审计；审计不得记录 headers、env 或密钥值。

## 验收清单

- 安装器由 NSIS 生成，产物名为 `地下管网知识模型数据库.exe`。
- 安装器使用当前用户权限安装，不触发 UAC 提权。
- `dist/images/yuxi-images.tar` 可由脚本生成，启动器能检测并加载。
- 安装完成后只打开启动器，不直接执行 Docker Compose 启动。
- 本机已有 `minio`、`redis`、`postgres` 容器时，桌面实例仍可启动。
- Web 默认端口被占用时，启动器能自动选择新端口并展示访问地址。
- `docker compose ps` 中容器、网络、卷都带 `COMPOSE_PROJECT_NAME` 前缀。
- 启用外部 MinIO 时，内置 MinIO 不启动，桶名前缀隔离通过。
- 卸载默认保留 `.env.desktop`、数据目录、命名卷和离线镜像包。
- 删除数据只影响当前 `COMPOSE_PROJECT_NAME` 下的资源。
- 生产环境无法创建自定义 stdio MCP，启用内置 stdio MCP 必须有超级管理员高风险确认和审计记录。
