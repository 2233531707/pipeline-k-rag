# 快速开始

本指南使用 Docker Compose 启动“地下管网知识模型数据库”的完整开发环境，包括 API、Worker、Web、PostgreSQL/PostGIS、Redis、MinIO、Milvus、Neo4j 和沙盒 provisioner。

## 环境要求

- Docker Engine 24+ 或 Docker Desktop；
- Docker Compose v2.20+；
- Git；
- 推荐 16 GB 内存、20 GB 可用磁盘；
- 模型 Provider API Key。

默认服务不要求 GPU。MinerU 和 PaddleX 仅在启用 `all` profile 时启动。

## 1. 获取代码

```bash
git clone https://github.com/2233531707/pipeline-k-rag.git
cd pipeline-k-rag
```

## 2. 配置环境

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

脚本会补齐 JWT 随机值并拉取基础镜像。手动配置时至少填写：

```dotenv
YUXI_ENV=development
JWT_SECRET_KEY=至少32字节随机值
YUXI_INSTANCE_ID=pipeline-k-rag-local
SILICONFLOW_API_KEY=你的模型服务密钥
```

`.env` 只用于本机，不要提交到 Git。

## 3. 启动完整环境

```bash
docker compose config
docker compose up -d --build
docker compose ps
```

首次构建可能需要较长时间。等待核心服务健康后访问：

| 服务 | 地址 |
|---|---|
| Web | http://localhost:5173 |
| API 文档 | http://localhost:5050/docs |
| API 健康检查 | http://localhost:5050/api/system/health |
| Neo4j Browser | http://localhost:7474 |
| MinIO Console | http://localhost:9001 |

首次访问 Web 时，页面会引导初始化超级管理员。

## 4. 验证和日志

```bash
docker logs api-dev --tail 100
docker logs worker-dev --tail 100
docker logs web-dev --tail 100
```

API 健康检查：

```bash
curl http://localhost:5050/api/system/health
```

## 5. 停止与更新

停止并保留数据：

```bash
docker compose down
```

拉取更新后重建：

```bash
git pull
docker compose up -d --build
```

不要在需要保留数据时执行 `docker compose down -v` 或删除 `docker/volumes/`。

## 可选模式

### Lite 模式

```bash
make up-lite
```

Lite 模式不启动 Milvus、Neo4j 等知识库依赖，不适合验证图谱、迁移和空间能力。

### GPU OCR

```bash
docker compose --profile all up -d --build
```

需要 NVIDIA Container Toolkit 和足够显存。

### Isolated 验收

```bash
pnpm --dir web install
pnpm --dir web build
make sync-test-rebuild
make sync-test-status
```

isolated Web 为 http://localhost:15173，API 为 http://localhost:15050。该 Web 使用 `web/dist`，修改前端源码后必须重新构建。

## 常见问题

### 端口占用

停止占用 `5173`、`5050`、`5432`、`6379`、`7474`、`7687`、`9000`、`9001`、`19530` 或 `9091` 的进程，或修改 Compose 端口。

### 构建或拉取失败

检查 Docker 网络和代理配置。初始化脚本使用 `scripts/pull_image.*` 拉取镜像；代理配置错误时也可能导致超时。

### Milvus 或 Neo4j 未健康

```bash
docker logs milvus --tail 100
docker logs graph --tail 100
docker compose up -d milvus graph
```

### 前端没有更新

开发环境使用 `5173` 热重载。若访问 `15173`，重新执行：

```bash
pnpm --dir web build
make sync-test-rebuild
```

### 迁移包返回 413

当前迁移接口后端支持 5 GiB，Nginx 支持 6 GiB。重新构建 Web/代理容器，并检查系统外层是否还有请求体限制更小的反向代理。

## 下一步

- [模型配置](./model-config.md)
- [知识库与知识图谱](./knowledge-base.md)
- [Main2 能力](../features/main2-capabilities.md)
- [智能体配置](../agents/agents-config.md)
- [生产部署](../advanced/deployment.md)
