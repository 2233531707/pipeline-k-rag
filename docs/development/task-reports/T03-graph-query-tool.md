# T03 任务报告 — 新增 query_knowledge_graph 工具

## 目标

新增显式知识图谱查询工具 `query_knowledge_graph`，允许智能体直接查询知识图谱的节点和关系，并返回增强检索提示信息。

## 分支

`feat/main2-t03-graph-query-tool`（从 `main2.0` 创建）

## 修改文件

| 文件 | 说明 |
|---|---|
| `backend/package/yuxi/agents/toolkits/kbs/tools.py` | 在 `get_common_kb_tools()` 中注册 `query_knowledge_graph`，工具数从 5 增至 6 |

## 新增文件

| 文件 | 说明 |
|---|---|
| `backend/package/yuxi/agents/toolkits/kbs/graph_tools.py` | `query_knowledge_graph` 工具实现 + `_extract_retrieval_hints` 辅助函数 |
| `backend/test/unit/toolkits/test_query_knowledge_graph.py` | 18 个单元测试覆盖 |

## 删除文件

无

## 设计要点

### 输入模型

```python
class QueryKnowledgeGraphInput(BaseModel):
    kb_id: str           # 知识库资源 ID
    keyword: str         # 图谱查询关键词
    max_depth: int = 1   # 关系跳数 (0-5)
    max_nodes: int = 50  # 最大节点数 (1-200)
    exclude_chunk: bool = True  # 默认排除 Chunk 节点
```

### 输出结构

```json
{
  "kb_id": "kb_xxx",
  "query": "供水管道漏损",
  "nodes": [...],
  "edges": [...],
  "retrieval_hints": {
    "graph_entity_ids": ["ent_1"],
    "chunk_ids": ["chunk_a"],
    "file_ids": ["file_x"],
    "keywords": ["供水", "管道", "漏损"]
  }
}
```

### 权限检查

- 复用 `_resolve_visible_knowledge_bases_for_query()` 进行会话可见性检查
- 新增 `kb_type == "milvus"` 检查：非 Milvus 知识库返回错误

### 复用

- `MilvusGraphService.query_nodes()` — 已有的 Neo4j 图谱查询方法
- `@tool` 装饰器 + `get_common_kb_tools()` — 标准工具注册流程

## 测试命令

```bash
docker exec yuxi-sync-api sh -c "cd /app && uv run --no-sync --no-dev pytest test/unit/toolkits/test_query_knowledge_graph.py -q"
```

## 测试结果

18 passed ✅

### 覆盖场景

| 测试 | 状态 |
|---|---|
| 默认参数值 | ✅ |
| 自定义参数值 | ✅ |
| 空关键词（schema 层面允许） | ✅ |
| 空节点/边提取 hints | ✅ |
| 从节点提取 entity_ids | ✅ |
| 从 Chunk 节点提取 chunk_ids/file_ids | ✅ |
| 从边提取 chunk_ids | ✅ |
| hints 去重 | ✅ |
| keyword 分词 | ✅ |
| 空 kb_id 返回错误 | ✅ |
| 空 keyword 返回错误 | ✅ |
| 无可访问知识库 | ✅ |
| kb 不在可见列表 | ✅ |
| 非 Milvus 知识库拒绝 | ✅ |
| 空图谱结果 | ✅ |
| 有节点和边的结果 | ✅ |
| 图谱服务异常 | ✅ |
| 会话未启用知识库 | ✅ |

## 风险

- `retrieval_hints` 基于简单规则，不保证线索质量；后续可在 T04 中由实际检索验证
- `graph_entity_ids` 上限 30、`chunk_ids` 上限 30，可能截断大型图谱

## 已知限制

- 依赖 Neo4j 连接；若 Neo4j 不可用，返回错误信息而非崩溃
- 仅支持 Milvus 类型知识库

## 提交

- 代码 commit：待提交
- 报告 commit：待提交（与代码同一提交）
- main2.0 commit：待合并推送

## 远端

- 任务分支：待推送
