# T25 任务报告：Docker 全量回归

## 验收环境

- 日期：2026-06-14
- 栈：Docker Compose 开发环境
- 后端版本：`0.7.0b2`
- 数据库：PostgreSQL/PostGIS 16-3.5
- 向量库：Milvus 2.5.6
- 图数据库：Neo4j 5.26
- 迁移样本：`1-kb_h44zy.yuxikb.zip`（约 20.4 MiB）
- 空间样本：`wspoint.zip`、`wsline.zip`

测试仅使用小样本和一份现有迁移包；实现仍采用流式上传、后台任务、批处理和数据库连接池等面向大批量数据及多用户并发的设计。

## 自动化回归

| 检查项 | 结果 |
| --- | --- |
| `docker compose config` | 通过 |
| Docker 服务健康检查 | API、PostGIS、Milvus、Neo4j、MinIO、Redis、Sandbox 均健康 |
| 后端单元测试 | `573 passed, 2 skipped` |
| 后端集成测试 | `142 passed, 4 skipped` |
| 后端 E2E 与恢复链路 | `8 passed, 3 skipped` |
| 前端 lint | 通过 |
| 前端测试 | 6 组脚本全部通过 |
| 前端生产构建 | 通过，8241 modules transformed |
| VitePress 文档构建 | 通过 |
| Web/API 探活 | `5173` 与 `/api/system/health` 均返回 200 |

集成测试的 4 个跳过项包括 1 个需要预置已上传文档的思维导图生成场景，以及 3 个需要真实外部模型密钥的 provider 连通性场景。E2E 的 3 个跳过项同样依赖真实外部 LLM 凭据；本轮使用本地 OpenAI 协议兼容模型替身验证迁移重建链路，没有把无密钥错误伪装成通过。

## 功能验收

- [x] 登录：管理员初始化、登录和 JWT 鉴权通过。
- [x] 权限：普通用户部门隔离、Agent 资源权限和 Viewer 越权拒绝通过。
- [x] 智能体：创建、读取、删除及知识工具选择持久化通过。
- [x] 知识库：列表、创建、迁移导入、查询和清理通过。
- [x] 图谱构建 Chat 模型：模型配置校验和 OpenAI 兼容调用链通过。
- [x] `query_knowledge_graph`：智能体可配置工具列表包含该工具，图谱子图查询返回节点。
- [x] graph-seeded `query_kb`：迁移知识库的图谱种子检索返回成功。
- [x] 迁移导出：后台导出任务成功，下载包非空。
- [x] 迁移导入：19 个文件、1711 个分块、3650 个实体、2723 条关系导入成功。
- [x] 重建索引：1711 个文档向量、1047 个图谱向量重建成功。
- [x] PostGIS：点、线图层均成功写入并可查询要素详情。
- [x] 图层叠加：图层组合创建接口返回 200。
- [x] 会话地图：`list_spatial_layers`、`query_spatial_features`、`show_spatial_map` 均进入 Agent 可配置工具列表。
- [x] UI：标题、导航、知识模型数据库页面和空间地图交互构建通过。
- [x] LICENSE：根目录 MIT License 存在。

## 实测数据

| 场景 | 结果 |
| --- | --- |
| 迁移包预检 | 19 files / 1711 chunks / 3650 entities / 2723 relationships |
| 迁移包导入 | 成功，无 413 |
| 文档向量重建 | 1711 |
| 图谱向量重建 | 1047 |
| `wspoint.zip` | 1 图层 / 590 点要素 |
| `wsline.zip` | 1 图层 / 2481 线要素 |
| 空间入库任务 | submitted=2 / failed=0 |
| Agent 知识工具 | 9 个，包含图谱检索和空间地图工具 |

不含 `.prj` 的 `ysline.zip` 被系统明确拒绝，符合坐标系校验预期。

## 修复与结论

- 修复 Windows/WSL bind mount 下 `watchfiles` 原生监听器导致 API/Worker 退出的问题，开发 Compose 默认启用轮询。
- 修复集成/E2E 中遗留的旧 Agent API 路径和 `agent_config_id` 请求字段。
- 修复 Agent 资源序列化遗漏 `knowledge_tools`，确保编辑器选择可持久化并进入运行时。
- PostgreSQL 开发和生产栈使用命名卷，生产数据库统一为 PostGIS 镜像。

T25 验收通过。非阻断警告包括 SQLAlchemy 旧 `declarative_base`、`langchain-community` 维护状态、Vite 大 chunk 提示和 pnpm overrides 配置迁移提示，均未影响本轮功能与构建结果。
