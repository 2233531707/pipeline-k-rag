# Issue tracker：GitHub

本仓库的 issues 和 PRDs 通过 `origin` remote 对应的 GitHub Issues 跟踪：`2233531707/pipeline-k-rag`。处理 issue 时使用 `gh` CLI。

## 约定

- **创建 issue**：`gh issue create --title "..." --body "..."`
- **读取 issue**：`gh issue view <number> --comments`
- **列出 issue**：`gh issue list --state open --json number,title,body,labels,comments`
- **评论 issue**：`gh issue comment <number> --body "..."`
- **添加 / 移除标签**：`gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **关闭 issue**：`gh issue close <number> --comment "..."`

在本仓库内运行 `gh` 命令，让它通过 `origin` 自动解析 GitHub 仓库。

## 当 skill 要求 “publish to the issue tracker”

创建一个 GitHub issue。

## 当 skill 要求 “fetch the relevant ticket”

运行 `gh issue view <number> --comments`。
