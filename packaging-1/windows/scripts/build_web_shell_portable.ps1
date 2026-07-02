param(
    [string]$OutputDir = (Join-Path (Join-Path $PSScriptRoot "..") "dist")
)

$ErrorActionPreference = "Stop"

$WindowsDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$WebShellDir = Join-Path $WindowsDir "web-shell"
$PackageJsonPath = Join-Path $WebShellDir "package.json"
$BuilderOutputDir = Join-Path $OutputDir "web-shell"
$ZipStageDir = Join-Path $OutputDir "_web-shell-zip"

if (-not (Test-Path $PackageJsonPath)) {
    throw "web-shell/package.json not found: $PackageJsonPath"
}

$PackageJson = Get-Content $PackageJsonPath -Raw | ConvertFrom-Json
$Version = $PackageJson.version
$ZipPath = Join-Path $OutputDir "yuxi-web-frontend-exe-$Version.zip"
$RootExeName = "地下管网知识模型数据库 Web 入口.exe"
$PnpmCommand = if ($env:YUXI_PNPM_CMD) { $env:YUXI_PNPM_CMD } else { "pnpm" }

function Invoke-Pnpm {
    param([string]$Arguments)

    $process = Start-Process -FilePath $PnpmCommand -ArgumentList $Arguments -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 0) {
        throw "pnpm $Arguments failed with exit code $($process.ExitCode)"
    }
}

Push-Location $WebShellDir
try {
    $env:CI = "true"
    Invoke-Pnpm "install --no-frozen-lockfile"
    Invoke-Pnpm "run dist:portable"
}
finally {
    Pop-Location
}

$PortableExe = Get-ChildItem -Path $BuilderOutputDir -Filter "*.exe" -File |
    Where-Object { $_.Name -notlike "elevate.exe" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $PortableExe) {
    throw "Portable exe not found in $BuilderOutputDir"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
if (Test-Path $ZipStageDir) {
    Remove-Item $ZipStageDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $ZipStageDir | Out-Null

Copy-Item $PortableExe.FullName (Join-Path $ZipStageDir $RootExeName) -Force
Copy-Item (Join-Path $WebShellDir "config.sample.json") (Join-Path $ZipStageDir "config.sample.json") -Force

@"
地下管网知识模型数据库 Web 入口

使用方法：
1. 解压 zip。
2. 双击当前目录下的「$RootExeName」。
3. 首次启动时填写已部署好的 Web 地址，例如 https://app.example.com。

可选预置：
- 如需交付时预置地址，请复制 config.sample.json 为 config.json，并把 webUrl 改成真实 Web 地址。
- 不要把前端静态资源放进这个 zip；此前端 exe 只负责打开服务器 Web URL。
"@ | Set-Content (Join-Path $ZipStageDir "README.txt") -Encoding UTF8

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path (Join-Path $ZipStageDir "*") -DestinationPath $ZipPath -Force
Remove-Item $ZipStageDir -Recurse -Force

Write-Host "Created $ZipPath"
