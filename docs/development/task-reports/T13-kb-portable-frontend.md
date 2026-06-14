# T13 任务报告 — 知识库迁移前端

## 目标

实现知识库便携迁移包的导入导出前端界面。

## 分支

`main2.0`

## 修改文件

| 文件 | 说明 |
|---|---|
| `web/src/views/DataBaseView.vue` | 添加"从迁移包导入"按钮、导入模态框（4 步骤：选文件→预检→配置→导入） |
| `web/src/apis/knowledge_api.js` | 新增 4 个迁移 API 方法 |

## 新增文件

无

## 删除文件

无

## UI 设计

### DataBaseView 导入 Modal

```
┌─ 从迁移包导入 ─────────────────────────┐
│                                         │
│ 1. 选择 .yuxikb.zip 迁移包             │
│    [选择文件] filename.yuxikb.zip       │
│                                         │
│ 2. 预检报告                             │
│    名称：xxx    文件数：12              │
│    Chunk数：428  实体数：982            │
│    关系数：1304                         │
│                                         │
│ 3. 导入配置                             │
│    新知识库名称：_______                │
│    嵌入模型：[选择器]                    │
│    图谱抽取 Chat 模型：[选择器]         │
│                                         │
│    [取消] [开始导入]                     │
│                                         │
│ ✓ 导入完成                              │
│    kb_id: xxx  名称: xxx                │
└─────────────────────────────────────────┘
```

### 新建知识库弹窗增加

- 空白新建（原有模式）
- 从迁移包导入（新增）

### API 层

```javascript
databaseApi.exportPortablePackage(kbId)
databaseApi.downloadPortablePackage(kbId, taskId)
databaseApi.preflightImport(formData)
databaseApi.importPortablePackage({ file, target_name, ... })
```

## 测试命令

```bash
docker exec web-dev sh -c "cd /app && pnpm lint"
docker exec web-dev sh -c "cd /app && pnpm build"
```

## 测试结果

- pnpm lint: ✅ 通过
- pnpm build: ✅ 通过 (39.80s)

## 风险

- 导入/导出 API 端点待 T14 集成测试验证
- 预检 API 的 `preflight_passed` 字段名需与后端一致

## 已知限制

- 导出功能按钮尚未添加到 DataBaseInfoView 详情页
- 导入进度暂无实时轮询，仅等待同步结果

## 提交

- 代码 commit：待提交

## 远端

- 分支：`main2.0`
