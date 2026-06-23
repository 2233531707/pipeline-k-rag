# Yuxi Portable Knowledge Package V1

> `*.yuxikb.zip` — 知识库应用层逻辑迁移包

## 概述

Yuxi Portable Knowledge Package 是跨终端迁移知识库的标准格式。它打包文档、解析结果、图谱数据和元配置，目标终端基于包内数据重建向量索引和 Neo4j 图谱。

## 包格式

### 文件名

```
{yuxi-kb-name}-{timestamp}.yuxikb.zip
```

### 内部目录结构

```
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

## 各文件定义

### `manifest.json`

```json
{
  "package_version": "1",
  "created_at": "2026-06-10T12:00:00Z",
  "generator": "yuxi-kb-export/1.0",
  "database_name": "供水管网知识库",
  "kb_type": "milvus",
  "stats": {
    "files": 12,
    "chunks": 428,
    "entities": 982,
    "relationships": 1304,
    "total_original_bytes": 15728640
  }
}
```

### `database.json`

```json
{
  "name": "供水管网知识库",
  "description": "描述",
  "kb_type": "milvus",
  "additional_params": {
    "chunk_preset_id": "general"
  }
}
```

> ⚠️ 禁止包含：`kb_id`、`embedding_model_spec`、`llm_model_spec`、`created_by`、`created_by_department_id`、`share_config`、`status`

### `files/originals/`

用户上传的原始文件，保持原始文件名和扩展名。

### `files/parsed/`

解析后的 Markdown 文件，与原始文件同名（`.md` 后缀）。

### `chunks/chunks.jsonl`

每行一个 JSON 对象：

```json
{
  "chunk_id": "chunk_xxx",
  "file_id": "file_xxx",
  "chunk_index": 0,
  "content": "文本内容",
  "start_char_pos": 0,
  "end_char_pos": 512,
  "ent_ids": [],
  "tags": []
}
```

> ⚠️ 禁止包含：`kb_id`、向量数据 (`embedding`)、`graph_indexed`（布尔）、`extraction_result`

### `graph/config.json`

```json
{
  "locked": true,
  "extractor_type": "llm",
  "extractor_options": {
    "model_spec": "",
    "schema": "",
    "concurrency_count": 1,
    "model_params": {}
  }
}
```

> ⚠️ `model_spec` 字段保留键名但清空值——不导出 API 凭据关联的 model spec

### `graph/extraction_results.jsonl`

每行一个抽取结果（LLM 原始 JSON 输出），用于可选的重新导入验证。

### `graph/entities.jsonl`

```json
{
  "entity_id": "ent_xxx",
  "name": "实体名",
  "label": "Entity",
  "attributes": [],
  "entity_type": "Person"
}
```

### `graph/relationships.jsonl`

```json
{
  "source_entity_id": "ent_a",
  "target_entity_id": "ent_b",
  "relation_type": "WORKS_AT",
  "keywords": "任职于"
}
```

### `settings/query_params.json`

```json
{
  "similarity_threshold": 0.2,
  "final_top_k": 10,
  "search_mode": "vector",
  "use_graph_retrieval": true,
  "graph_top_k": 20,
  "graph_max_nodes": 10000,
  "ppr_damping": 0.85
}
```

### `checksums/sha256.json`

```json
{
  "manifest.json": "sha256hex...",
  "database.json": "sha256hex...",
  "chunks/chunks.jsonl": "sha256hex...",
  "graph/entities.jsonl": "sha256hex...",
  "graph/relationships.jsonl": "sha256hex..."
}
```

对包内每个文件计算 SHA-256 校验和。导入预检会拒绝 `checksums/sha256.json` 清单外的额外文件；除清单文件自身外，包内所有实际文件都必须被 SHA-256 清单覆盖。

## 禁止导出清单

| 类别 | 具体内容 |
|---|---|
| 凭据 | API Key、Provider 凭证、用户 Token |
| 原始数据库 | Milvus collection 文件、Neo4j 数据目录、PostgreSQL dump、Docker volume |
| 对象存储 | 整个 MinIO bucket |
| 向量数据 | 原始 embedding 向量 |
| 用户/权限 | 原终端用户 ID、部门 ID、共享权限 |
| 任务状态 | 任务运行状态、进度 |
| 本地信息 | 本地绝对路径 |

## 导入流程

```
上传 .yuxikb.zip
  → 安全解压（Zip Slip 防护）
  → 校验 manifest 版本（仅为 "1"）
  → 校验 SHA-256
  → 返回预检报告（文件数、chunk 数、实体数、关系数、所需模型）
  → 用户确认并选择模型
  → 创建新 kb_id
  → 复制文件到 MinIO
  → 写入 Chunk 到 PostgreSQL
  → 使用目标终端选择的嵌入模型重建 Milvus 向量
  → 使用实体与关系重建 Neo4j 图谱
  → 重建图谱向量索引
  → 输出导入报告
```

## 安全模型

### Zip Slip 防护

解压时验证每个条目的规范化路径必须在目标目录内。拒绝包含 `..` 或绝对路径的条目。

### 大小限制

| 限制项 | 值 |
|---|---|
| 单文件大小上限 | 100 MB |
| ZIP 上传文件上限 | 5 GB |
| 解压后总大小上限 | 5 GB |
| 文件数量上限 | 10,000 |

### 校验

- `manifest.package_version` 必须为 `"1"`
- `manifest.stats` 中的文件数、chunk 数必须与实际匹配
- 逐个文件验证 SHA-256 校验和
- 拒绝 SHA-256 清单外的额外文件

### 导入隔离

- 创建全新的 `kb_id`，**不覆盖**已有知识库
- 必须先通过预检才能执行导入
- 导入过程中使用临时目录，失败时清理所有中间产物（MinIO、PostgreSQL、Neo4j、Milvus）
- 不恢复原用户的 API Key、用户 ID、共享权限

### 不执行代码

- ZIP 内禁止 `.py`、`.js`、`.sh`、`.bat`、`.exe` 等可执行文件
- 导入流程不执行任何 ZIP 内的脚本或代码

## 默认行为

| 行为 | 默认值 |
|---|---|
| 重新调用 LLM 抽取 | **否**——复用导出的实体与关系 |
| 重建向量 | **是**——使用目标终端选择的嵌入模型 |
| 重建图谱 | **是**——使用 Neo4j 重建 |
| 覆盖已有知识库 | **禁止**——总是创建新 kb_id |
