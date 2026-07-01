# Yuxi Web 前端应用壳

本目录是免安装 Windows Web URL 壳，不内置前端静态资源，也不注入桌面端运行时 API。它只用 Electron BrowserWindow 打开已经部署好的 Yuxi Web 地址。

## 配置

启动时按顺序读取：

1. exe 同目录的 `config.json`，适合交付人员预置服务器地址；
2. 用户数据目录里的 `config.json`，适合首次启动时由用户填写。

同目录 `config.json` 存在 `webUrl` 时优先级最高。用户在配置页保存地址时只写入用户数据目录，不修改 zip 解压目录。

## 构建

```powershell
cd packaging-1/windows/web-shell
pnpm install --no-frozen-lockfile
pnpm run dist:portable
```

也可以从仓库根目录执行：

```powershell
packaging-1/windows/scripts/build_web_shell_portable.ps1
```
