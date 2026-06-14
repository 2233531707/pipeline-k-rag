# T11 任务报告 — .yuxikb.zip 导出服务

## 目标

实现 Yuxi Portable Knowledge Package V1 导出服务，将知识库的文档、chunk、图谱、配置打包为 `.yuxikb.zip` 文件。

## 分支

`main2.0`

## 修改文件

无

## 新增文件

| 文件 | 说明 |
|---|---|
| `backend/package/yuxi/knowledge/migration/__init__.py` | 迁移模块初始化 |
| `backend/package/yuxi/knowledge/migration/schemas.py` | 数据模型（PackageManifest、DatabaseMeta、ChunkRecord、EntityRecord、RelationshipRecord、ExportTaskPayload）和安全常量 |
| `backend/package/yuxi/knowledge/migration/manifest.py` | Manifest 构建与校验 |
| `backend/package/yuxi/knowledge/migration/checksums.py` | SHA-256 校验和计算 |
| `backend/package/yuxi/knowledge/migration/exporter.py` | 导出核心逻辑——收集数据、写入文件、打包 ZIP |
| `backend/test/unit/knowledge/migration/test_exporter.py` | 11 个单元测试 |

## 删除文件

无

## 导出流程

```
export_portable_package(kb_id, work_dir, created_by)
  → 收集数据库元信息
  → 收集文件列表（从 KnowledgeFileRepository）
  → 收集 Chunk（从 KnowledgeChunkRepository）
  → 收集图谱数据（从 Neo4j via MilvusGraphService.query_nodes）
  → 收集图谱配置（清空 model_spec）
  → 下载原始文件和 Markdown（从 MinIO）
  → 写入 chunks.jsonl、entities.jsonl、relationships.jsonl
  → 写入 manifest.json、database.json、query_params.json
  → 计算 SHA-256 校验和
  → 打包为 .yuxikb.zip
  → 清理临时目录
```

## 安全保护

| 保护项 | 实现 |
|---|---|
| 文件名消毒 | `_sanitise_filename()` 移除路径分隔符和 `..` |
| model_spec 清空 | 图谱配置中的 `model_spec` 导出为空字符串 |
| 不含向量 | `ChunkRecord` 不包含 `embedding` 字段 |
| 不含凭据 | `DatabaseMeta` 不含 `kb_id`、`embedding_model_spec`、`created_by` |
| 临时目录清理 | `finally` 块中强制 `rmtree` |

## 测试命令

```bash
docker exec yuxi-sync-api sh -c "cd /app && uv run --no-sync --no-dev pytest test/unit/knowledge/migration/test_exporter.py -q"
```

## 测试结果

11 passed ✅

### 覆盖场景

| 测试 | 状态 |
|---|---|
| 文件名消毒-移除路径分隔符 | ✅ |
| 文件名消毒-移除 `..` | ✅ |
| 文件名消毒-正常文件名不变 | ✅ |
| Manifest 构建 | ✅ |
| Manifest 版本校验-OK | ✅ |
| Manifest 版本校验-不兼容版本 | ✅ |
| SHA-256 计算 | ✅ |
| 缺失文件跳过 | ✅ |
| ChunkRecord 不含 embedding | ✅ |
| DatabaseMeta 不含敏感字段 | ✅ |
| 禁止文件扩展名列表 | ✅ |

## 风险

- 导出 API 端点（POST/GET）待 T12 完成后注册
- 大知识库（>5GB 文件）导出需要异步任务支持，已预留 `ExportTaskPayload` 和 tasker 集成点

## 已知限制

- 图谱数据导出依赖 Neo4j 可用性；Neo4j 不可用时跳过图谱
- MinIO 文件下载失败跳过单个文件，不阻塞整体导出

## 提交

- 代码 commit：待提交
- 报告 commit：待提交

## 远端

- 分支：`main2.0`
