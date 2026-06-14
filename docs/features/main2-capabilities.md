# Main2.0 能力说明

Main2.0 将知识库、知识图谱与空间数据统一接入智能体运行链路，而不是把它们做成彼此独立的展示页面。

## 图谱增强检索

Milvus 保存文档 chunk、唯一实体与三元组的语义向量，Neo4j 保存实体关系和 chunk 引用。智能体可调用：

- `query_knowledge_graph`：按问题或实体显式查询图谱子图；
- `query_kb(graph_entity_ids=...)`：以实体 ID 为种子扩展图谱，再通过 RRF 融合 chunk 与图谱召回。

创建 Milvus 知识库时可预配置图谱抽取 Chat 模型、Schema、并发数和模型参数。该配置引用模型 spec，不复制 API Key。

## 可迁移知识库

`.yuxikb.zip` 是 Yuxi Portable Knowledge Package V1。导出包保存原始文件、解析 Markdown、chunks、图谱配置、实体关系与 checksum，不保存用户、权限或 Provider 凭据。

导入流程会先做 Zip Slip、数量、大小、版本与 SHA-256 校验，再创建新的 `kb_id`，恢复文件和图谱数据，并重建 Milvus 文档/图谱向量及 Neo4j 图索引。失败时回滚新建资源。

## 空间数据与地图

空间图层元数据和几何对象位于 PostgreSQL/PostGIS，原始数据文件位于 MinIO。系统支持上传、图层管理、图层叠加、派生空间分析及智能体空间工具。

`show_spatial_map` 的前端结果由 MapLibre GL JS 渲染，支持多图层显隐、顺序、透明度、缩放平移、自动 bounds、点击 Popup、属性抽屉、Loading/Error/空状态和要素超限提示。

## UI 与运行方式

`web/src/assets/css/tokens.css` 提供项目级 Token。开发 Web 使用 Vite 热重载；隔离验收 Web 使用 Nginx 挂载 `web/dist`，因此源码变化后必须先构建再启动或刷新隔离栈。

所有服务、数据卷与健康检查以 Docker Compose 为事实来源。Windows 交付同样调用 Compose，不另造一套运行架构。
