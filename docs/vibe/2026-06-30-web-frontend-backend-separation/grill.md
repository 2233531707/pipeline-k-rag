# 2026-06-30 Web 前后端分离部署 Grill

## 背景

本轮从 Electron 本地前端资源客户端方案切出一个更快的 Web 部署方向：优先让地下管网知识模型数据库以 Web 形式完成前后端分离交付。用户通过免安装 exe 壳或浏览器访问服务器上的 Web 前端入口，后端单独部署在服务器上并提供 API、Worker、数据库、对象存储、向量库、图数据库和沙盒运行能力。

## 当前目标草案

快速实现 Web 形式前后端分离：

- 后端服务部署在服务器。
- 前端以 Web 静态资源部署在服务器，并通过同域 Nginx 反向代理调用后端 API。
- 额外交付一个免安装 zip，其中 exe 只是 Web 前端应用壳，负责打开服务器 Web URL。
- 优先复用现有 Vue 前端和 Docker Compose 生产栈，少做新基础设施。

## 默认假设

- 本轮优先追求最快、最稳的前后端分离上线，而不是本地前端资源桌面化。
- 不引入安装器、自动更新或本地客户端诊断。
- exe 壳不内置前端静态资源，不使用 `kb-desktop://app`，不处理桌面端 token 安全存储。
- 不引入 Kubernetes、云市场镜像或复杂多环境发布系统。
- 不改变后端仍由 Docker Compose 管理的事实来源，除非后续 grill 明确推翻。

## 待 Grill 决策

1. Web 前后端分离是否采用“同域 Nginx 反向代理”作为最快默认方案，还是采用“前端静态站点独立域名 + 后端 API 域名”的强分离方案。
   - 已确认：先采用同域 Nginx 反向代理。
2. 免安装 zip 中的 exe 壳加载本地前端资源还是服务器 Web URL。
   - 已确认：先采用服务器 Web URL 壳，不把前端静态资源打入本地壳。
3. Web 前端应用壳采用什么技术。
   - 已确认：先使用 Electron BrowserWindow 壳打开服务器 Web URL，不使用默认浏览器启动器或 WebView2。
4. 服务器 Web URL 从哪里来。
   - 已确认：同时支持 zip 同目录 `config.json` 预置 URL，以及首次启动手动配置 URL；用户保存后的 URL 写入用户数据目录，不改 zip 解压目录。
5. Web 壳里的登录态怎么处理。
   - 已确认：Web 前端应用壳按普通 Web 模式运行，不启用桌面端 token 安全存储，不注入桌面运行时 API；切换服务器时清理当前 Electron session 的缓存、localStorage 和 cookies。
6. 前端构建产物是否仍由 `docker/web.Dockerfile` 和 Nginx 容器承载，还是输出纯静态包给外部 Nginx/CDN。
   - 已确认：前端静态资源交给外部 Nginx/CDN，不继续把生产 `web` 容器作为默认前端入口；后端服务器提供 API/Worker/数据服务等能力。
7. 后端生产部署是否继续以 `docker-compose.prod.yml` 为唯一事实来源。
   - 已确认：先保留生产 `web` 服务，不立即拆 Compose；外部 Nginx/CDN 作为新增部署模式记录，`web` 容器可用于本机验收、兜底和旧部署兼容。
8. 外部 Nginx/CDN 前端如何调用后端 API。
   - 已确认：采用同一前端域名下 `/api` 反代到后端，不让前端直接跨域请求独立 API 域名；外部 Nginx/CDN 需对 `/api` 禁用缓存、支持 SSE/流式和大文件上传。
9. 外部 Nginx 的 `/api` 反代目标。
   - 已确认：外部 Nginx 的 `/api` 直接反代到后端 API 服务，不反代到后端服务器上的 `web` Nginx 容器。
10. 前端构建产物里的 API 地址是否可配置。
   - 已确认：保持前端同源 `/api` 语义，不引入构建时 API Base URL 配置；外部 Nginx 负责把 `/api` 反代到后端 API。
11. 后端 API 端口是否公网开放。
   - 已确认：后端 API 端口只允许外部 Nginx 访问，不直接公网开放；公网统一从前端域名的 `/api` 进入。
12. 前端静态资源如何交付给外部 Nginx/CDN。
   - 已确认：第三轮产出版本化前端静态 zip 包，包含 `web/dist` 静态资源、`version.json`、`README.txt` 和 `nginx.example.conf`，而不是只让交付人员手动拷贝 `web/dist`。
13. CORS 是否尽量避免，还是显式配置跨域访问。
   - 已确认：本轮主路径避免 CORS，采用同源 `/api` 反代；跨域 API 域名只作为非推荐分支记录，不纳入主验收。
14. 本轮实现产物具体有哪些。
   - 已确认：锁定为前端静态 zip 构建脚本、外部 Nginx 示例配置、Electron BrowserWindow URL 壳、后端配套部署文档；不碰业务功能代码。
15. 本轮验收主链路。
   - 已确认：覆盖后端 `docker-compose.prod.yml` 启动 API/Worker/数据服务、外部 Nginx/CDN 部署前端静态 zip 解压内容、同源 `/api` 直接反代后端 API、API 端口仅允许外部 Nginx 访问、浏览器访问 Web 前端、exe 壳启动同一 Web URL、登录/初始化、主智能体对话、上传下载、SSE/流式响应和健康检查；本轮不做知识库管理、图谱管理、后台管理全量验收。
16. Web 前端应用壳实现目录。
   - 已确认：新建独立目录承载 URL 壳实现；后续进一步收敛为放入 `packaging-1/windows/web-shell/`，不复用现有 `packaging/windows/electron/`，避免与 Electron 本地前端资源客户端混用。
17. 前端静态 zip 构建脚本目录。
   - 已确认：新建 `packaging-1/web-static/` 承载前端静态 zip 构建脚本、外部 Nginx 示例配置和静态包说明；它是 Web 部署产物，不绑定 Windows URL 壳。
18. 后端服务器部署说明是否进入正式用户文档。
   - 已确认：新增正式文档 `docs/advanced/web-separated-deployment.md`，并同步更新 `docs/.vitepress/config.mts` 导航；该文档作为交付人员可复用的前后端分离部署方案，不只保存在 `docs/vibe` 过程记录中。
19. 本轮实现完成后是否直接提交并推送。
   - 已确认：实现、验证通过后直接提交并推送到当前分支，保证 GitHub 可见并方便后续任务接续。

## 当前不做

- Electron 本地前端资源绿色版。
- 客户端内置后端。
- 桌面端安全存储。
- 本地 Docker 管理。
- 自动更新。
- WebView2 壳。
- 只调用系统默认浏览器的启动器。

## 本轮落地结果

- 新增 `packaging-1/web-static/`，用于构建版本化前端静态 zip，并提供外部 Nginx 示例配置。
- 新增 `packaging-1/windows/web-shell/`，实现 Electron BrowserWindow Web URL 壳。
- 新增 `packaging-1/windows/scripts/build_web_shell_portable.ps1`，用于构建 Web URL 壳 portable exe。
- 新增正式文档 `docs/advanced/web-separated-deployment.md`，并加入 VitePress 高级配置导航。
- 更新 `CONTEXT.md`，补充 Web 前后端分离部署、Web 前端应用壳和 Web 前端能力桌面化全量等价三个术语。

## 验证记录

- `node --check packaging-1/windows/web-shell/main.js`
- `node --check packaging-1/windows/web-shell/preload.js`
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File packaging-1/web-static/build-static-package.ps1 -SkipBuild`
- `pnpm --dir docs run build`
- `pnpm --dir packaging-1/windows/web-shell run dist:portable`
- `git diff --check`
