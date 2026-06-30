$ErrorActionPreference = "Stop"

$WindowsDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$ElectronDir = Join-Path $WindowsDir "electron"

Push-Location $ElectronDir
try {
    $env:CI = "true"
    pnpm install --no-frozen-lockfile
    pnpm run dist:portable
}
finally {
    Pop-Location
}
