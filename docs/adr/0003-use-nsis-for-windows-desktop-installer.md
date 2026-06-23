# 使用 NSIS 作为 Windows 桌面安装器

我们决定用 NSIS 替换 Inno Setup 作为 Windows 桌面安装器，同时继续保留 Docker Compose 作为运行方式。安装器只负责当前用户安装、文件部署、启动器入口和卸载策略；业务服务仍由启动器通过 Docker Compose 管理。

这个决策牺牲了继续复用既有 Inno Setup 脚本的低迁移成本，换取安装流程、卸载数据策略和离线镜像旁路发布方式的可控性。NSIS 安装器不内置大体积 Docker 镜像，发布时单独准备 `dist/images/yuxi-images.tar`，由启动器在首次启动时检测并加载。

Windows 桌面交付只支持当前用户安装，默认路径为 `%LOCALAPPDATA%\地下管网知识模型数据库`。不提供管理员安装或所有用户安装模式，避免 UAC、写权限、多用户数据归属和 Docker 上下文混用问题。

卸载默认保留 `.env.desktop`、数据目录、Docker 命名卷和离线镜像包。只有用户二次确认删除数据时，才允许按当前 `COMPOSE_PROJECT_NAME` 删除本实例资源；不得按通用容器名或镜像名删除 MinIO、Redis、PostgreSQL 等资源。
