$ErrorActionPreference = "Stop"
$WindowsDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$RepoRoot = Resolve-Path (Join-Path $WindowsDir "..\..")
$Stage = Join-Path $WindowsDir "bundle\app"
$Launcher = Join-Path $WindowsDir "dist\launcher\YuxiDesktopLauncher.exe"

if (-not (Test-Path $Launcher)) { & (Join-Path $PSScriptRoot "build_launcher.ps1") }
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item $Stage -ItemType Directory | Out-Null

$Excluded = @(".git", ".venv", "node_modules", "saves", "logs", "packaging", "recovery-backups")
$SystemRobocopy = Join-Path $env:SystemRoot "System32\robocopy.exe"
$Robocopy = if (Test-Path $SystemRobocopy) { $SystemRobocopy } else { (Get-Command robocopy.exe -ErrorAction Stop).Source }
$null = & $Robocopy $RepoRoot $Stage /E /XD $Excluded /XF .env
if ($LASTEXITCODE -ge 8) { throw "robocopy failed with exit code $LASTEXITCODE" }

$LocalIscc = Join-Path $WindowsDir ".inno\ISCC.exe"
$Iscc = if (Test-Path $LocalIscc) { Get-Item $LocalIscc } else { Get-Command ISCC.exe -ErrorAction SilentlyContinue }
if (-not $Iscc) {
    $DefaultIscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $DefaultIscc) { $Iscc = Get-Item $DefaultIscc }
}
if (-not $Iscc) { throw "Inno Setup 6 ISCC.exe not found" }
& $Iscc (Join-Path $WindowsDir "installer\yuxi.iss")
