# T02 任务报告 — 显式图谱查询能力扫描与设计

## 目标

扫描现有知识图谱查询能力，输出设计报告，不修改业务代码。

## 分支

`main2.0`

## 修改文件

无

## 新增文件

| 文件 | 说明 |
|---|---|
| `docs/development/task-reports/T02-graph-query-design.md` | 本报告 |

## 删除文件

无

## 扫描结果

### 1. 核心架构

```
MilvusGraphService (backend/package/yuxi/knowledge/graphs/milvus_graph_service.py)
├── query_nodes(keyword, max_depth, max_nodes, exclude_chunk) → {nodes, edges}
├── query_seed_subgraph(kb_id, entity_ids, max_nodes) → {nodes, edges}
├── query_and_rank_chunks_by_ppr(kb_id, seed_weights, ...) → [(chunk_id, score)]
├── rank_chunks_by_ppr(subgraph, seed_weights, top_k, damping) → [(chunk_id, score)]  (static)
├── get_labels(kb_id) → [labels]
├── get_stats(kb_id) → {total_nodes, total_edges, entity_types}
└── configure(kb_id, extractor_type, extractor_options) → config
```

**关键发现：**

- `query_nodes` 是已有的显式图谱节点查询方法，支持关键词搜索、深度控制、节点数限制和 Chunk 节点过滤
- `query_seed_subgraph` 基于实体 ID 展开种子子图（用于 PPR 链路）
- `query_and_rank_chunks_by_ppr` 是图谱增强检索的核心：种子权重 → PPR → Chunk 排序

### 2. 当前检索链路（`query_kb` → 图谱增强）

```
query_kb (tools.py:196)
  → MilvusKnowledgeBase.query() (milvus.py:855+)
    → 向量/关键词/混合搜索
    → 若 use_graph_retrieval:
      → _retrieve_graph_chunks() (milvus.py:1020)
        → MilvusGraphVectorStore.search_entities()     # 向量检索实体
        → MilvusGraphVectorStore.search_triples()      # 向量检索三元组
        → _build_graph_seed_weights()                  # 构建种子权重
        → MilvusGraphService.query_and_rank_chunks_by_ppr()  # PPR 排序
        → _fuse_chunk_rankings() (RRF)                  # 融合图谱与向量结果
```

**关键发现：**

- `use_graph_retrieval` 仅在检索时自动触发，无显式图谱查询工具
- 图谱种子权重来源：实体向量命中 + 三元组向量命中 + base_chunks 关联的 ent_ids
- PPR 使用 python-igraph 计算
- RRF (k=60) 融合图谱与普通检索结果

### 3. 现有工具列表

| 工具 | 位置 | 功能 |
|---|---|---|
| `list_kbs` | kbs/tools.py:33 | 列出可访问知识库 |
| `get_mindmap` | kbs/tools.py:86 | 获取思维导图 |
| `query_kb` | kbs/tools.py:196 | 语义检索（可选图谱增强） |
| `find_kb_document` | kbs/tools.py:292 | 文档内关键词定位 |
| `open_kb_document` | kbs/tools.py:238 | 按窗口打开文档 |

**缺失：没有显式的图谱查询工具**，用户无法主动查询知识图谱的节点和关系。

### 4. 现有 API 端点

| 端点 | 路由 | 功能 |
|---|---|---|
| GET `/graph/list` | graph_router.py:24 | 列出 Milvus 知识库 |
| GET `/graph/subgraph` | graph_router.py:50 | 查询子图（节点+边） |
| GET `/graph/labels` | graph_router.py:78 | 获取图谱标签 |
| GET `/graph/stats` | graph_router.py:94 | 图谱统计 |

**关键发现：** `/graph/subgraph` 已直接调用 `query_nodes()`，但仅作为 Web API，未暴露为 Agent 工具。

### 5. 前端渲染

| 文件 | 功能 |
|---|---|
| `ToolCallRenderer.vue` | 工具结果分发（当前无 `query_knowledge_graph` 注册） |
| `toolRegistry.js` | 工具注册和图标映射 |
| `QueryKbTool.vue` | `query_kb` 渲染（已包含图谱结果卡片内嵌） |
| `GetMindmapTool.vue` | `get_mindmap` 渲染 |
| `BaseToolCall.vue` | 基础工具调用卡片 |

### 6. 权限检查模式

现有 `_find_query_target()` (tools.py:175) 实现：
```python
visible_kb_ids = {str(kb.get("kb_id")).strip() for kb in visible_kbs}
if normalized_kb_id not in visible_kb_ids:
    error
```

新工具 T03 需要复用此权限检查模式，同时增加知识库类型检查（仅 `milvus` 支持图谱）。

## 设计决策

### T03: `query_knowledge_graph` 工具

**输入模型：**
```python
class QueryKnowledgeGraphInput(BaseModel):
    kb_id: str = Field(description="知识库资源 ID")
    keyword: str = Field(description="图谱查询关键词，支持实体名、概念等")
    max_depth: int = Field(default=1, description="查询深度，0=仅匹配节点")
    max_nodes: int = Field(default=50, description="最大返回节点数")
    exclude_chunk: bool = Field(default=True, description="是否排除Chunk节点")
```

**实现方案：**

1. **新建文件** `backend/package/yuxi/agents/toolkits/kbs/graph_tools.py`
2. 复用 `MilvusGraphService.query_nodes()` — 已有方法，无需修改
3. 返回结构（除了 `nodes`/`edges`，额外生成 `retrieval_hints`）：

```json
{
  "kb_id": "kb_xxx",
  "query": "供水管道漏损",
  "nodes": [...],
  "edges": [...],
  "retrieval_hints": {
    "graph_entity_ids": ["entity_1", "entity_2"],
    "chunk_ids": ["chunk_a", "chunk_b"],
    "file_ids": ["file_x"],
    "keywords": ["供水", "管道", "漏损"]
  }
}
```

4. `retrieval_hints` 生成逻辑：
   - `graph_entity_ids`: 从 nodes 提取非 Chunk 节点的 entity_id
   - `chunk_ids`: 从 nodes 提取 Chunk 类型节点的 chunk_id
   - `file_ids`: 从 Chunk 节点属性中提取 file_id
   - `keywords`: 从 keyword 分词 + 实体名中提取

5. **权限检查**：复用 `_resolve_visible_knowledge_bases_for_query()` + 新增 `kb_type == "milvus"` 检查

6. **注册工具**：在 `get_common_kb_tools()` 中增加 `query_knowledge_graph`

### T04: `query_kb` 扩展 `graph_entity_ids` 参数

**修改 `SearchInputSchema`**：增加可选参数
```python
graph_entity_ids: list[str] | None = Field(default=None, description="图谱实体ID列表，作为种子增强检索")
```

**修改 `query_kb` 函数**：将 `graph_entity_ids` 传递到检索参数中

**修改 `MilvusKnowledgeBase.query()`**：
- 若 `graph_entity_ids` 不为空，直接构建种子权重 → PPR → 图谱 Chunks → RRF
- 若 `graph_entity_ids` 为空，保持现有 `use_graph_retrieval` 自动流程
- 图谱为空时回退普通 RAG

### T05: 前端 `KnowledgeGraphResult` 卡片

**新建** `web/src/components/ToolCallingResult/renderers/KnowledgeGraphResult.vue`：
- 默认折叠：显示节点数、关系数、增强检索提示
- 展开：节点表格、关系列表、检索提示
- 空状态、错误状态、加载状态

**修改** `ToolCallRenderer.vue`：注册 `query_knowledge_graph → KnowledgeGraphResult`
**修改** `toolRegistry.js`：添加 `query_knowledge_graph → Network` 图标映射

### T06: 回归测试

- 运行 T03、T04 的单元测试和集成测试
- 创建检查点 Tag `main2-checkpoint-graph`

## 测试命令

```bash
git diff --check
```

## 测试结果

- `git diff --check` — ✅ 通过（无代码修改）

## 风险

1. `query_nodes` 返回时需要额外的数据转换来提取 `retrieval_hints`
2. `graph_entity_ids` 流程与现有 `use_graph_retrieval` 自动流程可能产生重复计算，需设计清晰的分支逻辑
3. 前端 `KnowledgeGraphResult` 需要与现有 `BaseToolCall` 适配

## 已知限制

- `query_nodes` 依赖 Neo4j 连接，若 Neo4j 不可用需优雅降级
- PPR 计算依赖 `python-igraph`，当前已作为可选依赖处理

## 提交

本报告待提交。（T02 仅输出设计，不修改代码。）

## 远端

- 任务分支：`main2.0`（待提交推送）

## 验收标准

| 检查项 | 状态 |
|---|---|
| `query_nodes` 方法确认 | ✅ 已存在 |
| `query_seed_subgraph` 方法确认 | ✅ 已存在 |
| `query_and_rank_chunks_by_ppr` 确认 | ✅ 已存在 |
| `use_graph_retrieval` 集成点确认 | ✅ 已存在 |
| ToolCallRenderer 模式确认 | ✅ 已存在 |
| toolRegistry 模式确认 | ✅ 已存在 |
| 权限检查模式确认 | ✅ 已存在 |
| 设计文档完整 | ✅ |
