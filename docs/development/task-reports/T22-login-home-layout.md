# T22 任务报告 — 登录页、首页与整体布局优化

## 目标

优化登录页和首页样式，删除不符合架构的链接和 GitHub 推广内容。

## 分支

`main2.0`

## 删除的推广内容

| 位置 | 删除内容 |
|---|---|
| LoginView.vue footer | `github.com/xerrors` 联系链接 + `github.com/xerrors/Yuxi` 使用帮助链接 |
| HomeView.vue header | GitHub Star 链接（含 SVG 图标） |
| HomeView.vue hero | "查看文档" 按钮 → xerrors.github.io/Yuxi |
| HomeView.vue badge | GitHub Stars 打字动画（含 `GITHUB_REPO_API` / `GITHUB_STARS_TIMEOUT`） |
| HomeView.vue realtimeStats | Stars/Forks/Open Issues 实时统计显示 |
| HomeView.vue 错误页 | "常见问题" → FAQ 链接 |
| HomeView.vue script | `repoUrl` / `faqUrl` / `githubStats` / `fetchGithubRepo` / `stopStarsFetch` / `formatStars` / `starsFetchController` |

## 登录页保留功能

| 功能 | 状态 |
|---|---|
| 居右布局（双栏：左侧图片 + 右侧表单） | ✅ 已有 |
| 左侧视觉区域（login-bg.jpg） | ✅ 已有 |
| 固定右侧登录面板 | ✅ 已有 |
| Loading（a-spin / 登录按钮 loading） | ✅ 已有 |
| Error（errorMessage 红色提示） | ✅ 已有 |
| 密码显示（a-input-password） | ✅ 已有 |
| 记住状态（OIDC integration） | ✅ 保留 |
| 风格与内页一致 | ✅ 使用 infoStore 品牌色 |

## 首页保留功能

| 功能 | 状态 |
|---|---|
| 氛围装饰背景（orb + grid-mesh） | ✅ 保留 |
| 智能体 Harness→RAG 引擎→知识库 流程图 | ✅ 保留 |
| "开始体验" 按钮 | ✅ 保留 |
| Loading / Error / 重试 状态 | ✅ 保留 |
| 副标题轮播 | ✅ 保留 |

## 修改文件

| 文件 | 说明 |
|---|---|
| `web/src/views/LoginView.vue` | 删除 footer 中 GitHub 链接 |
| `web/src/views/HomeView.vue` | 删除 GitHub Star/链接/统计、FAQ 按钮、未使用 import |

## 测试命令

```bash
docker exec web-dev sh -c "cd /app && pnpm lint"
docker exec web-dev sh -c "cd /app && pnpm build"
```

## 测试结果

- pnpm lint: ✅ 通过
- pnpm build: ✅ 通过 (45.79s)

## 提交

- commit: 待提交

## 远端

- `main2.0`
