# T07 任务报告 — 图谱抽取模型配置扫描与设计

## 目标

扫描图谱抽取模型配置的现有能力，输出设计报告。确认后端 `configure()` 入口、前端新建知识库弹窗现状、`graph_build_config` 复用路径。

## 分支

`main2.0`

## 修改文件

无（仅设计文档）

## 新增文件

| 文件 | 说明 |
|---|---|
| `docs/development/task-reports/T07-graph-model-config-design.md` | 本报告 |

## 删除文件

无

## 扫描结果

### 1. 图谱抽取后端链路

```
create_database (knowledge_router.py:146)
  → additional_params → kb_class.normalize_additional_params()

MilvusGraphService.configure() (milvus_graph_service.py:117)
  输入: kb_id, extractor_type, extractor_options, created_by
  存储: additional_params.graph_build_config = {
    locked: true,
    extractor_type: "llm",
    extractor_options: { model_spec, schema, concurrency_count, model_params }
  }
  校验: GraphExtractorFactory.create() → LLMGraphExtractor.validate_options()

LLMGraphExtractor.extract() (llm.py:48)
  → select_model(model_spec=self.options["model_spec"], timeout=60, model_params=...)
```

**确认点：**
- ✅ `llm.py` 使用 `extractor_options.model_spec`，通过 `select_model()` 创建 Chat 模型实例
- ✅ `MilvusGraphService.configure()` 是唯一的配置入口
- ✅ 配置持久化在 `additional_params.graph_build_config`，不存储 API Key
- ✅ `validate_options()` 确保 `model_spec` 必填、不支持自定义 Prompt

### 2. 现有 API 端点

| 端点 | 方法 | 路由 | 功能 |
|---|---|---|---|
| 创建知识库 | POST | `/knowledge/databases` | 接收 `additional_params`，但未包含 `graph_build_config` |
| 配置图谱抽取 | POST | `/knowledge/databases/{kb_id}/graph-build/config` | **后置**配置，知识库已存在后 |
| 查询图谱状态 | GET | `/knowledge/databases/{kb_id}/graph-build/status` | 返回 config 是否已锁定 |
| 触发图谱构建 | POST | `/knowledge/databases/{kb_id}/graph-build/index` | 构建图谱索引 |

### 3. 当前创建流程限制

`create_database` (knowledge_router.py:146):
```python
additional_params: dict | None = Body(None)
```
- `additional_params` 已作为整体接收，理论上可包含 `graph_build_config`
- 但 `MilvusKB.normalize_additional_params()` 需要确认是否支持 `graph_build_config` 透传
- 创建时未显式调用 `MilvusGraphService.configure()`

### 4. 前端新建知识库弹窗 (DataBaseView.vue)

当前表单字段：
- 知识库名称 (必填)
- 嵌入模型 (EmbeddingModelSelector)
- 分块策略 (a-select)

**缺失**：无图谱抽取 Chat 模型选择器，无 `graph_build_config` 预配置区块。

### 5. 前端图谱配置页 (KnowledgeGraphSection.vue)

- 已有后置配置界面（知识库详情页 `DataBaseInfoView.vue`）
- 含 GraphCanvas、配置项、构建触发按钮
- 但仅在知识库**已创建后**可见

### 6. Chat 模型选择器现状

- `EmbeddingModelSelector` 已存在，仅加载 `model_type=embedding`
- 需要新建 `ChatModelSelector`，筛选 `model_type=chat`
- `select_model()` 已在 `llm.py` 中用于图谱抽取

### 7. `graph_build_config` 结构（确认）

```json
{
  "locked": true,
  "extractor_type": "llm",
  "extractor_options": {
    "model_spec": "provider/model",
    "schema": "",
    "concurrency_count": 1,
    "model_params": {}
  },
  "created_at": "2026-06-10T...",
  "created_by": "user_id"
}
```

## 设计决策

### T08 实现方案

**后端改动：**

1. `create_database` 增加可选 `graph_build_config: dict | None = Body(None)`
2. 创建流程中检查：
   ```python
   if graph_build_config and graph_build_config.get("enabled"):
       if kb_type != "milvus":
           raise HTTPException(400, "图谱构建仅支持 Milvus 知识库")
       await MilvusGraphService().configure(
           kb_id, extractor_type, extractor_options, created_by
       )
   ```
3. `graph_build_config.enabled` 控制是否在创建时预配置；若 `enabled=false`，仅当已有 `graph_build_config` 结构时透传但不锁定

**前端改动：**

1. 新建 `web/src/components/ChatModelSelector.vue`——只加载 `model_type=chat`
2. 在 `DataBaseView.vue` 新建知识库弹窗中增加：
   ```
   知识图谱构建
   [ ] 创建时配置知识图谱抽取
   抽取器类型：LLM（固定）
   图谱抽取 Chat 模型 ← ChatModelSelector
   Schema（可选文本框）
   并发队列数（默认 1）
   模型参数 JSON（默认 {}）
   ```
3. 仅在 `kb_type == "milvus"` 时显示图谱配置区块

### 关键约束

- 图谱抽取 Chat 模型使用 `model_spec`，**不绑定聊天智能体实例**
- 前端文案统一为"图谱抽取 Chat 模型"
- 配置保存到 `additional_params.graph_build_config`，复用现有 `MilvusGraphService.configure()`
- 不保存 API Key

## 测试命令

```bash
git diff --check
```

## 测试结果

- `git diff --check` — ✅ 通过（无代码修改）

## 风险

- `additional_params` 中 `graph_build_config` 需要通过 `normalize_additional_params` 的检查，可能需要确认不会拦截
- `ChatModelSelector` 需要与 `EmbeddingModelSelector` 共享 `model_cache` 查询模式

## 已知限制

- 创建时配置后，图谱构建仍需手动触发（或通过 Schedule 自动触发）
- Schema 输入为自由文本 JSON，暂无 Schema 模板库

## 提交

本报告待提交。

## 远端

- 分支：`main2.0`
