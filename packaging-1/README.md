# Web 前后端分离交付

本目录独立承载 Web 前后端分离交付产物，避免与既有 `packaging/` 下的 Electron 本地前端资源客户端混用。

## 目录

- `web-static/`：前端静态 zip 构建脚本、外部 Nginx 示例配置和静态包说明。
- `windows/web-shell/`：Electron BrowserWindow Web URL 壳工程。
- `windows/scripts/`：Web URL 壳构建脚本。

## 构建入口

- 前端静态 zip：`packaging-1/web-static/build-static-package.ps1`
- Web 前端 exe 交付 zip：`packaging-1/windows/scripts/build_web_shell_portable.ps1`

`build_web_shell_portable.ps1` 会生成可直接交付的 zip。用户解压后，当前目录下会直接出现 `地下管网知识模型数据库 Web 入口.exe`，无需安装，也无需再次构建。
