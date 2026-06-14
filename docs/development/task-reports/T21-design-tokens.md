# T21 任务报告 — UI 模板分析与设计 Token

## 目标

分析 UI 参考模板 `ui_template.html`，抽取统一设计 Token 并建立项目级 CSS 变量体系。

## 分支

`main2.0`

## 模板分析

从 `ui_template.html` 提取的视觉风格：

| 维度 | 值 |
|---|---|
| 品牌色 | `#0b6fe8` (600) / `#0758c9` (700) / `#1685ff` (500) |
| 背景色 | `#f6f8fc` (页面), `#ffffff` (面板/侧栏) |
| 主文字色 | `#162033` (`--ink-900`) |
| 次要文字 | `#637089` (`--ink-600`) |
| 边框色 | `#e7edf5` (`--line-200`) |
| 成功色 | `#0f9f6e` |
| 警告色 | `#c97a05` |
| 错误色 | `#d43a43` |
| 圆角 | `8px` / `12px` / `18px` |
| 阴影 | `0 1px 3px rgba(26,45,78,0.07)` |
| 侧栏宽 | `252px` |
| 顶栏高 | `58px` |
| 字体 | `-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif` |

## 修改文件

| 文件 | 说明 |
|---|---|
| `web/src/assets/css/base.css` | 顶部新增 `@import './tokens.css'` |

## 新增文件

| 文件 | 说明 |
|---|---|
| `web/src/assets/css/tokens.css` | 统一设计 Token：品牌色、背景色、文字色、边框色、语义色、圆角、阴影、布局尺寸 |
| `web/src/assets/css/layout.css` | 全局布局样式：app-shell（侧栏+主区）、nav-item、topbar、card、btn-primary、sidebar-collapsed |

## 删除文件

无

## Token 对照

| 指南要求 | 实现 | 值（来自模板） |
|---|---|---|
| `--color-primary` | ✅ | `#0b6fe8` |
| `--color-primary-hover` | ✅ | `#0758c9` |
| `--color-primary-light` | ✅ | `#eaf4ff` |
| `--color-bg-page` | ✅ | `#f6f8fc` |
| `--color-bg-sidebar` | ✅ | `#ffffff` |
| `--color-bg-card` | ✅ | `#ffffff` |
| `--color-text-primary` | ✅ | `#162033` |
| `--color-text-secondary` | ✅ | `#637089` |
| `--color-border` | ✅ | `#e7edf5` |
| `--color-success` | ✅ | `#0f9f6e` |
| `--color-warning` | ✅ | `#c97a05` |
| `--color-danger` | ✅ | `#d43a43` |
| `--radius-sm` | ✅ | `8px` |
| `--radius-md` | ✅ | `12px` |
| `--radius-lg` | ✅ | `18px` |
| `--shadow-card` | ✅ | `0 1px 3px rgba(26,45,78,0.07)` |
| `--sidebar-width` | ✅ | `252px` |
| `--sidebar-collapsed-width` | ✅ | `0px` |
| `--header-height` | ✅ | `58px` |

## 禁止事项确认

- ✅ 未复制 Tailwind CDN
- ✅ 未复制静态假数据
- ✅ 未复制静态路由
- ✅ 未复制与项目架构不符的页面

## 测试命令

```bash
docker exec web-dev sh -c "cd /app && pnpm lint"
docker exec web-dev sh -c "cd /app && pnpm build"
```

## 测试结果

- pnpm lint: ✅ 通过
- pnpm build: ✅ 通过 (32.02s)

## 提交

- commit: 待提交

## 远端

- main2.0
