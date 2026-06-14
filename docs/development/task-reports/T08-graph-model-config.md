# T08 任务报告 — 新建知识库支持图谱抽取 Chat 模型预配置

## 目标

在新建知识库时支持前瞻配置图谱抽取 Chat 模型，复用 `MilvusGraphService.configure()` 和 `graph_build_config` 结构。

## 分支

`feat/main2-t08-graph-model-config`

## 修改文件

| 文件 | 说明 |
|---|---|
| `backend/server/routers/knowledge_router.py` | `create_database` 新增 `graph_build_config` 参数，创建时调用 `MilvusGraphService.configure()` |
| `web/src/views/DataBaseView.vue` | 添加图谱构建预配置区块（仅在 kb_type==milvus 时显示），`buildRequestData` 中构建 `graph_build_config` |
| `web/src/components/ChatModelSelector.vue` | 新建，复用 `EmbeddingModelSelector` 模式，只加载 `model_type=chat` |

## 新增文件

| 文件 | 说明 |
|---|---|
| `web/src/components/ChatModelSelector.vue` | Chat 模型选择器组件 |

## 删除文件

无

## 后端设计

### create_database 新增参数

```python
graph_build_config: dict | None = Body(None)
```

### 处理流程

```
graph_build_config.enabled == true
  → 校验 kb_type == "milvus"
  → 校验 extractor_type in ("llm",)
  → 注入 additional_params[graph_build_config]
  → knowledge_base.create_database(...)
  → MilvusGraphService().configure(kb_id, extractor_type, extractor_options, created_by)
  → 返回 database_info + graph_build_config 状态
```

- `graph_build_config.enabled=false` 或未提供时，跳过图谱预配置
- 预配置失败不阻断知识库创建（仅记录错误日志）
- 复用 `MilvusGraphService.configure()` 完成校验和持久化

### 前端图谱构建区块

在 DataBaseView.vue 新建知识库弹窗中，仅在 `kb_type == "milvus"` 时显示：

```
知识图谱构建
  [开关] 创建时配置知识图谱抽取
  展开后：
    抽取器类型: LLM (固定)
    图谱抽取 Chat 模型: ChatModelSelector
    Schema: textarea
    并发队列数: 1-1000
    模型参数 JSON: textarea
```

### ChatModelSelector

- 复用 `EmbeddingModelSelector` 模板结构
- `getV2Models('chat')` — 只加载 `model_type=chat`
- 支持 v-model 双向绑定、状态图标、placeholder

## 测试命令

```bash
docker exec web-dev sh -c "cd /app && pnpm lint"
docker exec web-dev sh -c "cd /app && pnpm build"
```

## 测试结果

- pnpm lint: ✅ 通过
- pnpm build: ✅ 通过 (39.74s)
- 后端单元测试：待 T09 执行

## 风险

- `GRAPH_CONFIG_KEY` 在 `create_database` 中直接使用，需确保已从 `milvus_graph_service` 导入
- 前端 `model_params_json` 解析错误时显示 warning 但继续创建

## 已知限制

- 新建知识库时不校验 Chat 模型的有效性（仅在调用 `configure()` 时通过 `GraphExtractorFactory.create()` 间接校验）
- Schema 为自由文本，无法提供模板或自动补全

## 提交

- 代码 commit：`ed6708a1` — feat(knowledge): configure graph extraction chat model during database creation

## 远端

- 任务分支：`feat/main2-t08-graph-model-config`（待推送）
