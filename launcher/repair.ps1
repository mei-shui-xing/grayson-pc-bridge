. (Join-Path $PSScriptRoot 'common.ps1')

Write-Host '=== 安装或修复 AI电脑助手依赖 ===' -ForegroundColor Cyan
$allowlistPath = Join-Path $WindowsUiRoot 'config\allowlist.json'
$allowlistExample = Join-Path $WindowsUiRoot 'config\allowlist.example.json'
if (-not (Test-Path -LiteralPath $allowlistPath)) {
    if (-not (Test-Path -LiteralPath $allowlistExample)) {
        throw "缺少安全白名单模板：$allowlistExample"
    }
    Copy-Item -LiteralPath $allowlistExample -Destination $allowlistPath
    Write-Host '已从安全模板创建本机 allowlist.json；需要控制其他程序时请按需添加。' -ForegroundColor Yellow
}
$requiredTitlePatterns = @(
    'AI电脑助手',
    'AI Desktop Control Bridge',
    'Grayson电脑助手',
    'Grayson-PC-Bridge'
)
try {
    $allowlist = Get-Content -LiteralPath $allowlistPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $patterns = @($allowlist.allowed_window_title_patterns)
    $allowlistChanged = $false
    foreach ($requiredPattern in $requiredTitlePatterns) {
        if ($patterns -notcontains $requiredPattern) {
            $patterns += $requiredPattern
            $allowlistChanged = $true
        }
    }
    if ($allowlist.PSObject.Properties.Name -notcontains 'allowed_window_title_patterns') {
        $allowlist | Add-Member -NotePropertyName allowed_window_title_patterns -NotePropertyValue $patterns
        $allowlistChanged = $true
    } else {
        $allowlist.allowed_window_title_patterns = $patterns
    }
    $allowlistBytes = [System.IO.File]::ReadAllBytes($allowlistPath)
    $hasUtf8Bom = $allowlistBytes.Length -ge 3 -and $allowlistBytes[0] -eq 0xEF -and $allowlistBytes[1] -eq 0xBB -and $allowlistBytes[2] -eq 0xBF
    if ($allowlistChanged -or $hasUtf8Bom) {
        $allowlistJson = ($allowlist | ConvertTo-Json -Depth 20) + [Environment]::NewLine
        [System.IO.File]::WriteAllText($allowlistPath, $allowlistJson, [System.Text.UTF8Encoding]::new($false))
        Write-Host '已保留现有白名单规则、补充新旧启动器标题并保持 UTF-8 无 BOM。' -ForegroundColor Yellow
    }
} catch {
    throw "无法在保留现有规则的前提下更新白名单：$($_.Exception.Message)"
}
if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) { throw '请先安装 Node.js 18 或更高版本。' }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw '未找到 npm。请重新安装 Node.js。' }
if (-not (Get-Command uv.exe -ErrorAction SilentlyContinue)) { throw '未找到 uv。请先安装 uv，或让 Codex 帮你修复环境。' }

Push-Location $ProjectRoot
try {
    Write-Host '安装 Node 依赖并构建本地项目桥……'
    & npm.cmd install
    if ($LASTEXITCODE -ne 0) { throw 'npm install 失败。' }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'npm run build 失败。' }
} finally { Pop-Location }

Push-Location $WindowsUiRoot
try {
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        & uv.exe venv --python 3.11 .venv
        if ($LASTEXITCODE -ne 0) { throw '创建 Python 3.11 虚拟环境失败。' }
    }
    & uv.exe pip install --python $PythonExe -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw '安装 Windows UI 依赖失败。' }
    & $PythonExe -m compileall -q windows_ui
    if ($LASTEXITCODE -ne 0) { throw 'Python 模块检查失败。' }
} finally { Pop-Location }

$sourceLauncher = (Resolve-Path -LiteralPath (Join-Path $ProjectRoot 'launcher')).Path
$launcherTargets = [System.Collections.Generic.List[string]]::new()
$launcherTargets.Add($DesktopFolder)
foreach ($compatibleFolder in @($DefaultDesktopFolder, $LegacyDesktopFolder)) {
    if ((Test-Path -LiteralPath $compatibleFolder) -and $launcherTargets -notcontains $compatibleFolder) {
        $launcherTargets.Add($compatibleFolder)
    }
}

foreach ($launcherTarget in $launcherTargets) {
    New-Item -ItemType Directory -Force -Path $launcherTarget | Out-Null
    $targetLauncher = (Resolve-Path -LiteralPath $launcherTarget).Path
    if ($sourceLauncher -ne $targetLauncher) {
        Get-ChildItem -LiteralPath $sourceLauncher -File |
            Where-Object { $_.Name -ne 'assistant.config.json' } |
            Copy-Item -Destination $targetLauncher -Force
    }
    @{
        project_root = $ProjectRoot
        desktop_folder = $targetLauncher
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $targetLauncher 'assistant.config.json') -Encoding UTF8
    Write-Host "桌面启动器已更新：$targetLauncher" -ForegroundColor Green
}

Write-Host '依赖与构建已修复。' -ForegroundColor Green
Write-Host '现在可以双击“启动电脑助手.bat”。' -ForegroundColor Green
