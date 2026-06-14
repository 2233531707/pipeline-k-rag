$ErrorActionPreference = "Stop"
$WindowsDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$LauncherDir = Join-Path $WindowsDir "launcher"
$DistDir = Join-Path $WindowsDir "dist\launcher"
$VenvDir = Join-Path $WindowsDir ".build-venv"

if (-not (Test-Path $VenvDir)) {
    py -3.12 -m venv $VenvDir
}
$Python = Join-Path $VenvDir "Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $LauncherDir "requirements.txt")
& $Python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name YuxiDesktopLauncher `
    --distpath $DistDir `
    --workpath (Join-Path $WindowsDir "build\launcher") `
    --specpath (Join-Path $WindowsDir "build") `
    (Join-Path $LauncherDir "main.py")
Write-Host "Launcher built: $DistDir\YuxiDesktopLauncher.exe"
