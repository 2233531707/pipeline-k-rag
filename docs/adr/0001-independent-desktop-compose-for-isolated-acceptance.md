# 采用独立桌面 Compose 支持隔离验收

我们决定为 Windows 桌面交付和隔离验收模式使用专用的 `docker-compose.desktop.yml`，同时保留 `docker-compose.yml` 作为开发栈、`docker-compose.prod.yml` 作为服务端生产候选栈。这样可以避免桌面安装包启动热重载开发栈，也避免把服务端生产约束和桌面交付约束塞进同一份 Compose 文件。

桌面 Compose 从启动器生成的 `.env.desktop` 读取随机本地密钥，缺少必要密钥时应失败。桌面交付默认只暴露 Web 入口；API 健康检查如需直连只能使用本机访问，PostgreSQL、Redis、MinIO、Milvus、Neo4j 等状态服务保留在 Docker internal network 内。
