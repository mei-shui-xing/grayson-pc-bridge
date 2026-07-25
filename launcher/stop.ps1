. (Join-Path $PSScriptRoot 'common.ps1')

New-Item -ItemType Directory -Force -Path $RuntimeDir, $LogsDir | Out-Null
Write-Host '=== 停止 AI电脑助手 ===' -ForegroundColor Cyan
$bridge = Get-BridgeProcess
$uiStatus = Read-JsonFile $UiStatusFile

if (Test-ProcessId $uiStatus.uiPid) {
    Write-Host '1/4 暂停远程鼠标键盘……'
    Push-Location $WindowsUiRoot
    try {
        & $PythonExe -m windows_ui.cli pause | Out-Host
        if ($LASTEXITCODE -ne 0) { Write-Host '暂停命令未确认，仍将关闭本助手。' -ForegroundColor Yellow }
    } finally { Pop-Location }
} else {
    Write-Host '1/4 UI 模块未运行。'
}

if ($bridge) {
    Write-Host "2/4 请求设备端正常退出（PID $($bridge.ProcessId)）……"
    @{ requestedAt = (Get-Date).ToString('o'); requesterPid = $PID } | ConvertTo-Json | Set-Content -LiteralPath $StopRequestFile -Encoding UTF8
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline -and (Get-Process -Id $bridge.ProcessId -ErrorAction SilentlyContinue)) {
        Start-Sleep -Milliseconds 300
    }
    if (Get-Process -Id $bridge.ProcessId -ErrorAction SilentlyContinue) {
        Write-Host '正常退出超时，只终止本助手自己的进程树。' -ForegroundColor Yellow
        $all = Get-CimInstance Win32_Process
        $targets = New-Object System.Collections.Generic.List[int]
        $queue = New-Object System.Collections.Generic.Queue[int]
        $queue.Enqueue([int]$bridge.ProcessId)
        while ($queue.Count -gt 0) {
            $parentId = $queue.Dequeue()
            $targets.Add($parentId)
            foreach ($child in $all | Where-Object { $_.ParentProcessId -eq $parentId }) {
                $queue.Enqueue([int]$child.ProcessId)
            }
        }
        foreach ($targetId in ($targets | Sort-Object -Descending)) {
            Stop-Process -Id $targetId -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host '3/4 本地项目桥和 UI 模块已停止。' -ForegroundColor Green
} else {
    Write-Host '2/4 本地项目桥未运行。'
    Write-Host '3/4 无需关闭服务。'
}

Remove-Item -LiteralPath $PidFile, $StopRequestFile -Force -ErrorAction SilentlyContinue
Write-Host '4/4 已清理本助手 PID 文件；没有关闭其他 Python、Node 或终端进程。'
Write-Host "日志位置：$LogsDir"
