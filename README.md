# 地下管网知识模型数据库（Pipeline-K-RAG）

面向地下管网、企业文档和空间数据的多用户智能体平台。系统把 RAG、显式知识图谱检索、可迁移知识库、PostGIS 空间分析、图层叠加和会话地图接入同一套 LangGraph 运行链路。

[English](README.en.md) · [架构](ARCHITECTURE.md) · [完整文档](docs/intro/project-overview.md) · [MIT License](LICENSE)

## 核心能力

- **智能体编排**：模型、提示词、内置工具、知识库工具、MCP、Skills 和 SubAgents 可按智能体配置。
- **RAG 与知识图谱**：Milvus 保存文档、实体和三元组向量，Neo4j 保存关系；`query_knowledge_graph` 显式返回子图。
- **图谱增强检索**：`query_kb(graph_entity_ids=...)` 以图谱实体为种子扩展关系，并融合文档与图谱召回。
- **独立图谱构建模型**：创建 Milvus 知识库时可选择图谱抽取 Chat 模型、Schema、并发数和模型参数。
- **知识库迁移**：`.yuxikb.zip` 导出文档、chunks、图谱和配置；导入前校验 manifest/checksum，导入后重建 Milvus 与 Neo4j 索引。
- **空间数据**：PostgreSQL/PostGIS 保存图层和几何对象，MinIO 保存原始文件；支持 GeoJSON、SHP ZIP、GPKG、图层组合和派生分析。
- **交互地图**：MapLibre GL JS 支持图层显隐、顺序、透明度、拖拽、缩放、要素点击和属性查看。
- **多用户平台**：支持超级管理员、部门管理员和普通用户，以及知识库和智能体资源权限。

## 技术栈

| 层 | 技术 |
|---|---|
| Web | Vue 3、Vite、Pinia、Ant Design Vue、MapLibre GL JS |
| API / Agent | FastAPI、LangGraph v1、ARQ Worker |
| 数据 | PostgreSQL + PostGIS、Redis、MinIO、Milvus、Neo4j |
| 交付 | Docker Compose、Nginx、Windows 启动器与 Inno Setup |

## 部署前准备

推荐环境：

- Docker Engine 24+ 或 Docker Desktop；
- Docker Compose v2.20+；
- Git；
- 至少 16 GB 内存和 20 GB 可用磁盘；大规模知识库应预留更多空间；
- 可访问所选模型 Provider 的网络和 API Key。

默认开发端口：

| 服务 | 地址 |
|---|---|
| Web | http://localhost:5173 |
| API / Swagger | http://localhost:5050/docs |
| Neo4j Browser | http://localhost:7474 |
| MinIO Console | http://localhost:9001 |
| PostgreSQL | localhost:5432 |
| Milvus | localhost:19530 |

若端口已占用，请先停止冲突服务，或修改 `docker-compose.yml` 的宿主机端口。

## 五分钟启动

### 1. 获取代码

```bash
git clone https://github.com/2233531707/pipeline-k-rag.git
cd pipeline-k-rag
```

### 2. 创建配置

Linux / macOS：

```bash
cp .env.template .env
./scripts/init.sh
```

Windows PowerShell：

```powershell
Copy-Item .env.template .env
.\scripts\init.ps1
```

初始化脚本会补齐 JWT 安全项并拉取基础镜像。也可以手动编辑 `.env`，至少配置：

```dotenv
YUXI_ENV=development
JWT_SECRET_KEY=请替换为至少32字节的随机值
YUXI_INSTANCE_ID=pipeline-k-rag-local
SILICONFLOW_API_KEY=你的模型服务密钥
```

不要提交 `.env`。模型 Provider 也可在系统启动后通过“模型配置”页面维护。

### 3. 校验并启动

```bash
docker compose config
docker compose up -d --build
docker compose ps
```

首次构建会下载镜像和依赖，时间取决于网络。等待 `api-dev`、PostgreSQL、Redis、MinIO、Milvus、Neo4j 和 sandbox provisioner 健康后，访问：

- Web：http://localhost:5173
- API 健康检查：http://localhost:5050/api/system/health
- API 文档：http://localhost:5050/docs

首次进入 Web 时按页面提示初始化超级管理员。

### 4. 查看日志

```bash
docker logs api-dev --tail 100
docker logs worker-dev --tail 100
docker logs web-dev --tail 100
```

停止服务但保留数据：

```bash
docker compose down
```

不要在仍需保留数据时执行 `docker compose down -v`，也不要删除 `docker/volumes/`。PostgreSQL/PostGIS 使用 Docker 命名卷，`down -v` 会删除该数据库卷。

## 运行模式

### 完整开发模式

```bash
docker compose up -d
```

`api-dev`、`worker-dev` 和 `web-dev` 挂载源码并热重载。后端代码位于容器 `/app/package`、`/app/server`，测试位于 `/app/test`。

### 轻量模式

仅在不需要 Milvus、Neo4j 和知识库能力时使用：

```bash
make up-lite
```

地下管网知识模型数据库的主要功能依赖完整模式，正式验收不要使用 Lite 模式。

### GPU OCR

默认栈不启动 MinerU 和 PaddleX。具备 NVIDIA Container Toolkit 时可启用：

```bash
docker compose --profile all up -d --build
```

### Isolated 验收模式

isolated 环境使用独立端口、容器名和数据卷，适合验证生产构建：

```bash
pnpm --dir web install
pnpm --dir web build
make sync-test-rebuild
make sync-test-status
```

访问：

- Web：http://localhost:15173
- API：http://localhost:15050
- Neo4j：http://localhost:17474
- MinIO Console：http://localhost:19001

isolated Web 由 Nginx 只读挂载 `web/dist`，不支持源码热更新。修改 `web/src` 后必须重新执行 `pnpm --dir web build` 并刷新页面。

## 生产部署

生产环境使用独立配置：

```bash
cp .env.template .env.prod
```

至少修改：

```dotenv
YUXI_ENV=production
JWT_SECRET_KEY=使用密码管理器生成的强随机值
YUXI_INSTANCE_ID=生产实例唯一标识
POSTGRES_PASSWORD=强密码
NEO4J_PASSWORD=强密码
MINIO_ACCESS_KEY=非默认访问键
MINIO_SECRET_KEY=强随机密钥
```

启动时必须同时传入 `--env-file`，确保 Compose 变量替换和容器 `env_file` 使用同一份配置：

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml config
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

生产 Web 默认监听 http://localhost ，API 经 Nginx 的 `/api` 转发。公网部署前还应配置 HTTPS、反向代理访问控制、备份、监控和日志保留策略。详见 [生产部署指南](docs/advanced/deployment.md)。

## 开发与测试

后端测试必须在 Docker 容器内运行：

```bash
docker compose exec api pytest test/unit -q
docker compose exec api pytest test/integration -q
docker compose exec api pytest test/e2e -q
docker compose exec api ruff check package server test
```

前端：

```bash
docker compose exec web pnpm lint
docker compose exec web pnpm test
docker compose exec web pnpm build
```

完整规范见 [测试规范](docs/develop-guides/testing-guidelines.md)。

## 大数据与并发说明

- 文件上传、迁移包导入和空间数据导入采用流式或分批处理，避免把大文件完整载入内存。
- `.yuxikb.zip` 后端上限为 5 GiB；Nginx 迁移接口预留到 6 GiB，并关闭请求缓冲。
- 长耗时智能体和导入任务交给 Worker；Redis 承载运行事件，PostgreSQL 保存任务和业务状态。
- Milvus、Neo4j、PostGIS 和 MinIO 分别承担向量、关系、空间和对象存储职责，避免单库混用。
- 生产容量仍需按文档数量、并发用户、向量维度和空间要素规模做压测与资源规划。

## 项目结构

```text
backend/            后端业务包、FastAPI 服务、Worker 和测试
web/                Vue 前端源码；dist 为本地构建产物
docker/             镜像、Nginx、沙盒和本地数据卷
docs/               用户文档、开发指南和任务报告
packaging/windows/  Windows 启动器和安装包源码
scripts/            初始化、镜像和维护脚本
```

详见 [项目结构说明](docs/develop-guides/project-structure.md) 和 [架构代码地图](ARCHITECTURE.md)。

## 常见问题

### 页面没有显示最新前端修改

开发环境访问 `5173`。若访问 `15173`，先构建 `web/dist`：

```bash
pnpm --dir web build
make sync-test-rebuild
```

### 迁移包导入返回 413

确认访问的是当前 Nginx 配置，并重新构建 Web/代理容器：

```bash
docker compose up -d --build web
```

迁移接口 `/api/knowledge/portable-import` 的代理上限是 6 GiB，后端包上限是 5 GiB。若前面还有其他反向代理，也要同步调整其请求体限制。

### API 启动失败

```bash
docker compose ps
docker logs api-dev --tail 200
docker logs postgres --tail 100
docker logs milvus --tail 100
docker logs graph --tail 100
```

常见原因是端口占用、`.env` 缺少 JWT 配置、数据卷权限或依赖服务未健康。

### 智能体工具调用异常

先在智能体编辑器的“知识库工具”中确认启用了所需工具，再检查模型是否支持标准 tool calling。`query_knowledge_graph`、`query_kb`、`list_spatial_layers`、`query_spatial_features` 和 `show_spatial_map` 都属于知识库工具。

## 不应提交的内容

`.gitignore` 已排除以下本地内容：

- `.env*` 私密配置；
- `docker/volumes/`、`saves*` 和数据库文件；
- `node_modules/`、`dist/`、缓存和日志；
- `.yuxikb.zip` 迁移包、模型文件和 Windows 构建产物；
- `.claude/`、`.codex/` 和 IDE 个人配置。

发布前仍应执行敏感信息扫描，确认模板和文档中没有真实密码、Token、用户数据或私有迁移包。

## 文档

- [项目简介](docs/intro/project-overview.md)
- [快速开始](docs/intro/quick-start.md)
- [Main2 能力](docs/features/main2-capabilities.md)
- [知识库迁移格式](docs/features/knowledge-base-portable-package.md)
- [生产部署](docs/advanced/deployment.md)
- [Windows 打包](docs/advanced/windows-package.md)
- [测试规范](docs/develop-guides/testing-guidelines.md)
- [版本记录](docs/develop-guides/changelog.md)

## License 与致谢

项目遵循 [MIT License](LICENSE)。二次开发继续保留上游 Yuxi 以及 LangGraph、Milvus、Neo4j、PostGIS、MapLibre 等第三方项目的许可证和必要归属说明。
