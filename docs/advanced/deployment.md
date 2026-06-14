# 生产部署

生产部署使用 `docker-compose.prod.yml`。它会构建无热重载的 API/Worker 和 Nginx Web，并持久化 PostgreSQL/PostGIS、Redis、MinIO、Milvus、Neo4j 与应用文件。

## 前置要求

- Docker Engine 24+；
- Docker Compose v2.20+；
- 推荐 4 核 CPU、16 GB 内存和 50 GB 可扩展磁盘作为小规模起点；
- 公网场景需要独立 HTTPS 反向代理或负载均衡器；
- 大规模文档、空间要素和并发用户需要单独压测。

## 1. 创建生产配置

```bash
cp .env.template .env.prod
```

必须设置：

```dotenv
YUXI_ENV=production
JWT_SECRET_KEY=至少32字节的强随机值
YUXI_INSTANCE_ID=生产实例唯一标识
POSTGRES_USER=postgres
POSTGRES_PASSWORD=强密码
POSTGRES_DB=yuxi
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=强密码
MINIO_ACCESS_KEY=非默认访问键
MINIO_SECRET_KEY=强随机密钥
```

按实际 Provider 增加模型密钥。不要把 `.env.prod` 提交到 Git、镜像或备份日志中。

## 2. 校验 Compose

生产命令必须同时使用 `--env-file .env.prod` 与 `-f docker-compose.prod.yml`。前者负责 Compose 变量替换，后者选择生产服务定义。

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml config
```

检查输出中没有空的生产密钥、默认密码或错误路径。

## 3. 构建和启动

CPU 核心服务：

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

启用 GPU OCR：

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile all up -d --build
```

## 4. 验证

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker logs api-prod --tail 200
docker logs worker-prod --tail 200
docker logs web-prod --tail 100
curl http://localhost/api/system/health
```

默认 Web 为 http://localhost ，API 通过 `/api` 转发。

首次访问后初始化超级管理员，并验证登录、模型、智能体、知识库、图谱、迁移和空间地图。

## 5. HTTPS 与反向代理

生产 Compose 的 Nginx 已处理应用静态文件、API、SSE 和迁移大文件。公网入口还应：

- 只开放 80/443，数据库、Milvus、Neo4j 和 MinIO 管理端口仅内网可见；
- 配置 TLS、HSTS、访问日志和合理的速率限制；
- SSE 路径关闭代理缓冲并延长读取超时；
- 对 `/api/knowledge/portable-import` 允许至少 6 GiB 请求体，或与后端 5 GiB 上限保持一致；
- 保持上传流式转发，避免代理层为并发大文件占用大量临时磁盘。

## 6. 数据和备份

PostgreSQL/PostGIS 使用 Compose 命名卷 `postgres_prod_data`，其余本地运行数据位于 `docker/volumes/`；两者都不得提交 Git。备份至少覆盖：

- PostgreSQL/PostGIS 命名卷（使用 `pg_dump`/`pg_restore`，不要直接复制运行中的数据目录）；
- Neo4j 数据目录；
- Milvus、etcd 和 MinIO 数据；
- `docker/volumes/yuxi` 应用文件；
- 生产 `.env.prod`，但应使用受控的密钥备份渠道。

备份必须做恢复演练。知识库 `.yuxikb.zip` 是跨实例迁移格式，不能替代整套平台备份。

## 7. 更新与回滚

更新前备份数据并记录当前镜像和提交：

```bash
git pull
docker compose --env-file .env.prod -f docker-compose.prod.yml build
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

更新后重新执行健康检查和关键业务验收。代码回滚不能替代数据库兼容性评估，涉及表结构或索引变更时应先阅读版本记录。

## 8. 容量和并发

- API 与 Worker 分离，长耗时任务不应阻塞请求进程；
- Redis 负责队列与运行事件，PostgreSQL 保存任务状态；
- 大文件采用流式上传，空间要素和文档索引采用分批处理；
- Milvus、Neo4j、PostGIS 和对象存储应根据数据规模独立监控；
- 生产压测应覆盖并发对话、工具调用、迁移导入、空间查询和批量入库。

## 9. 停止服务

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml down
```

除非已确认不再需要数据，否则不要添加 `-v`，也不要直接删除 `docker/volumes/`。
