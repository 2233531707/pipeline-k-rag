$ErrorActionPreference = "Stop"

$WindowsDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$WebShellDir = Join-Path $WindowsDir "web-shell"

Push-Location $WebShellDir
try {
    $env:CI = "true"
    pnpm install --no-frozen-lockfile
    pnpm run dist:portable
}
finally {
    Pop-Location
}
