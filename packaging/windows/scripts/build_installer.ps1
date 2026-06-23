$ErrorActionPreference = "Stop"
$WindowsDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$RepoRoot = Resolve-Path (Join-Path $WindowsDir "..\..")
$Stage = Join-Path $WindowsDir "bundle\app"
$Launcher = Join-Path $WindowsDir "dist\launcher\YuxiDesktopLauncher.exe"

if (-not (Test-Path $Launcher)) { & (Join-Path $PSScriptRoot "build_launcher.ps1") }
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item $Stage -ItemType Directory | Out-Null

$SystemRobocopy = Join-Path $env:SystemRoot "System32\robocopy.exe"
$Robocopy = if (Test-Path $SystemRobocopy) { $SystemRobocopy } else { (Get-Command robocopy.exe -ErrorAction Stop).Source }

$RuntimeDirectories = @("backend", "docker", "web")
$ExcludedDirectories = @(
    "__pycache__", ".pytest_cache", ".ruff_cache", ".venv",
    "node_modules", "dist", "volumes", ".pnpm-store", "test",
    "*.egg-info"
)
$ExcludedFiles = @(
    "*.pyc", "*.pyo", "*.log", "*.tmp", "*.db", "*.sqlite", "*.sqlite3",
    "*.yuxikb.zip", "*.tar", "*.tar.gz", ".env*",
    ".eslintcache"
)

foreach ($Directory in $RuntimeDirectories) {
    $Source = Join-Path $RepoRoot $Directory
    $Destination = Join-Path $Stage $Directory
    $RobocopyArgs = @(
        $Source, $Destination, "/E", "/R:1", "/W:1",
        "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/XD"
    ) + $ExcludedDirectories + @("/XF") + $ExcludedFiles
    $Copy = Start-Process -FilePath $Robocopy -ArgumentList $RobocopyArgs `
        -Wait -PassThru -NoNewWindow
    if ($Copy.ExitCode -ge 8) {
        throw "robocopy failed for $Directory with exit code $($Copy.ExitCode)"
    }
}

$RuntimeFiles = @(".dockerignore", ".env.template", "docker-compose.desktop.yml", "LICENSE", "README.md")
foreach ($File in $RuntimeFiles) {
    Copy-Item (Join-Path $RepoRoot $File) (Join-Path $Stage $File) -Force
}

$DataDirectories = @(
    "backend\test",
    "docker\volumes\yuxi",
    "docker\volumes\models",
    "docker\volumes\neo4j\data",
    "docker\volumes\neo4j\logs",
    "docker\volumes\milvus\etcd",
    "docker\volumes\milvus\minio",
    "docker\volumes\milvus\minio_config",
    "docker\volumes\milvus\milvus",
    "docker\volumes\milvus\logs",
    "docker\volumes\redis",
    "docker\volumes\paddlex"
)
foreach ($Directory in $DataDirectories) {
    New-Item (Join-Path $Stage $Directory) -ItemType Directory -Force | Out-Null
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
foreach ($Directory in $RuntimeDirectories) {
    $Archive = Join-Path $WindowsDir "bundle\$Directory.zip"
    if (Test-Path $Archive) { Remove-Item $Archive -Force }
    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        (Join-Path $Stage $Directory),
        $Archive,
        [System.IO.Compression.CompressionLevel]::Optimal,
        $true
    )
    if (-not (Test-Path $Archive)) { throw "Runtime archive was not created: $Archive" }
}

$ArchiveRequirements = @{
    backend = "backend/package/yuxi/__init__.py"
    docker = "docker/api.Dockerfile"
    web = "web/package.json"
}
foreach ($Directory in $RuntimeDirectories) {
    $Zip = [System.IO.Compression.ZipFile]::OpenRead((Join-Path $WindowsDir "bundle\$Directory.zip"))
    $EntryNames = $Zip.Entries | ForEach-Object { $_.FullName.Replace("\", "/") }
    $Found = $EntryNames -contains $ArchiveRequirements[$Directory]
    $Zip.Dispose()
    if (-not $Found) { throw "Runtime archive is incomplete: $Directory.zip" }
}

$LocalIscc = Join-Path $WindowsDir ".inno\ISCC.exe"
$Iscc = if (Test-Path $LocalIscc) { Get-Item $LocalIscc } else { Get-Command ISCC.exe -ErrorAction SilentlyContinue }
if (-not $Iscc) {
    $DefaultIscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $DefaultIscc) { $Iscc = Get-Item $DefaultIscc }
}
if (-not $Iscc) { throw "Inno Setup 6 ISCC.exe not found" }

$LegacyInstaller = Join-Path $WindowsDir "dist\Yuxi-Desktop-Setup.exe"
if (Test-Path $LegacyInstaller) { Remove-Item $LegacyInstaller -Force }

$IsccPath = if ($Iscc -is [System.IO.FileInfo]) { $Iscc.FullName } else { [string]$Iscc }
$Compile = Start-Process -FilePath $IsccPath `
    -ArgumentList @((Join-Path $WindowsDir "installer\yuxi.iss")) `
    -Wait -PassThru -NoNewWindow
if ($Compile.ExitCode -ne 0) { throw "Inno Setup failed with exit code $($Compile.ExitCode)" }

$Installer = Join-Path $WindowsDir "dist\地下管网知识模型数据库.exe"
if (-not (Test-Path $Installer)) { throw "Installer was not created: $Installer" }
$Guide = Join-Path $WindowsDir "地下管网知识模型数据库-使用教程.txt"
Copy-Item $Guide (Join-Path $WindowsDir "dist\地下管网知识模型数据库-使用教程.txt") -Force
Write-Host "Installer built: $Installer"
