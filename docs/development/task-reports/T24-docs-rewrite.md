# T24 任务报告：文档重写与目录整理

## 整理原则

- 保留 `backend`、`web`、`docker`、`docs`、`packaging` 和 `scripts` 的既有运行边界。
- 不为“看起来整齐”移动 Docker 挂载、构建上下文或脚本依赖的目录。
- 根目录只清理临时日志；UI 模板和 Main2 任务基线仍被开发流程引用，继续保留。
- 新增项目结构说明，明确源码、运行数据、构建产物和私密配置边界。

## 完成内容

- 重写中英文 README，补齐开发、生产、Lite、GPU OCR 和 isolated 启动方式。
- 修正远端分支、生产 `--env-file`、容器内测试路径和前端构建说明。
- 重写项目简介、快速开始与生产部署文档。
- 统一产品展示名称为“地下管网知识模型数据库”。
- 记录 Milvus + Neo4j、`query_knowledge_graph`、graph-seeded `query_kb`、图谱抽取模型、`.yuxikb.zip`、索引重建、PostGIS、图层叠加、会话地图、Docker 和 Windows 安装包。
- 保留 `docs/archive/` 中仍需追溯的上游文档。
- 扩展 `.gitignore`，排除迁移包、运行数据、依赖、构建产物、缓存和日志。

## 验证

- `docker compose config`
- VitePress production build
- README 中的开发和生产 Compose 命令
- 文档链接与导航
- 上传清单和敏感信息扫描
