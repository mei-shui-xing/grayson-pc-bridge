$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$ConfigPath = Join-Path $PSScriptRoot 'assistant.config.json'
if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "缺少配置文件：$ConfigPath"
}
$AssistantConfig = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$configuredProjectRoot = [Environment]::ExpandEnvironmentVariables([string]$AssistantConfig.project_root)
$repoCandidate = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..') -ErrorAction SilentlyContinue).Path
if ($configuredProjectRoot -and (Test-Path -LiteralPath (Join-Path $configuredProjectRoot 'package.json'))) {
    $ProjectRoot = (Resolve-Path -LiteralPath $configuredProjectRoot).Path
} elseif ($repoCandidate -and (Test-Path -LiteralPath (Join-Path $repoCandidate 'package.json'))) {
    $ProjectRoot = $repoCandidate
} else {
    throw '找不到 AI Desktop Control Bridge 项目目录。请从仓库内运行，或在 assistant.config.json 中填写 project_root。'
}
$DefaultDesktopFolder = Join-Path ([Environment]::GetFolderPath('Desktop')) 'AI电脑助手'
$LegacyDesktopFolder = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Grayson电脑助手'
$DesktopFolder = [Environment]::ExpandEnvironmentVariables([string]$AssistantConfig.desktop_folder)
if (-not $DesktopFolder) {
    $DesktopFolder = $DefaultDesktopFolder
}
$WindowsUiRoot = Join-Path $ProjectRoot 'windows-ui'
$RuntimeDir = Join-Path $WindowsUiRoot 'runtime'
$LogsDir = Join-Path $DesktopFolder 'logs'
$PythonExe = Join-Path $WindowsUiRoot '.venv\Scripts\python.exe'
$NodeEntry = Join-Path $ProjectRoot 'dist\index.js'
$PidFile = Join-Path $RuntimeDir 'bridge.pid'
$BridgeStatusFile = Join-Path $RuntimeDir 'bridge-status.json'
$UiStatusFile = Join-Path $RuntimeDir 'ui-status.json'
$StopRequestFile = Join-Path $RuntimeDir 'stop-request.json'

function Get-BridgeProcess {
    if (-not (Test-Path -LiteralPath $PidFile)) { return $null }
    $processIdText = (Get-Content -LiteralPath $PidFile -Raw -ErrorAction SilentlyContinue).Trim()
    if ($processIdText -notmatch '^\d+$') { return $null }
    $candidate = Get-CimInstance Win32_Process -Filter "ProcessId=$processIdText" -ErrorAction SilentlyContinue
    if (-not $candidate) { return $null }
    $escapedRoot = [Regex]::Escape($ProjectRoot)
    if ($candidate.Name -ne 'node.exe' -or $candidate.CommandLine -notmatch $escapedRoot -or $candidate.CommandLine -notmatch '\bremote\b') {
        return $null
    }
    return $candidate
}

function Read-JsonFile([string]$Path) {
    try {
        if (Test-Path -LiteralPath $Path) {
            return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
        }
    } catch { }
    return $null
}

function Test-ProcessId([object]$ProcessIdValue) {
    if ($null -eq $ProcessIdValue -or "$ProcessIdValue" -notmatch '^\d+$') { return $false }
    return $null -ne (Get-Process -Id ([int]$ProcessIdValue) -ErrorAction SilentlyContinue)
}

function Get-WindowsUiProcess {
    $uiStatus = Read-JsonFile $UiStatusFile
    if (-not (Test-ProcessId $uiStatus.uiPid)) { return $null }
    $candidate = Get-CimInstance Win32_Process -Filter "ProcessId=$($uiStatus.uiPid)" -ErrorAction SilentlyContinue
    if (-not $candidate) { return $null }
    # uv-created venv launchers replace themselves with the managed Python
    # binary, so the final child command line may not contain WindowsUiRoot.
    # The PID comes from our private runtime status file; validate the module.
    if ($candidate.Name -ne 'python.exe' -or $candidate.CommandLine -notmatch 'windows_ui\.server') {
        return $null
    }
    return $candidate
}

function Get-ScreenshotHealth {
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        return [pscustomobject]@{ ok = $false; error = 'Python 虚拟环境不存在' }
    }
    Push-Location $WindowsUiRoot
    try {
        $raw = & $PythonExe -m windows_ui.health 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $raw) {
            return [pscustomobject]@{ ok = $false; error = '截图探针执行失败' }
        }
        return $raw | ConvertFrom-Json
    } catch {
        return [pscustomobject]@{ ok = $false; error = $_.Exception.Message }
    } finally {
        Pop-Location
    }
}
