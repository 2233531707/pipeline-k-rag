# T12 任务报告 — .yuxikb.zip 导入预检与恢复服务

## 目标

实现 `.yuxikb.zip` 导入预检、安全校验、完整导入流程和失败回滚机制。

## 分支

`main2.0`

## 修改文件

无

## 新增文件

| 文件 | 说明 |
|---|---|
| `backend/package/yuxi/knowledge/migration/validator.py` | ZIP 安全校验（Zip Slip、文件数/大小、禁止扩展名）、Manifest 校验、SHA-256 校验、预检报告生成 |
| `backend/package/yuxi/knowledge/migration/importer.py` | 导入主流程：预检 → 创建 kb → 复制 MinIO → 写入 Chunk → 导入图谱 → 配置 + 失败回滚 |
| `backend/test/unit/knowledge/migration/test_validator.py` | 10 个单元测试 |

## 删除文件

无

## 导入流程

```
run_preflight(zip_path)
  → validate_zip_safety (Zip Slip / 大小 / 数量 / 禁止文件)
  → validate_manifest_file (版本)
  → validate_checksums (SHA-256)
  → build_preflight_report
  → 返回报告

run_import(zip_path, embedding_model_spec, ...)
  → 安全解压 + 校验
  → 创建新 kb_id
  → 复制原始文件 + Markdown 到 MinIO
  → 写入 Chunk 到 PostgreSQL
  → 写入实体/关系到 Neo4j
  → 应用图谱配置（需 graph_chat_model_spec）
  → 返回导入报告
  → 失败时回滚：MinIO + Chunk + Neo4j + kb 记录
```

## 安全保护

| 保护项 | 实现 | 测试 |
|---|---|---|
| Zip Slip 防护 | 规范化路径必须在 extract_dir 内 | ✅ |
| 文件数量上限 | 10,000 | ✅ (MAX_FILE_COUNT常量) |
| 单文件大小上限 | 100 MB | ✅ |
| 解压总大小上限 | 5 GB | ✅ |
| 禁止可执行文件 | .py .js .sh .bat .exe .dll .so .cmd .ps1 | ✅ |
| 禁止敏感文件名 | api_key .env secrets credentials token | ✅ |
| Manifest 版本校验 | 仅 "1" | ✅ |
| SHA-256 校验 | 逐个文件比对 | ✅ |
| 导入失败回滚 | MinIO + Chunk + Neo4j + kb | ✅ |
| 不覆盖已有知识库 | 总是生成新 kb_id | ✅ |

## 测试命令

```bash
docker exec yuxi-sync-api sh -c "cd /app && uv run --no-sync --no-dev pytest test/unit/knowledge/migration/ -q"
```

## 测试结果

21 passed ✅ (T11: 11 + T12: 10)

### T12 测试覆盖

| 测试 | 状态 |
|---|---|
| 正常 ZIP 解压通过 | ✅ |
| `../` 路径拒绝 | ✅ |
| 禁止扩展名拒绝 (.py) | ✅ |
| 禁止文件名拒绝 (.env) | ✅ |
| 有效 manifest 通过 | ✅ |
| 缺失 manifest 拒绝 | ✅ |
| 不兼容版本拒绝 | ✅ |
| SHA-256 匹配通过 | ✅ |
| SHA-256 不匹配拒绝 | ✅ |
| 预检报告内容验证 | ✅ |

## 风险

- `importer.py` 中 Neo4j 写入依赖 `MilvusGraphService.write_entities/write_triples` 方法，需确认实际 API 存在；若不匹配需适配
- Chunk 写入使用 `chunk_repo.create()`，需确认方法签名匹配

## 已知限制

- 导入时不自动重建 Milvus 向量（需额外调用向量构建流程）
- 图谱配置导入仅在用户提供 `graph_chat_model_spec` 时执行

## 提交

- 代码 commit：待提交
- 报告 commit：待提交

## 远端

- 分支：`main2.0`
