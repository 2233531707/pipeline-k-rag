# T05 任务报告 — 图谱工具前端结果卡片

## 目标

为 `query_knowledge_graph` 工具新增前端结果渲染卡片，支持节点、关系展示和增强检索提示。

## 分支

`feat/main2-t05-knowledge-graph-result`

## 修改文件

| 文件 | 说明 |
|---|---|
| `web/src/components/ToolCallingResult/ToolCallRenderer.vue` | 注册 `KnowledgeGraphResult` 组件到 `query_knowledge_graph` |
| `web/src/components/ToolCallingResult/toolRegistry.js` | 添加 `query_knowledge_graph → Network` 图标映射 |

## 新增文件

| 文件 | 说明 |
|---|---|
| `web/src/components/ToolCallingResult/renderers/KnowledgeGraphResult.vue` | 图谱查询结果卡片组件 |

## 删除文件

无

## UI 设计

### 默认折叠状态
```
已查询知识图谱 | 12 个节点 · 18 条关系 · 已生成知识库增强检索提示
```

### 展开状态
- **节点列表**：节点名、类型标签、描述（截断200字）
- **关系列表**：source_id → type → target_id
- **增强检索提示**：graph_entity_ids、chunk_ids、file_ids、keywords
- **空状态**：未查询到匹配的图谱节点和关系
- **错误状态**：红色错误卡片，显示错误消息
- **加载状态**：旋转 Loader2 图标

### 技术细节
- 使用 `<details>/<summary>` 原生 HTML 实现折叠/展开
- 图标使用 lucide-vue-next（AlertCircle、Info、Loader2）
- 样式使用 base.css 颜色变量
- 禁止渲染大型图谱画布（仅列表展示）

## 测试命令

```bash
docker exec web-dev sh -c "cd /app && pnpm lint"
docker exec web-dev sh -c "cd /app && pnpm build"
```

## 测试结果

- pnpm lint: ✅ 通过（无错误）
- pnpm build: ✅ 通过（48.85s）
- pnpm test: ⚠️ web-dev 未配置测试脚本（无前端测试文件）

## 风险

- `knowledge_graph_result` 渲染器放在 `renderers/` 而非 `tools/` 目录，与现有组件组织风格略有差异
- `useDatabaseStore` 通过 `require()` 动态引入，可能在某些打包配置下报错

## 已知限制

- 节点 ID 显示为 Neo4j element_id（长数字），尚未适配为友好名称
- 关系列表无去重逻辑，大型图谱可能显示冗余

## 提交

- 代码 commit：待提交
- 报告 commit：待提交

## 远端

- 任务分支：`feat/main2-t05-knowledge-graph-result`（待推送）
