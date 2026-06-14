param([switch]$Install)
$ErrorActionPreference = "Stop"
$WindowsDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$Installer = Join-Path $WindowsDir "dist\Yuxi-Desktop-Setup.exe"
if (-not (Test-Path $Installer)) { throw "Installer not found: $Installer" }
if ((Get-Item $Installer).Length -lt 1MB) { throw "Installer is unexpectedly small" }
Write-Host "Installer artifact verified: $Installer"

if ($Install) {
    $Target = Join-Path $env:TEMP "YuxiDesktopInstallerTest"
    $InstallProcess = Start-Process -FilePath $Installer -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/DIR=`"$Target`"") -Wait -PassThru
    if ($InstallProcess.ExitCode -ne 0) { throw "Silent install failed: $($InstallProcess.ExitCode)" }
    if (-not (Test-Path (Join-Path $Target "YuxiDesktopLauncher.exe"))) {
        throw "Launcher missing after installation"
    }
    Write-Host "Silent installation verified: $Target"
}
