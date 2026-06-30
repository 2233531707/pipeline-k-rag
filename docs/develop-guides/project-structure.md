# 项目结构

本项目保持后端、前端、容器编排、文档和交付工具的边界清晰。目录整理遵循“只移动无运行依赖的文档或临时产物”原则，避免为了表面整齐破坏 Docker 挂载、构建上下文和脚本路径。

## 根目录

```text
pipeline-k-rag/
├── backend/                 FastAPI、LangGraph、知识库、任务 Worker 与测试
├── web/                     Vue 3 前端源码、静态资源和前端测试
├── docker/                  Dockerfile、Nginx、沙盒 provisioner 与本地运行卷
├── docs/                    VitePress 用户文档、开发指南和任务报告
├── packaging/windows/       Windows 桌面前端客户端打包源码与历史废弃资产
├── scripts/                 初始化、镜像拉取、数据卷检查和版本脚本
├── docker-compose.yml       开发与调试环境
├── docker-compose.prod.yml  生产构建环境
├── Makefile                 常用 Compose、格式化和 isolated 验收命令
├── ARCHITECTURE.md          稳定架构边界和代码地图
├── AGENTS.md                通用开发约束
├── CLAUDE.md                Claude 开发约束
├── README.md                中文项目入口和部署说明
└── README.en.md             English project entry
```

根目录的 `ui_template.html` 是 UI 风格参考，`yuxi_main2_claude_task_split_guide_clean.md` 是 Main2 任务与验收基线。两者仍被开发流程直接引用，因此保留在根目录，不参与运行构建。

## 后端

```text
backend/
├── package/yuxi/
│   ├── agents/              Agent、Context、中间件、Tools、MCP、Skills
│   ├── knowledge/           RAG、图谱、迁移、空间数据、解析与分块
│   ├── repositories/        数据访问层
│   ├── services/            用例与跨模块编排
│   └── storage/             PostgreSQL、MinIO 等基础设施
├── server/
│   ├── routers/             FastAPI 路由和 HTTP 适配
│   ├── main.py              API 入口
│   └── worker_main.py       异步 Worker 入口
├── test/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── scripts/                 后端维护和初始化脚本
```

容器内后端根目录为 `/app`，因此测试路径使用 `test/unit`，不是 `backend/test/unit`。

## 前端

```text
web/
├── src/
│   ├── apis/                所有后端 API 封装
│   ├── components/          可复用组件
│   ├── composables/         流式运行和页面组合逻辑
│   ├── layouts/             应用布局
│   ├── stores/              Pinia 状态
│   ├── utils/               通用逻辑和前端测试
│   └── views/               页面入口
├── public/                  favicon、头像等静态资源
├── dist/                    生产构建产物，不提交 Git
├── package.json
└── pnpm-lock.yaml
```

开发栈的 `web-dev` 使用 Vite 热重载；isolated 栈只读挂载 `web/dist`，前端源码变化后必须先执行 `pnpm --dir web build`。

## 数据与构建产物

下列内容只属于本机运行或构建过程，不应提交：

- `.env`、`.env.prod`、测试账号配置和任何密钥文件；
- `docker/volumes/`、Compose 数据卷、`backend/saves*`、数据库文件和用户上传内容；
- `web/node_modules/`、`web/dist/`；
- `packaging/windows/{.cache,.nsis,build,dist}`；
- `.yuxikb.zip` 迁移包、Docker 镜像归档、日志和缓存；
- `.claude/`、`.codex/`、IDE 配置和个人工作记录。

可提交的是源码、锁文件、模板、Compose 文件、Dockerfile、测试、正式文档和 Windows 桌面客户端打包源码。

当前首版桌面客户端工程放在 `packaging/windows/electron/`，Windows 构建脚本放在 `packaging/windows/scripts/build_electron_portable.ps1`。被废弃的本地单机版交付遗留已经从 `packaging/windows/` 清理，不应再按该方向恢复目录、脚本或测试。

## 变更边界

- 新增 API 必须放在 `web/src/apis` 对应模块。
- 后端路由保持薄，业务流程优先进入 `yuxi.services`，持久化进入 repository。
- 测试必须放在 `backend/test` 对应层级。
- 不直接修改或上传 `docker/volumes` 中的数据。
- 不把 `web/dist` 当作源码；它只用于本地 isolated 验收和镜像构建。
