# Yuxi `main2.0` 二次开发分任务执行指南

> 适用对象：Claude Code  
> 开发目录：`D:\learn\pro\yuxi\Yuxi-sync-upstream-latest`  
> 目标集成分支：`main2.0`  
> UI 参考模板：`D:\learn\pro\yuxi\Yuxi-sync-upstream-latest\ui_template.hml`
>
> 本文档用于分阶段执行 Yuxi 新版本二次开发。  
> 每个任务必须独立执行、独立测试、独立提交、独立推送，并保留可回溯历史。

---

# 1. 全局技术规则

## 1.1 开发基线

- 所有开发只在 `D:\learn\pro\yuxi\Yuxi-sync-upstream-latest` 中进行。
- 旧版本主工作区仅作为只读参考，不允许整体复制旧版目录。
- 禁止恢复 LightRAG。
- 最终集成分支固定为：

```text
main2.0
```

## 1.2 知识图谱架构

知识图谱能力必须基于当前新版本架构：

```text
Milvus 文档知识库
+ Neo4j 图谱节点与关系
+ 图谱抽取
+ 图谱扩展检索
+ Personalized PageRank
+ RRF 融合
```

本次增强目标：

```text
query_knowledge_graph
→ 返回节点、关系、graph_entity_ids
→ query_kb(graph_entity_ids=...)
→ 图谱扩展召回
→ 与普通知识库检索融合
→ 返回增强后的文档片段
```

## 1.3 图谱抽取模型配置

图谱抽取使用 Chat 模型规格，不绑定聊天智能体实例。

统一使用：

```text
graph_build_config.extractor_options.model_spec
```

前端文案统一为：

```text
图谱抽取 Chat 模型
```

禁止使用：

```text
Chat 智能体
聊天智能体
问答智能体
```

图谱抽取配置唯一保存位置：

```text
additional_params.graph_build_config
```

推荐结构：

```json
{
  "locked": true,
  "extractor_type": "llm",
  "extractor_options": {
    "model_spec": "provider/model",
    "schema": "",
    "concurrency_count": 1,
    "model_params": {}
  }
}
```

## 1.4 知识库迁移格式

实现应用层逻辑迁移包：

```text
Yuxi Portable Knowledge Package V1
*.yuxikb.zip
```

迁移包禁止直接打包底层数据库文件。

禁止导出：

```text
Milvus 原始 collection 文件
Neo4j 数据目录
PostgreSQL dump
Docker volume
整个 MinIO bucket
API Key
Provider 凭证
用户 Token
原终端用户 ID
部门 ID
共享权限
本地绝对路径
任务运行状态
```

迁移包必须包含：

```text
manifest.json
database.json
files/originals/
files/parsed/
chunks/chunks.jsonl
graph/config.json
graph/extraction_results.jsonl
graph/entities.jsonl
graph/relationships.jsonl
settings/query_params.json
checksums/sha256.json
```

导入规则：

```text
上传迁移包
→ 安全校验
→ 创建新 kb_id
→ 恢复原始文档和 Markdown
→ 恢复 Chunk
→ 使用目标终端选择的嵌入模型重建 Milvus 向量
→ 使用实体与关系重建 Neo4j 图谱
→ 重建图谱向量索引
→ 输出导入报告
```

默认不重复调用 LLM 抽取。  
只有用户明确选择重新抽取图谱时，才重新调用图谱抽取 Chat 模型。

## 1.5 空间数据架构

空间数据模块独立于文档知识库模块。

统一采用：

```text
PostgreSQL + PostGIS
MinIO
GeoPandas
Shapely
PyProj
GeoJSON API
MapLibre GL JS
```

## 1.6 UI 参考模板

UI 模板路径：

```text
D:\learn\pro\yuxi\Yuxi-sync-upstream-latest\ui_template.hml
```

执行 UI 任务前必须确认该文件是否实际为 HTML。

若 `.hml` 不存在，再检查：

```text
D:\learn\pro\yuxi\Yuxi-sync-upstream-latest\ui_template.html
```

模板只能用于抽取：

- 视觉风格；
- 页面布局；
- 色彩；
- 圆角；
- 阴影；
- 间距；
- 卡片；
- 表单；
- 导航；
- 地图展示；
- 图谱结果卡片。

禁止直接覆盖 Vue 项目。  
禁止复制 Tailwind CDN、静态演示逻辑、假数据和静态路由。

## 1.7 Windows `.exe` 方案

唯一允许的 Windows 交付形式：

```text
Yuxi-Desktop-Setup.exe
```

它是 Docker 启动器安装包，不是将 Linux 容器转换为原生 Windows 单体程序。

开发环境仍以 Docker Compose 为主。

---

# 2. Git 提交与远端回溯规范

## 2.1 每个任务必须独立分支

任务分支格式：

```text
feat/main2-tXX-任务名称
```

示例：

```text
feat/main2-t03-graph-query-tool
feat/main2-t08-graph-model-config
feat/main2-t11-kb-portable-export
feat/main2-t20-spatial-map
feat/main2-t22-ui-layout
```

## 2.2 每个任务开始前必须执行

```powershell
cd D:\learn\pro\yuxi\Yuxi-sync-upstream-latest

git fetch origin --prune
git status --short
git branch --show-current
git remote -v
git remote get-url origin
git log --oneline --decorate -n 12
```

若存在未提交修改：

- 列出全部修改文件；
- 不覆盖；
- 不 reset；
- 不 stash；
- 不继续开发；
- 输出阻断报告。

## 2.3 远端安全检查

禁止直接推送原作者仓库：

```text
xerrors/Yuxi
```

只允许推送用户自己的 fork。

推荐远端结构：

```text
origin   = 用户自己的 fork
upstream = xerrors/Yuxi
```

## 2.4 每个任务完成后的固定流程

```text
完成代码修改
→ 运行当前任务测试
→ 修复测试失败
→ 提交代码
→ 新增任务报告
→ 提交任务报告
→ 推送任务分支
→ 合并到 main2.0
→ 推送 main2.0
→ 输出远端 commit SHA
```

## 2.5 测试失败规则

若测试失败且暂时无法修复：

```text
不得合并 main2.0
不得推送失败代码到 main2.0
允许推送任务分支保留现场
任务报告必须标记 WIP
任务报告必须写明失败原因
```

## 2.6 任务报告

每个任务完成后新增：

```text
docs/development/task-reports/TXX-任务名称.md
```

统一结构：

```markdown
# TXX 任务报告

## 目标
## 分支
## 修改文件
## 新增文件
## 删除文件
## 测试命令
## 测试结果
## 风险
## 已知限制
## 提交
- 代码 commit：
- 报告 commit：
- main2.0 commit：
## 远端
- 任务分支：
- main2.0：
```

## 2.7 阶段检查点 Tag

完成阶段后创建：

```text
main2-checkpoint-graph
main2-checkpoint-migration
main2-checkpoint-spatial
main2-checkpoint-ui
main2-checkpoint-docs
main2-checkpoint-windows
```

---

# 3. 任务总览

| 编号 | 任务 | 前置任务 | 必须测试 | 必须独立提交并推送 |
|---|---|---|---:|---:|
| T00 | 工作区、远端与模板基线检查 | 无 | 是 | 是 |
| T01 | 初始化 `main2.0` 与任务报告机制 | T00 | 是 | 是 |
| T02 | 显式图谱查询能力扫描与设计 | T01 | 是 | 是 |
| T03 | 新增 `query_knowledge_graph` | T02 | 是 | 是 |
| T04 | 扩展 `query_kb` 图谱种子增强检索 | T03 | 是 | 是 |
| T05 | 图谱工具前端结果卡片 | T04 | 是 | 是 |
| T06 | 图谱显式检索链路回归 | T05 | 是 | 是 |
| T07 | 图谱抽取模型配置扫描与设计 | T06 | 是 | 是 |
| T08 | 新建知识库支持图谱抽取 Chat 模型预配置 | T07 | 是 | 是 |
| T09 | 图谱抽取模型配置交互测试 | T08 | 是 | 是 |
| T10 | 知识库迁移格式设计与安全模型 | T09 | 是 | 是 |
| T11 | `.yuxikb.zip` 导出服务 | T10 | 是 | 是 |
| T12 | `.yuxikb.zip` 导入预检与恢复服务 | T11 | 是 | 是 |
| T13 | 知识库迁移前端 | T12 | 是 | 是 |
| T14 | 知识库迁移端到端测试 | T13 | 是 | 是 |
| T15 | 空间数据模块扫描与设计 | T14 | 是 | 是 |
| T16 | PostGIS 空间图层基础模型 | T15 | 是 | 是 |
| T17 | 空间数据上传与图层管理 | T16 | 是 | 是 |
| T18 | 图层叠加与派生空间分析 | T17 | 是 | 是 |
| T19 | 空间智能体工具 | T18 | 是 | 是 |
| T20 | 会话内地图可视化 | T19 | 是 | 是 |
| T21 | UI 模板分析与设计 Token | T20 | 是 | 是 |
| T22 | 登录页、首页与整体布局优化 | T21 | 是 | 是 |
| T23 | 业务页面统一与品牌清理 | T22 | 是 | 是 |
| T24 | 文档重写与目录整理 | T23 | 是 | 是 |
| T25 | Docker 全量回归 | T24 | 是 | 是 |
| T26 | Windows `.exe` 启动器与安装包 | T25 | 是 | 是 |
| T27 | 最终验收、Tag 与发布报告 | T26 | 是 | 是 |

---

# 4. T00：工作区、远端与模板基线检查

## 目标

确认：

- 工作树；
- 当前分支；
- Git 远端；
- 未提交改动；
- Docker；
- Docker Compose；
- UI 模板；
- 项目基础目录。

## 执行

```powershell
cd D:\learn\pro\yuxi\Yuxi-sync-upstream-latest

git fetch --all --tags --prune
git status --short
git branch --show-current
git branch --all
git remote -v
git remote get-url origin
git log --oneline --decorate -n 15
git worktree list

Get-ChildItem -Force
Get-Item .\ui_template.hml -ErrorAction SilentlyContinue
Get-Content .\ui_template.hml -TotalCount 80 -ErrorAction SilentlyContinue
Get-Item .\ui_template.html -ErrorAction SilentlyContinue
Get-Content .\ui_template.html -TotalCount 80 -ErrorAction SilentlyContinue

docker version
docker compose version
docker compose config
docker ps
```

## 输出报告

```text
docs/development/task-reports/T00-workspace-baseline.md
```

## 测试

```powershell
docker compose config
git diff --check
git status --short
```

## 提交

```text
chore: record main2.0 workspace baseline
```

---

# 5. T01：初始化 `main2.0` 与任务报告机制

## 目标

建立：

```text
main2.0
docs/development/main2-roadmap.md
docs/development/task-reports/
```

## 执行

若 `main2.0` 不存在：

```powershell
git switch -c main2.0
git push -u origin main2.0
```

若已存在：

```powershell
git switch main2.0
git pull --ff-only origin main2.0
```

新增：

```text
docs/development/main2-roadmap.md
```

记录：

- 任务清单；
- 当前状态；
- 已完成任务；
- 风险；
- 测试记录；
- 检查点 Tag；
- 远端 commit。

## 测试

```powershell
git status --short
git log --oneline --decorate -n 8
```

## 提交

```text
chore: initialize main2.0 roadmap and task reporting
```

---

# 6. T02：显式图谱查询能力扫描与设计

## 目标

扫描现有能力，仅输出设计报告，不修改业务代码。

## 检查范围

```text
backend/package/yuxi/agents/toolkits/kbs/
backend/package/yuxi/agents/middlewares/
backend/package/yuxi/knowledge/graphs/
backend/package/yuxi/knowledge/implementations/milvus.py
backend/package/yuxi/knowledge/schemas.py
backend/test/
web/src/components/ToolCallingResult/
docs/agents/
```

## 搜索

```bash
rg -n "query_kb|query_nodes|query_seed_subgraph|query_and_rank_chunks_by_ppr|use_graph_retrieval|MilvusGraphService|SearchInputSchema|ToolCallRenderer|toolRegistry" .
```

## 输出

```text
docs/development/task-reports/T02-graph-query-design.md
```

## 测试

```powershell
git diff --check
```

## 提交

```text
docs(graph): define explicit graph query integration
```

---

# 7. T03：新增 `query_knowledge_graph`

## 新增

```text
backend/package/yuxi/agents/toolkits/kbs/graph_tools.py
```

## 输入模型

```python
class QueryKnowledgeGraphInput(BaseModel):
    kb_id: str
    keyword: str
    max_depth: int = 1
    max_nodes: int = 50
    exclude_chunk: bool = True
```

## 复用

```python
MilvusGraphService().query_nodes(...)
```

## 输出

```json
{
  "kb_id": "kb_xxx",
  "query": "供水管道漏损",
  "nodes": [],
  "edges": [],
  "retrieval_hints": {
    "graph_entity_ids": [],
    "chunk_ids": [],
    "file_ids": [],
    "keywords": []
  }
}
```

## 权限

必须满足：

```text
用户可访问
且
当前会话已启用
且
知识库类型支持图谱
```

## 测试

新增：

```text
backend/test/unit/toolkits/test_query_knowledge_graph.py
```

覆盖：

- 空关键词；
- 空知识库；
- 无权限；
- 会话未启用；
- 空图谱；
- 节点；
- 关系；
- 非 Milvus。

## 提交

```text
feat(graph): add explicit knowledge graph query tool
```

---

# 8. T04：扩展 `query_kb` 图谱种子增强检索

## 新增参数

```python
graph_entity_ids: list[str] | None = None
```

## 调用链

```text
graph_entity_ids
→ seed_weights
→ PPR
→ graph chunks
→ RRF
→ 文档片段
```

## 规则

- 图谱召回不作为强制过滤；
- 图谱为空时必须回退普通 RAG；
- 兼容旧调用；
- Dify 外部知识库不得进入 Milvus 图谱逻辑。

## 测试

新增：

```text
backend/test/unit/knowledge/test_milvus_graph_seed_retrieval.py
backend/test/integration/test_graph_to_kb_workflow.py
```

## 提交

```text
feat(graph): support graph-seeded knowledge retrieval
```

---

# 9. T05：图谱工具前端结果卡片

## 新增

```text
web/src/components/ToolCallingResult/renderers/KnowledgeGraphResult.vue
```

## 修改

```text
web/src/components/ToolCallingResult/toolRegistry.js
web/src/components/ToolCallingResult/ToolCallRenderer.vue
```

## UI

默认折叠：

```text
已查询知识图谱
12 个节点
18 条关系
已生成知识库增强检索提示
```

展开后显示：

- 节点；
- 关系；
- 图谱增强检索状态；
- 空状态；
- 错误状态；
- 加载状态。

禁止在会话卡片中渲染大型图谱画布。

## 测试

```powershell
docker compose exec web-dev pnpm lint
docker compose exec web-dev pnpm test
docker compose exec web-dev pnpm build
```

## 提交

```text
feat(web): render knowledge graph tool results
```

---

# 10. T06：图谱显式检索链路回归

## 测试

```powershell
docker compose exec api-dev pytest backend/test/unit/toolkits/test_query_knowledge_graph.py -q
docker compose exec api-dev pytest backend/test/unit/knowledge/test_milvus_graph_seed_retrieval.py -q
docker compose exec api-dev pytest backend/test/integration/test_graph_to_kb_workflow.py -q
```

## Tag

```powershell
git tag main2-checkpoint-graph
git push origin main2-checkpoint-graph
```

## 提交

```text
test(graph): complete graph-enhanced retrieval regression
```

---

# 11. T07：图谱抽取模型配置扫描与设计

## 扫描

```bash
rg -n "select_model|model_spec|graph_build_config|extractor_options|configure_graph_build|KnowledgeGraphSection|ModelSelectorComponent|EmbeddingModelSelector|createDatabase" .
```

## 确认

- `llm.py` 使用 `extractor_options.model_spec`；
- `MilvusGraphService.configure()` 是配置入口；
- 图谱页面已有后置配置；
- 新建知识库弹窗目前仅有嵌入模型；
- 图谱抽取模型配置必须复用现有 `graph_build_config`。

## 输出

```text
docs/development/task-reports/T07-graph-model-config-design.md
```

## 测试

```powershell
git diff --check
```

## 提交

```text
docs(graph): define graph extraction chat model configuration
```

---

# 12. T08：新建知识库支持图谱抽取 Chat 模型预配置

## 后端

修改：

```text
backend/server/routers/knowledge_router.py
backend/package/yuxi/knowledge/graphs/milvus_graph_service.py
backend/test/
```

创建知识库请求增加：

```python
graph_build_config: dict | None = Body(None)
```

结构：

```json
{
  "enabled": true,
  "extractor_type": "llm",
  "extractor_options": {
    "model_spec": "provider/model",
    "schema": "",
    "concurrency_count": 1,
    "model_params": {}
  }
}
```

处理：

```text
创建知识库
→ graph_build_config.enabled == true
→ 校验 KB 类型为 milvus
→ 调用 MilvusGraphService.configure(...)
→ 返回图谱配置状态
```

必须复用：

```python
MilvusGraphService.configure(...)
```

## 前端

修改：

```text
web/src/views/DataBaseView.vue
web/src/apis/knowledge_api.js
web/src/components/
```

新增：

```text
web/src/components/ChatModelSelector.vue
```

只加载：

```text
model_type=chat
```

新建知识库弹窗增加：

```text
知识图谱构建
[ ] 创建时配置知识图谱抽取
抽取器类型：LLM
图谱抽取 Chat 模型
Schema
并发队列数
模型参数 JSON
```

## 测试

新增：

```text
backend/test/unit/routers/test_knowledge_database_graph_config.py
```

前端：

```powershell
docker compose exec web-dev pnpm lint
docker compose exec web-dev pnpm test
docker compose exec web-dev pnpm build
```

## 提交

```text
feat(knowledge): configure graph extraction chat model during database creation
```

---

# 13. T09：图谱抽取模型配置交互测试

## 覆盖

```markdown
- [ ] 不启用图谱配置时可创建知识库
- [ ] 启用后必须选择 Chat 模型
- [ ] 嵌入模型和 Chat 模型互不混淆
- [ ] 非 Milvus 不显示图谱配置
- [ ] 创建后图谱页面显示已配置
- [ ] 后续可修改模型和 Schema
- [ ] 修改配置提示不会自动重算已有图谱
- [ ] 不保存 API Key
```

## 测试

```powershell
docker compose exec api-dev pytest backend/test/unit/routers/test_knowledge_database_graph_config.py -q
docker compose exec web-dev pnpm lint
docker compose exec web-dev pnpm test
docker compose exec web-dev pnpm build
```

## 提交

```text
test(knowledge): verify graph extraction model configuration flow
```

---

# 14. T10：知识库迁移格式设计与安全模型

## 新增文档

```text
docs/features/knowledge-base-portable-package.md
docs/development/task-reports/T10-kb-portable-package-design.md
```

## 定义

```text
Yuxi Portable Knowledge Package V1
*.yuxikb.zip
```

## 安全要求

- Zip Slip 防护；
- 文件数量上限；
- 单文件大小上限；
- 解压后总大小上限；
- manifest 版本校验；
- SHA-256；
- 临时目录；
- 导入失败回滚；
- 不恢复 API Key；
- 不恢复用户 ID；
- 不恢复共享权限；
- 不执行 ZIP 内脚本；
- 不允许覆盖已有知识库；
- 导入时创建新 kb_id。

## 测试

```powershell
git diff --check
```

## 提交

```text
docs(migration): define portable knowledge package format
```

---

# 15. T11：`.yuxikb.zip` 导出服务

## 新增

```text
backend/package/yuxi/knowledge/migration/
├── __init__.py
├── schemas.py
├── exporter.py
├── manifest.py
└── checksums.py
```

## API

```http
POST /api/knowledge/databases/{kb_id}/portable-export
GET  /api/knowledge/databases/{kb_id}/portable-export/{task_id}/download
```

导出必须使用异步任务。

## 导出内容

```text
manifest
database metadata
original files
parsed markdown
chunks
graph config
graph extraction results
entities
relationships
query params
checksums
```

## 禁止导出

```text
API Key
Provider credential
raw vectors
raw Milvus
raw Neo4j
PostgreSQL dump
user IDs
department IDs
share config
task status
absolute local paths
```

## 测试

```text
backend/test/unit/knowledge/migration/test_exporter.py
backend/test/integration/api/test_kb_portable_export.py
```

## 提交

```text
feat(migration): export portable knowledge packages
```

---

# 16. T12：`.yuxikb.zip` 导入预检与恢复服务

## 新增

```text
backend/package/yuxi/knowledge/migration/importer.py
backend/package/yuxi/knowledge/migration/validator.py
```

## API

```http
POST /api/knowledge/portable-import/preflight
POST /api/knowledge/portable-import
GET  /api/knowledge/portable-import/{task_id}/status
```

## 流程

```text
上传
→ 安全解压
→ 校验 manifest
→ 校验 SHA-256
→ 校验版本
→ 返回预检报告
→ 用户确认
→ 创建新知识库
→ 复制 MinIO
→ 写入 Chunk
→ 重建 Milvus 文档向量
→ 写入 Neo4j 实体关系
→ 重建图谱向量
→ 返回导入报告
```

## 预检输出

```json
{
  "package_version": "1",
  "database_name": "示例知识库",
  "files": 12,
  "chunks": 428,
  "entities": 982,
  "relationships": 1304,
  "requires_embedding_model": true,
  "requires_graph_chat_model": false,
  "warnings": []
}
```

## 默认行为

```text
复用导出的实体与关系
不重新调用 LLM 抽取
重建向量
```

## 导入失败必须回滚

```text
清理临时目录
删除新 kb_id
清理 MinIO
清理 Chunk
清理 Neo4j
清理 Milvus
输出失败报告
```

## 测试

```text
backend/test/unit/knowledge/migration/test_importer.py
backend/test/unit/knowledge/migration/test_validator.py
backend/test/integration/api/test_kb_portable_import.py
```

## 提交

```text
feat(migration): import portable knowledge packages with index rebuild
```

---

# 17. T13：知识库迁移前端

## 修改

```text
web/src/views/DataBaseView.vue
web/src/views/DataBaseInfoView.vue
web/src/apis/knowledge_api.js
web/src/components/
```

## 新建知识库弹窗

增加：

```text
新建空白知识库
从迁移包导入
```

## 导入流程 UI

```text
上传 .yuxikb.zip
→ 预检
→ 文件数
→ Chunk 数
→ 实体数
→ 关系数
→ 新知识库名称
→ 嵌入模型
→ 图谱抽取 Chat 模型
→ 开始导入
→ 进度
→ 导入报告
```

## 知识库详情页

增加：

```text
导出迁移包
```

固定提示：

```text
导出的迁移包不包含模型 API Key、用户账号和共享权限。
目标终端将重新生成向量索引。
```

## 测试

```powershell
docker compose exec web-dev pnpm lint
docker compose exec web-dev pnpm test
docker compose exec web-dev pnpm build
```

## 提交

```text
feat(web): add portable knowledge package import and export flows
```

---

# 18. T14：知识库迁移端到端测试

## 场景

```text
终端 A
→ 创建知识库
→ 上传文档
→ 解析
→ 入库
→ 图谱抽取
→ 导出 .yuxikb.zip

隔离测试环境
→ 上传 .yuxikb.zip
→ 预检
→ 选择模型
→ 导入
→ 重建索引
→ 查询文档
→ 查询图谱
→ 验证实体关系
```

## 覆盖

```markdown
- [ ] 原始文件
- [ ] Markdown
- [ ] Chunk
- [ ] 查询
- [ ] 图谱节点
- [ ] 图谱关系
- [ ] 图谱增强检索
- [ ] 无 API Key
- [ ] 无原用户 ID
- [ ] 无原共享权限
- [ ] 重建向量
- [ ] Zip Slip
- [ ] 校验和错误
- [ ] 版本不兼容
- [ ] 中途失败回滚
```

## Tag

```powershell
git tag main2-checkpoint-migration
git push origin main2-checkpoint-migration
```

## 提交

```text
test(migration): verify portable knowledge package round trip
```

---

# 19. T15：空间数据模块扫描与设计

## 扫描

```bash
rg -n "spatial|gis|map|geojson|shapefile|layer|postgis|maplibre|leaflet|geometry" .
```

## 输出

```text
docs/development/task-reports/T15-spatial-design.md
```

## 确认架构

```text
PostGIS
MinIO
GeoPandas
Shapely
PyProj
MapLibre GL JS
```

## 提交

```text
docs(spatial): define spatial module architecture
```

---

# 20. T16：PostGIS 空间图层基础模型

## 新增表

```text
spatial_layers
spatial_features
spatial_layer_compositions
spatial_layer_composition_items
```

## 要求

- PostGIS extension；
- EPSG:4326；
- bbox；
- geometry type；
- feature count；
- properties JSON；
- owner；
- 权限隔离。

## 测试

- migration；
- geometry；
- bbox；
- owner；
- 权限。

## 提交

```text
feat(spatial): add postgis spatial layer persistence
```

---

# 21. T17：空间数据上传与图层管理

## 支持格式

```text
.geojson
.json
.zip
.gpkg
```

`.zip` 用于 Shapefile 文件组。

## 流程

```text
上传
→ MinIO
→ 安全解压
→ CRS
→ EPSG:4326
→ geometry repair
→ PostGIS
```

## 安全

- Zip Slip；
- 单文件大小；
- 解压总大小；
- 文件数量；
- Shapefile 完整性；
- 无 CRS 拒绝；
- 权限隔离。

## 测试

- GeoJSON；
- Shapefile；
- GPKG；
- Zip Slip；
- 无 CRS；
- 不完整 Shapefile；
- 权限。

## 提交

```text
feat(spatial): support spatial import and layer management
```

---

# 22. T18：图层叠加与派生空间分析

## 图层组合

支持：

```text
顺序
显隐
透明度
样式覆盖
```

## 派生分析

```text
intersection
union
difference
```

结果必须写入新图层，不覆盖源图层。

## 测试

- 创建组合；
- 图层顺序；
- 显隐；
- 透明度；
- intersection；
- union；
- difference；
- 源数据不变。

## 提交

```text
feat(spatial): add layer compositions and derived analysis
```

---

# 23. T19：空间智能体工具

## 新增工具

```text
list_spatial_layers
query_spatial_features
show_spatial_map
```

## ToolMessage

只返回：

```text
URL
图层
bounds
样式
popup 字段
```

禁止返回大体积 GeoJSON。

## 测试

- 权限；
- 空图层；
- bbox；
- 大图层保护；
- composition；
- URL；
- ToolMessage 大小。

## 提交

```text
feat(agent): add spatial query and map tools
```

---

# 24. T20：会话内地图可视化

## 技术

```text
MapLibre GL JS
```

## 功能

- 多图层；
- 图层显隐；
- 图层顺序；
- 透明度；
- 缩放；
- 平移；
- 自动 bounds；
- 点击要素；
- Popup；
- 属性抽屉；
- 空状态；
- Loading；
- Error；
- 超限提示。

## Tag

```powershell
git tag main2-checkpoint-spatial
git push origin main2-checkpoint-spatial
```

## 提交

```text
feat(web): render interactive spatial maps in chat
```

---

# 25. T21：UI 模板分析与设计 Token

## 模板

```text
D:\learn\pro\yuxi\Yuxi-sync-upstream-latest\ui_template.hml
```

## 检查

```powershell
Get-Item .\ui_template.hml
Get-Content .\ui_template.hml -TotalCount 80
```

若不存在：

```powershell
Get-Item .\ui_template.html -ErrorAction SilentlyContinue
```

## 新增

```text
web/src/assets/css/tokens.css
web/src/assets/css/base.css
web/src/assets/css/layout.css
```

## Token

至少统一：

```css
--color-primary
--color-primary-hover
--color-primary-light
--color-bg-page
--color-bg-sidebar
--color-bg-card
--color-text-primary
--color-text-secondary
--color-border
--color-success
--color-warning
--color-danger
--radius-sm
--radius-md
--radius-lg
--shadow-card
--sidebar-width
--sidebar-collapsed-width
--header-height
```

## 禁止复制

```text
Tailwind CDN
静态假数据
静态路由
静态事件处理
与项目架构不符的页面
```

## 提交

```text
refactor(web): establish unified design tokens
```

---

# 26. T22：登录页、首页与整体布局优化

## 真实导航

```text
新建对话
工作区
智能体扩展
智能体管理
数据总览
空间数据
```

## 删除不符合架构的页面入口

```text
智能管网诊断
拓扑闭环校验
运行效能核算
```

## 登录页

- 居右布局；
- 左侧视觉区域；
- 固定右侧登录面板；
- Loading；
- Error；
- 密码显示；
- 记住状态；
- 风格与内页一致。

## 首页

展示：

```text
智能体
知识库
图谱增强检索
知识库迁移
空间数据
MCP
Skills
```

## 提交

```text
refactor(web): redesign login home and app layout
```

---

# 27. T23：业务页面统一与品牌清理

## 检查

```text
AgentView
WorkspaceView
DashboardView
ModelManageView
ExtensionsView
DataBaseView
DataBaseInfoView
SettingsModal
TaskCenterDrawer
ToolCallingResult
```

## 删除

```text
原作者 GitHub Star
原作者 GitHub 入口
原作者文档推广
原作者 Logo
原作者头像
原作者专属文案
```

## 保留

```text
LICENSE
MIT License
第三方依赖声明
必要致谢
```

## 统一

- 标题；
- Button；
- Input；
- Card；
- Table；
- Tabs；
- Drawer；
- Modal；
- Empty；
- Loading；
- Error；
- Toast；
- Tooltip；
- 二次确认；
- Breadcrumb；
- 可返回性。

## Tag

```powershell
git tag main2-checkpoint-ui
git push origin main2-checkpoint-ui
```

## 提交

```text
refactor(web): unify product pages and remove upstream branding
```

---

# 28. T24：文档重写与目录整理

## 更新

```text
README.md
README.en.md
ARCHITECTURE.md
AGENTS.md
CLAUDE.md
docs/
```

## 必须记录

- Milvus + Neo4j；
- `query_knowledge_graph`；
- `query_kb(graph_entity_ids=...)`；
- 图谱抽取 Chat 模型；
- `.yuxikb.zip`；
- 导入时重建索引；
- PostGIS；
- 图层叠加；
- 会话地图；
- UI 模板；
- Docker；
- Windows 安装包；
- Git 检查点策略。

## 旧文档

移动到：

```text
docs/archive/
```

禁止直接删除仍可能需要追溯的旧文档。

## Tag

```powershell
git tag main2-checkpoint-docs
git push origin main2-checkpoint-docs
```

## 提交

```text
docs: rewrite main2.0 architecture and operations guides
```

---

# 29. T25：Docker 全量回归

## 执行

```powershell
docker compose config
docker compose up -d --build
docker ps
docker compose logs --tail 200

docker compose exec api-dev pytest backend/test/unit -q
docker compose exec api-dev pytest backend/test/integration -q

docker compose exec web-dev pnpm lint
docker compose exec web-dev pnpm test
docker compose exec web-dev pnpm build
```

## 验收

```markdown
- [ ] 登录
- [ ] 权限
- [ ] 智能体
- [ ] 知识库
- [ ] 图谱构建 Chat 模型
- [ ] query_knowledge_graph
- [ ] graph-seeded query_kb
- [ ] 迁移导出
- [ ] 迁移导入
- [ ] 重建索引
- [ ] PostGIS
- [ ] 图层叠加
- [ ] 会话地图
- [ ] UI
- [ ] LICENSE
```

## 提交

```text
test: complete main2.0 docker regression
```

---

# 30. T26：Windows `.exe` 启动器与安装包

## 产物

```text
Yuxi-Desktop-Setup.exe
```

## 新增目录

```text
packaging/windows/
├── launcher/
│   ├── main.py
│   ├── docker_manager.py
│   ├── healthcheck.py
│   ├── config_manager.py
│   └── requirements.txt
├── bundle/
│   ├── docker-compose.yml
│   ├── .env.template
│   └── images/
├── installer/
│   └── yuxi.iss
├── scripts/
│   ├── build_launcher.ps1
│   ├── export_images.ps1
│   ├── build_installer.ps1
│   └── test_installer.ps1
└── README.md
```

## 功能

- Docker Desktop；
- WSL2；
- Docker daemon；
- Compose；
- 配置初始化；
- 端口；
- 镜像；
- 启动；
- 停止；
- 重启；
- 日志；
- 打开 Web；
- 健康检查；
- 用户数据保护。

## Tag

```powershell
git tag main2-checkpoint-windows
git push origin main2-checkpoint-windows
```

## 提交

```text
build(windows): add docker-based launcher and installer
```

---

# 31. T27：最终验收、Tag 与发布报告

## 检查

```powershell
git status --short
git log --oneline --decorate --all -n 100
git remote -v
```

## 输出

```text
docs/development/task-reports/T27-final-delivery.md
```

## 最终 Tag

```powershell
git tag main2.0-release-candidate
git push origin main2.0-release-candidate
git push origin main2.0
```

---

# 32. Claude 单任务统一执行 Prompt

每次只执行一个任务。替换 `<TASK_ID>` 与 `<TASK_SLUG>`。

```markdown
请在本地项目 `D:\learn\pro\yuxi\Yuxi-sync-upstream-latest` 中执行任务 `<TASK_ID>`。

任务分支：

`feat/main2-<TASK_ID>-<TASK_SLUG>`

必须遵守：

1. 只执行 `<TASK_ID>`，禁止提前执行后续任务。
2. 开始前执行：
   - `git fetch origin --prune`
   - `git status --short`
   - `git branch --show-current`
   - `git remote -v`
   - `git remote get-url origin`
   - `git log --oneline --decorate -n 12`
3. 若存在未提交修改：
   - 停止；
   - 列出文件；
   - 不覆盖；
   - 不 reset；
   - 不 stash。
4. 检查 origin：
   - 禁止直接推送 `xerrors/Yuxi`；
   - 只允许推送用户 fork。
5. 从 `origin/main2.0` 创建独立任务分支。
6. 修改前输出本任务计划。
7. 仅修改本任务范围。
8. 运行当前任务相关测试。
9. 测试失败时先修复，不进入后续任务。
10. 测试通过后：
    - 提交代码；
    - 新增 `docs/development/task-reports/<TASK_ID>-<TASK_SLUG>.md`；
    - 提交任务报告；
    - 推送任务分支；
    - 合并到 `main2.0`；
    - 推送 `main2.0`；
    - 输出远端 commit SHA。
11. 测试失败且无法修复时：
    - 不合并 `main2.0`；
    - 可推送任务分支保留现场；
    - 报告标记 WIP。
12. 禁止恢复 LightRAG。
13. 禁止删除 LICENSE。
14. 禁止保存、导出或提交 API Key。
15. 图谱构建配置使用 Chat 模型 `model_spec`，不得绑定聊天智能体实例。
16. 知识库迁移使用 `.yuxikb.zip` 应用层逻辑包，不得复制底层数据库文件。
17. UI 任务读取：
    `D:\learn\pro\yuxi\Yuxi-sync-upstream-latest\ui_template.hml`
    作为视觉参考，不得直接覆盖 Vue 项目。
18. 最终输出：
    - 分支；
    - 修改文件；
    - 新增文件；
    - 删除文件；
    - 测试命令；
    - 测试结果；
    - 风险；
    - 已知限制；
    - 代码 commit；
    - 报告 commit；
    - main2.0 commit；
    - 远端分支；
    - 是否满足验收标准。
```

---

# 33. 推荐执行顺序

```text
T00
T01
T02
T03
T04
T05
T06
T07
T08
T09
T10
T11
T12
T13
T14
T15
T16
T17
T18
T19
T20
T21
T22
T23
T24
T25
T26
T27
```
