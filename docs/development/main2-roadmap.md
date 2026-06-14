# Main2.0 开发路线图

> 分支：`main2.0`
> 基线提交：`254c1db3` (codex/sync-upstream-after-20260422-latest)
> 创建日期：2026-06-10

## 目标

基于上游 xerrors/Yuxi v0.7.0.beta2，完成 Yuxi 新版本二次开发，涵盖知识图谱增强、知识库迁移、空间数据模块、UI 重构和 Windows 交付。

## 任务清单

| 编号 | 任务 | 状态 | 检查点 Tag |
|---|---|---|---|
| T00 | 工作区、远端与模板基线检查 | ✅ 完成 | — |
| T01 | 初始化 main2.0 与任务报告机制 | ✅ 完成 | — |
| T02 | 显式图谱查询能力扫描与设计 | ✅ 完成 | — |
| T03 | 新增 query_knowledge_graph | ✅ 完成 | — |
| T04 | 扩展 query_kb 图谱种子增强检索 | ✅ 完成 | — |
| T05 | 图谱工具前端结果卡片 | ✅ 完成 | — |
| T06 | 图谱显式检索链路回归 | ✅ 完成 | main2-checkpoint-graph ✅ |
| T07 | 图谱抽取模型配置扫描与设计 | ✅ 完成 | — |
| T08 | 新建知识库支持图谱抽取 Chat 模型预配置 | ✅ 完成 | — |
| T09 | 图谱抽取模型配置交互测试 | ✅ 完成 | — |
| T10 | 知识库迁移格式设计与安全模型 | ✅ 完成 | — |
| T11 | .yuxikb.zip 导出服务 | ✅ 完成 | — |
| T12 | .yuxikb.zip 导入预检与恢复服务 | ✅ 完成 | — |
| T13 | 知识库迁移前端 | ✅ 完成 | — |
| T14 | 知识库迁移端到端测试 | ✅ 完成 | main2-checkpoint-migration ✅ |
| T15 | 空间数据模块扫描与设计 | ✅ 完成 | — |
| T16 | PostGIS 空间图层基础模型 | ✅ 完成 | — |
| T17 | 空间数据上传与图层管理 | ✅ 完成 | — |
| T18 | 图层叠加与派生空间分析 | ✅ 完成 | — |
| T19 | 空间智能体工具 | ✅ 完成 | — |
| T20 | 会话内地图可视化 | ⬜ 待开始 | main2-checkpoint-spatial |
| T21 | UI 模板分析与设计 Token | ⬜ 待开始 | — |
| T22 | 登录页、首页与整体布局优化 | ⬜ 待开始 | — |
| T23 | 业务页面统一与品牌清理 | ⬜ 待开始 | main2-checkpoint-ui |
| T24 | 文档重写与目录整理 | ⬜ 待开始 | main2-checkpoint-docs |
| T25 | Docker 全量回归 | ⬜ 待开始 | — |
| T26 | Windows .exe 启动器与安装包 | ⬜ 待开始 | main2-checkpoint-windows |
| T27 | 最终验收、Tag 与发布报告 | ⬜ 待开始 | main2.0-release-candidate |

## 技术架构要求

- 知识图谱：Milvus + Neo4j + PPR + RRF
- 图谱抽取：Chat 模型 spec，不绑定智能体实例
- 知识库迁移：Yuxi Portable Knowledge Package V1 (.yuxikb.zip)
- 空间数据：PostgreSQL + PostGIS + MinIO + GeoPandas + MapLibre GL JS
- Windows 交付：Docker 启动器安装包 (Yuxi-Desktop-Setup.exe)

## 当前状态

- 基线：`codex/sync-upstream-after-20260422-latest` @ `254c1db3`
- 所有 Docker 容器运行正常
- 下一步：T20 会话内地图可视化

## 已完成任务

### T19 — 2026-06-10
- Commit: `9c99d7d1` — feat(agent): add spatial query and map tools
- 报告: `docs/development/task-reports/T19-spatial-tools.md`

### T18 — 2026-06-10
- Commit: `c30bdb00` — feat(spatial): add layer compositions and derived analysis
- 报告: `docs/development/task-reports/T18-spatial-analysis.md`

### T17 — 2026-06-10
- Commit: `57a84c23` — feat(spatial): support spatial import and layer management
- 报告: `docs/development/task-reports/T17-spatial-upload.md`

### T16 — 2026-06-10
- Commit: `2962ee0f` — feat(spatial): add postgis spatial layer persistence
- 报告: `docs/development/task-reports/T16-spatial-persistence.md`

### T15 — 2026-06-10
- Commit: `5733032f` — docs(spatial): define spatial module architecture
- 报告: `docs/development/task-reports/T15-spatial-design.md`

### T14 — 2026-06-10
- Commit: `9f12f51b` — test(migration): verify portable knowledge package round trip
- Tag: `main2-checkpoint-migration`

### T13 — 2026-06-10
- Commit: `4608cefe` — feat(web): add portable knowledge package import and export flows
- 报告: `docs/development/task-reports/T13-kb-portable-frontend.md`

### T12 — 2026-06-10
- Commit: `9cbe4b5b` — feat(migration): import portable knowledge packages with index rebuild
- 报告: `docs/development/task-reports/T12-kb-portable-import.md`

### T11 — 2026-06-10
- Commit: `688d1182` — feat(migration): export portable knowledge packages
- 报告: `docs/development/task-reports/T11-kb-portable-export.md`

### T10 — 2026-06-10
- Commit: `d7f1e457` — docs(migration): define portable knowledge package format
- 报告: `docs/development/task-reports/T10-kb-portable-package-design.md`

### T09 — 2026-06-10
- Commit: `0ae26bb9` — test(knowledge): verify graph extraction model configuration flow

### T08 — 2026-06-10
- Commit: `dbf554f5` — docs: add T08 graph model config task report
- Commit: `ed6708a1` — feat(knowledge): configure graph extraction chat model during database creation
- 报告: `docs/development/task-reports/T08-graph-model-config.md`

### T07 — 2026-06-10
- Commit: `3530a376` — docs(graph): define graph extraction chat model configuration
- 报告: `docs/development/task-reports/T07-graph-model-config-design.md`

### T06 — 2026-06-10
- Commit: `93c02362` — test(graph): complete graph-enhanced retrieval regression
- Tag: `main2-checkpoint-graph`

### T05 — 2026-06-10
- Commit: `beef2ab7` — feat(web): render knowledge graph tool results
- 报告: `docs/development/task-reports/T05-knowledge-graph-result.md`

### T04 — 2026-06-10
- Commit: `b49498b5` — docs: add T04 graph-seeded retrieval task report
- 报告: `docs/development/task-reports/T04-graph-seeded-retrieval.md`

### T03 — 2026-06-10
- Commit: `b4fc3811` — feat(graph): add explicit knowledge graph query tool
- 报告: `docs/development/task-reports/T03-graph-query-tool.md`

### T02 — 2026-06-10
- Commit: `b5f4ab34` — docs(graph): define explicit graph query integration
- 报告: `docs/development/task-reports/T02-graph-query-design.md`

### T01 — 2026-06-10
- Commit: `f863f017` — docs: update T01 report with commit and remote details

### T00 — 2026-06-10
- Commit: `254c1db3` — chore: record main2.0 workspace baseline
- 报告: `docs/development/task-reports/T00-workspace-baseline.md`

## 风险

- `main2.0` 可直接基于 origin/main 创建，也可基于当前 codex 分支，需确认策略
- `ui_template.hml` 不存在，实际为 `ui_template.html`

## 测试记录

| 阶段 | 测试 | 结果 |
|---|---|---|
| T00 | docker compose config | ✅ |
| T00 | git diff --check | ✅ |

## 检查点 Tag

（尚未创建）

## 远端

- origin: `https://github.com/2233531707/pipeline-k-rag.git` (用户 fork)
- upstream: xerrors/Yuxi (只读参考)
