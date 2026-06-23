param([switch]$Install)
$ErrorActionPreference = "Stop"
$WindowsDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$Installer = Join-Path $WindowsDir "dist\地下管网知识模型数据库.exe"
if (-not (Test-Path $Installer)) { throw "Installer not found: $Installer" }
if ((Get-Item $Installer).Length -lt 1MB) { throw "Installer is unexpectedly small" }
Write-Host "Installer artifact verified: $Installer"

if ($Install) {
    $Target = Join-Path $env:TEMP "PipelineKnowledgeModelInstallerTest"
    if (Test-Path $Target) { Remove-Item $Target -Recurse -Force }
    $InstallProcess = Start-Process -FilePath $Installer -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/DIR=`"$Target`"") -Wait -PassThru
    if ($InstallProcess.ExitCode -ne 0) { throw "Silent install failed: $($InstallProcess.ExitCode)" }
    if (-not (Test-Path (Join-Path $Target "地下管网知识模型数据库启动器.exe"))) {
        throw "Launcher missing after installation"
    }
    if (-not (Test-Path (Join-Path $Target "地下管网知识模型数据库-使用教程.txt"))) {
        throw "User guide missing after installation"
    }
    $RequiredRuntimeFiles = @(
        "app\docker-compose.desktop.yml",
        "app\docker\api.Dockerfile",
        "app\backend\package\yuxi\__init__.py",
        "app\web\package.json"
    )
    foreach ($File in $RequiredRuntimeFiles) {
        if (-not (Test-Path (Join-Path $Target $File))) { throw "Runtime file missing: $File" }
    }
    if (Test-Path (Join-Path $Target "app\.git")) {
        throw "Git metadata must not be included in the installer"
    }
    if (Test-Path (Join-Path $Target "app\.env")) {
        throw "Local environment configuration must not be included in the installer"
    }
    if (Test-Path (Join-Path $Target "app\backend\test\data")) {
        throw "Test data must not be included in the installer"
    }
    Write-Host "Silent installation verified: $Target"
}
