# 项目简介

地下管网知识模型数据库（Pipeline-K-RAG）是基于 LangGraph v1、Vue 3、FastAPI、Milvus、Neo4j、PostgreSQL/PostGIS 和 MinIO 的多用户智能体平台。它面向地下管网、企业文档和空间数据，把知识入库、图谱构建、检索增强、空间分析与智能体工具调用整合为可部署的业务系统。

## 设计目标

- **知识统一**：文档 chunks、图谱实体关系和空间图层使用统一的知识库权限与智能体配置。
- **运行统一**：RAG、图谱和地图不是独立展示页，而是可被 LangGraph 智能体显式调用的工具。
- **数据可迁移**：`.yuxikb.zip` 在实例间迁移文档、chunks、图谱和配置，导入后重建索引。
- **多用户可治理**：部门、用户、知识库和智能体资源有明确的后端权限边界。
- **Docker 优先**：开发、测试、生产和 Windows 启动器都以 Docker Compose 为运行事实来源。

## 技术架构

| 层 | 技术 | 职责 |
|---|---|---|
| Web | Vue 3、Vite、Pinia、Ant Design Vue、MapLibre | 管理、对话、图谱、图层和地图 |
| API | FastAPI、Uvicorn | 认证、业务 API、SSE 与任务入口 |
| Agent | LangGraph v1、Tools、MCP、Skills、SubAgents | 智能体运行与工具编排 |
| 向量检索 | Milvus | 文档、实体和三元组向量 |
| 图数据库 | Neo4j | 实体关系和 chunk 引用 |
| 空间与业务数据 | PostgreSQL + PostGIS | 用户、权限、任务、chunks、图层和几何对象 |
| 对象存储 | MinIO | 原始文档、空间源文件和对象 |
| 队列与事件 | Redis、Worker | 异步任务、运行事件和取消信号 |
| 交付 | Docker Compose、Nginx、Windows Installer | 开发、生产与桌面启动 |

## 核心链路

### 智能体

智能体可以配置模型、提示词、内置工具、知识库工具、知识库、MCP、Skills 和 SubAgents。知识库工具包含 `query_kb`、`query_knowledge_graph`、空间图层查询和地图展示。

### RAG 与图谱

文档上传后经过解析、分块和向量化。图谱构建从 chunks 中抽取实体与关系，把关系写入 Neo4j，并为实体和三元组建立 Milvus 向量。`query_knowledge_graph` 查询显式子图，返回的实体 ID 可交给 `query_kb(graph_entity_ids=...)` 做图谱增强检索。

### 知识库迁移

导出包保存原始文件、解析结果、chunks、图谱和配置，不保存用户权限或 Provider 密钥。导入前执行结构、版本、数量、大小、Zip Slip 和 SHA-256 校验；导入后创建新 `kb_id` 并重建 Milvus 与 Neo4j 索引。

### 空间数据

空间模块支持 GeoJSON、SHP ZIP 和 GPKG。PostGIS 保存几何和图层元数据，MinIO 保存原始文件。用户可以管理图层、叠加显示、执行派生分析；智能体可查询图层和要素，并返回 MapLibre 交互地图。

## 适用场景

- 地下管网资料、图层和运维知识统一管理；
- 企业私有知识问答与可追溯检索；
- 知识图谱实体关系探查与图谱增强 RAG；
- 多部门、多用户的知识资源治理；
- 文档知识库跨终端迁移；
- 空间要素分析和智能体会话地图。

## 开始使用

- [快速开始](./quick-start.md)
- [模型配置](./model-config.md)
- [知识库与知识图谱](./knowledge-base.md)
- [Main2 能力](../features/main2-capabilities.md)
- [智能体配置](../agents/agents-config.md)
- [生产部署](../advanced/deployment.md)
