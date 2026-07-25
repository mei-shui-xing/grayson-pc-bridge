. (Join-Path $PSScriptRoot 'common.ps1')

New-Item -ItemType Directory -Force -Path $DesktopFolder, $LogsDir, $RuntimeDir | Out-Null
$launcherLog = Join-Path $LogsDir ("launcher-{0:yyyy-MM-dd}.log" -f (Get-Date))
Start-Transcript -LiteralPath $launcherLog -Append | Out-Null

try {
    Write-Host '=== AI电脑助手启动检查 ===' -ForegroundColor Cyan
    if (-not (Test-Path -LiteralPath $ProjectRoot)) { throw "项目不存在：$ProjectRoot" }
    if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) { throw '未找到 Node.js。请安装 Node.js 18 或更高版本。' }
    $nodeMajor = [int]((& node.exe --version).TrimStart('v').Split('.')[0])
    if ($nodeMajor -lt 18) { throw "Node.js 版本过低：$nodeMajor。需要 18 或更高版本。" }
    if (-not (Test-Path -LiteralPath $PythonExe)) { throw 'Python 虚拟环境缺失。请双击“安装或修复依赖.bat”。' }
    if (-not (Test-Path -LiteralPath $NodeEntry)) { throw '本地项目桥尚未构建。请双击“安装或修复依赖.bat”。' }
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'node_modules'))) { throw 'Node 依赖缺失。请双击“安装或修复依赖.bat”。' }

    $existing = Get-BridgeProcess
    if ($existing) {
        $existingUi = Get-WindowsUiProcess
        if ($existingUi) {
            Write-Host "电脑助手已经完整运行（Node PID $($existing.ProcessId)，Windows UI PID $($existingUi.ProcessId)），不会重复启动。" -ForegroundColor Yellow
            & (Join-Path $PSScriptRoot 'status.ps1') -NoPause
            exit 0
        }

        Write-Host "检测到 Node 主桥仍在运行，但 Windows UI 侧车缺失；将只重启本助手进程树以恢复完整能力。" -ForegroundColor Yellow
        & (Join-Path $PSScriptRoot 'stop.ps1')
        $existing = Get-BridgeProcess
        if ($existing) { throw "旧 Node 主桥未能退出（PID $($existing.ProcessId)）。" }
    }

    $legacy = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq 'node.exe' -and $_.CommandLine -match '@wonderwhy-er[\\/]desktop-commander' -and $_.CommandLine -match '\bremote\b'
    }
    if ($legacy) {
        throw '检测到旧版 Desktop Commander Remote 仍在运行。请先在旧窗口按 Ctrl+C，或关闭旧窗口，再重新双击启动。'
    }

    Remove-Item -LiteralPath $StopRequestFile -Force -ErrorAction SilentlyContinue
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $bridgeOut = Join-Path $LogsDir "bridge-$stamp.out.log"
    $bridgeErr = Join-Path $LogsDir "bridge-$stamp.err.log"

    $env:DC_WINDOWS_UI_PYTHON = $PythonExe
    $env:DC_WINDOWS_UI_ROOT = $WindowsUiRoot
    $env:DC_WINDOWS_UI_REQUIRED = 'true'
    $env:WINDOWS_UI_CONFIG = Join-Path $WindowsUiRoot 'config\allowlist.json'
    $env:WINDOWS_UI_RUNTIME_DIR = $RuntimeDir
    $env:WINDOWS_UI_LOG_DIR = $LogsDir
    $env:AI_DESKTOP_CONTROL_BRIDGE_RUNTIME_DIR = $RuntimeDir
    $env:GRAYSON_ASSISTANT_RUNTIME_DIR = $RuntimeDir

    $bridge = Start-Process -FilePath (Get-Command node.exe).Source `
        -ArgumentList @($NodeEntry, 'remote', '--persist-session') `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $bridgeOut `
        -RedirectStandardError $bridgeErr `
        -PassThru -WindowStyle Hidden
    Set-Content -LiteralPath $PidFile -Value $bridge.Id -Encoding ASCII
    Write-Host "已启动本地项目桥（PID $($bridge.Id)），正在等待远程连接和 Windows UI 模块……"

    $deadline = (Get-Date).AddMinutes(3)
    $authHintShown = $false
    while ((Get-Date) -lt $deadline) {
        if ($bridge.HasExited) {
            $lastError = if (Test-Path $bridgeErr) { Get-Content -LiteralPath $bridgeErr -Tail 20 -Encoding UTF8 } else { '无错误日志' }
            throw "设备端启动失败。最近日志：`n$($lastError -join "`n")"
        }
        $bridgeStatus = Read-JsonFile $BridgeStatusFile
        $uiStatus = Read-JsonFile $UiStatusFile
        if ($bridgeStatus -and $bridgeStatus.bridgePid -eq $bridge.Id -and $bridgeStatus.connected -eq $true -and (Get-WindowsUiProcess)) {
            $screenshotHealth = Get-ScreenshotHealth
            if (-not $screenshotHealth.ok) {
                throw "Windows UI 已启动，但截图健康检查失败：$($screenshotHealth.error)"
            }
            Write-Host ''
            Write-Host '🟢 Windows UI：允许远程控制' -ForegroundColor Green
            Write-Host "设备名称：$($bridgeStatus.deviceName)"
            Write-Host "远程状态：在线（HTTPS/WSS 端口 $($bridgeStatus.remotePort)）"
            Write-Host "UI 通道：$($bridgeStatus.uiTransport)（PID $($uiStatus.uiPid)）"
            Write-Host "截图能力：正常（$($screenshotHealth.backend)）"
            Write-Host "已注册工具：$($bridgeStatus.toolCount)"
            Write-Host ''
            Write-Host '现在可以让当前 AI 客户端操作电脑' -ForegroundColor Green
            exit 0
        }
        if (-not $authHintShown -and (Get-Date) -gt $deadline.AddMinutes(-2.8)) {
            Write-Host '如果浏览器弹出授权页，请完成一次授权；以后会自动恢复会话。' -ForegroundColor Yellow
            $authHintShown = $true
        }
        Start-Sleep -Seconds 1
    }
    throw "等待健康检查超时。请查看：$bridgeOut 和 $bridgeErr"
} catch {
    Write-Host ''
    Write-Host "启动失败：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host '修复依赖可双击“安装或修复依赖.bat”。'
    exit 1
} finally {
    Stop-Transcript | Out-Null
}
