# T10 任务报告 — 知识库迁移格式设计与安全模型

## 目标

定义 `Yuxi Portable Knowledge Package V1` (*.yuxikb.zip) 格式规范与安全模型，为 T11（导出）和 T12（导入）提供设计基线。

## 分支

`main2.0`

## 修改文件

无（仅设计文档）

## 新增文件

| 文件 | 说明 |
|---|---|
| `docs/features/knowledge-base-portable-package.md` | 迁移包格式规范完整文档（包结构、字段定义、安全模型、导入流程） |
| `docs/development/task-reports/T10-kb-portable-package-design.md` | 本报告 |

## 删除文件

无

## 设计核心

### 格式定义

```
Yuxi Portable Knowledge Package V1
*.yuxikb.zip
```

### 包内结构

```
manifest.json                  # 包元信息：版本、时间、统计
database.json                  # 知识库元数据（不含 kb_id、模型 spec、用户信息）
files/originals/               # 原始文件
files/parsed/                  # Markdown 解析结果
chunks/chunks.jsonl            # 文本块（不含向量）
graph/config.json              # 图谱抽取配置（model_spec 清空）
graph/extraction_results.jsonl # LLM 抽取结果（可选）
graph/entities.jsonl           # 实体数据
graph/relationships.jsonl      # 关系数据
settings/query_params.json     # 检索参数
checksums/sha256.json          # 全部文件校验和
```

### 安全模型

| 防护项 | 规则 |
|---|---|
| Zip Slip | 验证规范化路径必须在目标目录内 |
| 单文件大小 | ≤ 100 MB |
| ZIP 总大小 | ≤ 2 GB |
| 解压总大小 | ≤ 5 GB |
| 文件数量 | ≤ 10,000 |
| 版本校验 | manifest.package_version == "1" |
| 完整性校验 | SHA-256 逐文件验证 |
| 导入隔离 | 创建新 kb_id，不覆盖已有知识库 |
| 回滚 | 导入失败清理 MinIO + PostgreSQL + Neo4j + Milvus |
| 凭据保护 | 不导出 API Key、用户 Token、共享权限 |
| 禁止可执行文件 | .py、.js、.sh、.bat、.exe 等 |

### 导入流程

```
上传 → 安全解压 → manifest 校验 → SHA-256 校验
  → 预检报告（文件数、chunk 数、实体数、关系数、所需模型）
  → 用户确认 + 选模型
  → 创建新 kb_id
  → 复制 MinIO → 写入 Chunk → 重建向量 → 重建图谱 → 导入报告
```

### 默认行为

| 行为 | 默认值 |
|---|---|
| 重新调用 LLM 抽取 | 否 |
| 重建向量索引 | 是 |
| 覆盖已有知识库 | 禁止 |

## 禁止导出清单（确认）

- [x] API Key
- [x] Provider 凭证
- [x] 原始 Milvus collection 文件
- [x] Neo4j 数据目录
- [x] PostgreSQL dump
- [x] Docker volume
- [x] 整个 MinIO bucket
- [x] 用户 Token
- [x] 原终端用户 ID
- [x] 部门 ID
- [x] 共享权限
- [x] 本地绝对路径
- [x] 任务运行状态
- [x] 原始 embedding 向量

## 测试命令

```bash
git diff --check
```

## 测试结果

- `git diff --check` — ✅ 通过

## 风险

- 知识库数据量较大时（>10,000 文件、>5 GB），需要分批导出或放宽上限
- `model_spec` 清空后，导入时需要用户手动选择 Chat 模型来重新配置图谱抽取

## 已知限制

- 不支持增量迁移/增量更新
- 大文件导出需要异步任务 + 进度上报，单次同步导出不可接受

## 提交

本报告待提交。

## 远端

- 分支：`main2.0`
