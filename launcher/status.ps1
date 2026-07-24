param([switch]$NoPause)
. (Join-Path $PSScriptRoot 'common.ps1')

$bridge = Get-BridgeProcess
$bridgeStatus = Read-JsonFile $BridgeStatusFile
$uiStatus = Read-JsonFile $UiStatusFile
$bridgeRunning = $null -ne $bridge
$uiRunning = Test-ProcessId $uiStatus.uiPid

Write-Host '=== Grayson电脑助手运行状态 ===' -ForegroundColor Cyan
Write-Host ("本地项目桥：{0}" -f $(if ($bridgeRunning) { "运行中（PID $($bridge.ProcessId)）" } else { '未运行' })) -ForegroundColor $(if ($bridgeRunning) { 'Green' } else { 'Red' })
Write-Host ("Windows UI：{0}" -f $(if ($uiRunning) { "运行中（PID $($uiStatus.uiPid)）" } else { '未运行' })) -ForegroundColor $(if ($uiRunning) { 'Green' } else { 'Red' })
Write-Host ("远程服务：{0}" -f $(if ($bridgeRunning -and $bridgeStatus.connected -eq $true) { '已连接' } elseif ($bridgeRunning) { '连接中/正在重连' } else { '离线' }))

if ($uiStatus -and $uiRunning) {
    $color = switch ($uiStatus.state) { 'active' { 'Green' } 'paused' { 'Yellow' } default { 'Red' } }
    $label = switch ($uiStatus.state) { 'active' { '绿色：允许远程控制' } 'paused' { '黄色：只允许查看' } default { '红色：已停止' } }
    Write-Host "控制状态：$label" -ForegroundColor $color
    Write-Host "紧急快捷键：$($uiStatus.emergencyHotkey)"
} else {
    Write-Host '控制状态：不可用（Windows UI 模块未运行）' -ForegroundColor Red
}

if ($uiRunning -and (Test-Path -LiteralPath $PythonExe)) {
    Push-Location $WindowsUiRoot
    try {
        $foreground = & $PythonExe -c "import json; from windows_ui.windows import foreground_window; print(json.dumps(foreground_window(), ensure_ascii=False))" 2>$null
        if ($foreground) {
            $fg = $foreground | ConvertFrom-Json
            Write-Host "当前前台窗口：$($fg.title) [$($fg.process), PID $($fg.pid)]"
        }
    } finally { Pop-Location }
}

$lastError = $bridgeStatus.lastError
if (-not $lastError) { $lastError = $uiStatus.lastError }
if (-not $lastError -and (Test-Path -LiteralPath $LogsDir)) {
    $latestErr = Get-ChildItem -LiteralPath $LogsDir -Filter 'bridge-*.err.log' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestErr) {
        $match = Select-String -LiteralPath $latestErr.FullName -Pattern 'error|failed|失败' -CaseSensitive:$false | Select-Object -Last 1
        if ($match) { $lastError = $match.Line }
    }
}
Write-Host "最近一次错误：$(if ($lastError) { $lastError } else { '无' })"
Write-Host "设备名称：$(if ($bridgeStatus.deviceName) { $bridgeStatus.deviceName } else { $env:COMPUTERNAME })"
Write-Host "远程端口：$(if ($bridgeStatus.remotePort) { $bridgeStatus.remotePort } else { '443（未连接）' })"
Write-Host "日志位置：$LogsDir"
