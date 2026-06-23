$ErrorActionPreference = "Stop"
$WindowsDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$LauncherDir = Join-Path $WindowsDir "launcher"
$DistDir = Join-Path $WindowsDir "dist\launcher"
$VenvDir = Join-Path $WindowsDir ".build-venv"

if (-not (Test-Path $VenvDir)) {
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        & $PyLauncher.Source -3.12 -m venv $VenvDir
    }
    else {
        $SystemPython = Get-Command python -ErrorAction SilentlyContinue
        $PythonCandidates = @(
            (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
            $(if ($SystemPython) { $SystemPython.Source }),
            "D:\Anaconda3\python.exe"
        ) | Where-Object { $_ -and (Test-Path $_) }

        if (-not $PythonCandidates) {
            throw "未找到可用的 Windows Python。请安装 Python 3.12，或将 python/py 加入 PATH。"
        }
        $PythonCommand = $PythonCandidates | Select-Object -First 1
        $VenvProcess = Start-Process -FilePath $PythonCommand `
            -ArgumentList @("-m", "venv", $VenvDir) `
            -Wait -PassThru -NoNewWindow
        if ($VenvProcess.ExitCode -ne 0) {
            throw "创建 Windows 构建虚拟环境失败，退出码：$($VenvProcess.ExitCode)"
        }
    }
}
$Python = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Windows 构建虚拟环境创建失败：$VenvDir"
}

function Invoke-Python([string[]]$Arguments, [string]$Description) {
    $Process = Start-Process -FilePath $Python -ArgumentList $Arguments `
        -Wait -PassThru -NoNewWindow
    if ($Process.ExitCode -ne 0) {
        throw "$Description 失败，退出码：$($Process.ExitCode)"
    }
}

Invoke-Python @("-m", "pip", "install", "--upgrade", "pip") "升级 pip"
Invoke-Python @("-m", "pip", "install", "-r", (Join-Path $LauncherDir "requirements.txt")) "安装启动器构建依赖"
Invoke-Python @(
    "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
    "--name", "YuxiDesktopLauncher",
    "--distpath", $DistDir,
    "--workpath", (Join-Path $WindowsDir "build\launcher"),
    "--specpath", (Join-Path $WindowsDir "build"),
    (Join-Path $LauncherDir "main.py")
) "构建启动器"
Write-Host "Launcher built: $DistDir\YuxiDesktopLauncher.exe"
