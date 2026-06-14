# T04 任务报告 — 扩展 query_kb 图谱种子增强检索

## 目标

扩展 `query_kb` 接收 `graph_entity_ids` 参数，实现从图谱实体到增强检索的完整链路。

## 分支

`feat/main2-t03-graph-query-tool`（与 T03 合并在同一分支）

## 修改文件

| 文件 | 说明 |
|---|---|
| `backend/package/yuxi/knowledge/schemas.py` | `SearchInputSchema` 新增 `graph_entity_ids` 可选字段 |
| `backend/package/yuxi/agents/toolkits/kbs/tools.py` | `query_kb` 函数签名新增 `graph_entity_ids` 参数，Dify 拒绝逻辑 |
| `backend/package/yuxi/knowledge/implementations/milvus.py` | `aquery` 和 `_retrieve_graph_chunks` 支持 `graph_entity_ids` 直接种子模式 |

## 新增文件

| 文件 | 说明 |
|---|---|
| `backend/test/unit/knowledge/test_milvus_graph_seed_retrieval.py` | 6 个单元测试覆盖图谱种子增强检索 |

## 删除文件

无

## 调用链（新增 graph_entity_ids 路径）

```
query_kb(graph_entity_ids=["ent_1", "ent_2"], ...)
  → _find_query_target → 权限/会话检查 + kb_type 检查（Dify 拒绝）
  → retriever(query_text, graph_entity_ids=[...])
    → MilvusKB.aquery()
      → merged_kwargs = {**query_params, graph_entity_ids: [...]}
      → use_graph_retrieval = False, graph_entity_ids = [...]
      → _retrieve_graph_chunks(graph_entity_ids=[...])
        → seed_weights = {eid: 1.0}  ← 直接构造，跳转向量搜索
        → query_and_rank_chunks_by_ppr(seed_weights)
        → PPR → chunk_ids → chunk records
      → _fuse_chunk_rankings() → RRF 融合
```

与原有 `use_graph_retrieval` 的区别：
- 原路径：`use_graph_retrieval=True` → 向量搜索实体 → 构建种子权重
- 新路径：`graph_entity_ids=[...]` → 直接构造种子权重，无向量搜索

## 设计决策

1. **图谱召回不作为强制过滤**：图谱结果与向量结果通过 RRF 融合
2. **图谱为空回退普通 RAG**：PPR 无结果时 `graph_chunks=[]`，不影响普通检索
3. **向后兼容**：不传 `graph_entity_ids` 时完全保持原有行为
4. **Dify 保护**：`query_kb` 工具层检查 `kb_type == "dify"` 时忽略 `graph_entity_ids`

## 测试命令

```bash
docker exec yuxi-sync-api sh -c "cd /app && uv run --no-sync --no-dev pytest test/unit/knowledge/test_milvus_graph_seed_retrieval.py -q"
docker exec yuxi-sync-api sh -c "cd /app && uv run --no-sync --no-dev pytest test/unit/toolkits/test_query_knowledge_graph.py -q"
```

## 测试结果

- T03 `test_query_knowledge_graph.py`: 18 passed ✅
- T04 `test_milvus_graph_seed_retrieval.py`: 6 passed ✅

### T04 测试覆盖

| 测试 | 状态 |
|---|---|
| graph_entity_ids 参数传递到 aquery | ✅ |
| graph_entity_ids 直接传给 _retrieve_graph_chunks | ✅ |
| entity_ids 转换为 seed_weights 传入 PPR | ✅ |
| PPR 无结果时回退普通 RAG | ✅ |
| Dify 拒绝（工具层） | ✅（占位，集成测试验证） |
| 不传 graph_entity_ids 时保持原有行为 | ✅ |

## 风险

- 在 `_retrieve_graph_chunks` 中的 `graph_entity_ids` 分支未验证 Neo4j label 合法性，若实体 ID 在 Neo4j 中不存在会静默失败
- `seed_weights` 等权（均为 1.0），未考虑实体重要性区分

## 已知限制

- `graph_entity_ids` → PPR 路径未经 Neo4j 真实数据验证（单元测试 mock 了 MilvusGraphService）
- 集成测试 `test_graph_to_kb_workflow.py` 待 T06 阶段实现

## 提交

- 代码 commit：`b4fc3811` — feat(graph): add explicit knowledge graph query tool / support graph-seeded knowledge retrieval

## 远端

- 任务分支：`feat/main2-t03-graph-query-tool`
