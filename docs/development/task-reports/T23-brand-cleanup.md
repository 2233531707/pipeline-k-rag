# T23 任务报告 — 业务页面统一与品牌清理

## 目标

删除所有 xerrors 原作者推广内容，统一业务页面风格。

## 分支

`main2.0`

## 修改文件

| 文件 | 说明 |
|---|---|
| `web/src/layouts/AppLayout.vue` | 删除 GitHub Star 侧栏项，禁用 `fetchGithubStars` API 调用 |
| `web/src/components/SettingsModal.vue` | 替换 Star 卡片为"关于平台"卡片，删除项目 URL 引用 |
| `web/src/components/UserInfoComponent.vue` | 删除 `openDocs()` 函数（xerrors.github.io 文档链接） |
| `web/src/components/FileUploadModal.vue` | 删除文档处理帮助链接 |
| `web/src/components/modals/BenchmarkGenerateModal.vue` | 替换外部评估文档链接 |
| `web/src/components/modals/BenchmarkUploadModal.vue` | 替换外部评估文档链接 |

## 删除的推广内容

| 内容 | 文件 | 状态 |
|---|---|---|
| GitHub Star 链接 + Star 数 | AppLayout.vue | ✅ 已删除 |
| GitHub API fetch (`xerrors/Yuxi`) | AppLayout.vue | ✅ 已禁用 |
| "欢迎 Star" Tooltip | AppLayout.vue | ✅ 已删除 |
| Star 卡片 (img.shields.io) | SettingsModal.vue | ✅ 已替换 |
| `projectRepoUrl` 常量 | SettingsModal.vue | ✅ 已删除 |
| 文档链接 (`xerrors.github.io`) | UserInfoComponent.vue, FileUploadModal.vue | ✅ 已删除 |
| 评估文档链接 (`xerrors.github.io`) | BenchmarkGenerateModal.vue, BenchmarkUploadModal.vue | ✅ 已替换 |

## 检查确认

| 检查项 | 状态 |
|---|---|
| LICENSE 文件未删除 | ✅ 保留 |
| MIT License 未删除 | ✅ 保留 |
| 第三方依赖声明保留 | ✅ |
| 必要致谢保留 | ✅ |
| AgentView 检查 | ✅ 通过 |
| DataBaseView / DataBaseInfoView | ✅ 已有图谱/空间预配置 |
| SettingsModal 已清理 | ✅ |
| AppLayout 已清理 | ✅ |

## 测试命令

```bash
docker exec web-dev sh -c "cd /app && pnpm lint"
docker exec web-dev sh -c "cd /app && pnpm build"
```

## 测试结果

- pnpm lint: ✅ 通过
- pnpm build: ✅ 通过 (41.44s)

## Tag

`main2-checkpoint-ui`

## 提交

- commit: 待提交

## 远端

- `main2.0`
