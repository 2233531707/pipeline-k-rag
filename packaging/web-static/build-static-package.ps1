param(
    [string]$OutputDir = (Join-Path $PSScriptRoot "dist"),
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path (Join-Path $PSScriptRoot "..") "..")
$WebDir = Join-Path $RepoRoot "web"
$WebDist = Join-Path $WebDir "dist"
$PackageJsonPath = Join-Path $WebDir "package.json"
$NginxExample = Join-Path $PSScriptRoot "nginx.example.conf"
$ReadmeTemplate = Join-Path $PSScriptRoot "README.txt"

if (-not (Test-Path $PackageJsonPath)) {
    throw "web/package.json not found: $PackageJsonPath"
}

$WebPackage = Get-Content $PackageJsonPath -Raw | ConvertFrom-Json
$Version = $WebPackage.version
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$PackageName = "yuxi-web-static-$Version-$Timestamp.zip"
$OutputPath = Join-Path $OutputDir $PackageName
$StageDir = Join-Path $OutputDir "_stage"

if (-not $SkipBuild) {
    Push-Location $WebDir
    try {
        npx -y pnpm@10.11.0 install --frozen-lockfile
        npx -y pnpm@10.11.0 run build
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path (Join-Path $WebDist "index.html"))) {
    throw "web/dist/index.html not found. Run the script without -SkipBuild or build web first."
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
if (Test-Path $StageDir) {
    Remove-Item $StageDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $StageDir | Out-Null

Copy-Item (Join-Path $WebDist "*") $StageDir -Recurse -Force
Copy-Item $NginxExample (Join-Path $StageDir "nginx.example.conf") -Force
Copy-Item $ReadmeTemplate (Join-Path $StageDir "README.txt") -Force

$VersionInfo = [ordered]@{
    name = "yuxi-web-static"
    version = $Version
    builtAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    apiMode = "same-origin /api reverse proxy"
}
$VersionInfo | ConvertTo-Json | Set-Content (Join-Path $StageDir "version.json") -Encoding UTF8

if (Test-Path $OutputPath) {
    Remove-Item $OutputPath -Force
}
Compress-Archive -Path (Join-Path $StageDir "*") -DestinationPath $OutputPath -Force
Remove-Item $StageDir -Recurse -Force

Write-Host "Created $OutputPath"
