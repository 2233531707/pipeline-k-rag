param([switch]$Pull)
$ErrorActionPreference = "Stop"
$WindowsDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$RepoRoot = Resolve-Path (Join-Path $WindowsDir "..\..")
$Output = Join-Path $WindowsDir "bundle\images\yuxi-images.tar"
Push-Location $RepoRoot
try {
    $Images = docker compose config --images | Sort-Object -Unique
    if ($Pull) {
        foreach ($Image in $Images) { docker pull $Image }
    }
    docker save -o $Output $Images
    Write-Host "Images exported: $Output"
}
finally { Pop-Location }
