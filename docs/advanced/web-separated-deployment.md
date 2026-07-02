# Web 前后端分离部署

本方案用于快速交付“前端静态资源独立部署、后端服务单独部署、Windows 免安装 exe 壳打开 Web 地址”的前后端分离形态。主路径保持前端同源 `/api` 语义，由外部 Nginx/CDN 负责把 `/api` 反向代理到后端 API，避免浏览器 CORS 配置。

## 交付物

- 后端服务器：继续使用 `docker-compose.prod.yml` 启动 API、Worker、PostgreSQL/PostGIS、Redis、MinIO、Milvus、Neo4j 和沙盒 provisioner。
- 前端静态包：使用 `packaging-1/web-static/build-static-package.ps1` 生成版本化 zip，交给外部 Nginx/CDN 解压部署。
- Web 前端应用壳：使用 `packaging-1/windows/web-shell/` 构建免安装 Windows `portable exe`，打开服务器上的 Web URL。

本方案不把前端静态资源打入 exe 壳，不引入桌面端 token 安全存储，也不让前端直接跨域访问独立 API 域名。

## 1. 启动后端服务器

按生产部署文档准备 `.env.prod` 后启动后端生产栈：

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

默认生产 Compose 保留 `web` 服务用于本机验收、兜底和旧部署兼容。本方案的公网入口以外部 Nginx/CDN 为准。

## 2. 为外部 Nginx 提供受限 API 入口

`docker-compose.prod.yml` 中 API 容器默认只在 Docker 网络内监听 `5050`。如果外部 Nginx 和 Compose 在同一台服务器上，推荐新增本地 override 文件，只把 API 绑定到 `127.0.0.1`：

```yaml
# docker-compose.web-separated.override.yml
services:
  api:
    ports:
      - "127.0.0.1:15050:5050"
```

启动时叠加 override：

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  -f docker-compose.web-separated.override.yml \
  up -d --build
```

不要把 API 端口直接开放到公网。公网访问应统一从前端域名的 `/api` 进入。

## 3. 构建前端静态 zip

在 Windows PowerShell 中执行：

```powershell
packaging-1/web-static/build-static-package.ps1
```

产物默认输出到：

```text
packaging-1/web-static/dist/yuxi-web-static-<version>-<timestamp>.zip
```

zip 内容包括：

- `web/dist` 静态资源；
- `version.json`；
- `README.txt`；
- `nginx.example.conf`。

## 4. 部署外部 Nginx/CDN

将静态 zip 解压到外部 Nginx 静态目录，例如：

```bash
mkdir -p /var/www/yuxi-web
unzip yuxi-web-static-*.zip -d /var/www/yuxi-web
```

参考 `packaging-1/web-static/nginx.example.conf` 配置站点：

```text
https://app.example.com/        -> 静态前端
https://app.example.com/api/... -> 反代到后端 API
```

关键要求：

- `/api` 禁用缓存；
- SSE/流式响应关闭代理缓冲并延长超时；
- `/api/knowledge/portable-import` 允许 6 GiB 请求体并关闭请求缓冲；
- 前端静态资源可由 Nginx 或 CDN 缓存，但不得缓存 `/api`。

## 5. 构建 Web 前端应用壳

Web 壳只是一个免安装 Electron BrowserWindow URL 壳。构建：

```powershell
packaging-1/windows/scripts/build_web_shell_portable.ps1
```

最终交付 zip 默认输出到：

```text
packaging-1/windows/dist/yuxi-web-frontend-exe-<version>.zip
```

该 zip 解压后，当前目录下会直接出现：

```text
地下管网知识模型数据库 Web 入口.exe
README.txt
config.sample.json
```

如需预置服务器地址，可复制 `config.sample.json` 为 exe 同目录的 `config.json`：

```json
{
  "webUrl": "https://app.example.com"
}
```

如果同目录没有 `config.json`，首次启动会进入配置页，由用户手动填写 Web 地址。用户保存后的地址写入用户数据目录；切换地址时会清理 Electron session 的缓存、localStorage 和 cookies。

## 6. 验收清单

后端：

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
curl http://127.0.0.1:15050/api/system/health
```

外部入口：

```bash
curl https://app.example.com/api/system/health
```

浏览器验收：

- 打开 `https://app.example.com`；
- 完成首次初始化或登录；
- 主智能体对话可用；
- 上传、下载和 SSE/流式响应可用。

exe 壳验收：

- 解压免安装 zip；
- 通过同目录 `config.json` 或首次配置页打开同一 Web URL；
- 完成登录或初始化；
- 主智能体对话、上传、下载和流式响应可用。

本轮主验收不覆盖知识库管理、图谱管理和后台管理全量功能；这些能力仍应在后续全量等价矩阵中逐项审计。
