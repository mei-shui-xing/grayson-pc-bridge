# Grayson PC Bridge

> **v0.1.0-alpha 使用原则**：本项目是 **GPT-first, not GPT-only** 的 MCP 分支。默认先使用文件、终端、窗口和 UI Automation 等结构化工具；只有结构化能力无法识别自绘页面、弹窗或控件时，才使用截图和坐标视觉兜底。
>
> Alpha 阶段没有电脑级全局租约。任何时刻只允许一个 AI/客户端操作鼠标键盘；ChatGPT、Codex、Computer Use 或其他模型不得并发抢占。发布、发送、删除、账号/权限变更、购买、支付、密码等敏感操作必须暂停并由主人确认。

这是基于 `wonderwhy-er/DesktopCommanderMCP` 的 Windows 修改分支。它保留上游的文件、终端和进程工具，并增加一个受安全白名单约束的 Windows UI sidecar，让远程 ChatGPT 能读取窗口、截图并执行鼠标键盘操作。

上游项目、作者归属和 MIT 许可证必须保留。本分支只在 GitHub 分发源码，不使用上游 npm 包名发布。

## 能做什么

- 通过 Desktop Commander Remote MCP 访问本机文件、终端和进程。
- 读取当前窗口、UI Automation 节点和可见截图。
- 对白名单程序执行点击、滑动、滚动、按键、文本输入和等待。
- 使用桌面启动器启动、停止、修复依赖和查看运行状态。
- 多个远程对话同时调用 Windows UI 时会进入同一串行队列，避免鼠标键盘指令直接并发。

## 安全边界

- 这不是沙箱；文件和终端工具仍以当前 Windows 用户权限运行。
- Windows UI 默认只控制 `windows-ui/config/allowlist.json` 允许的程序或窗口。
- 密码框、支付/银行页面、微信、QQ、密码管理器、UAC、锁屏和高风险快捷键会被拦截。
- 本机可通过 `Ctrl + Alt + Pause` 紧急停止；若被占用则使用 `Ctrl + Alt + F12`。
- 串行队列只能避免指令同时执行，不能保证两个对话基于同一张旧截图做出的计划仍然正确。操作桌面时仍建议只让一个对话主控。

## 安装

要求 Windows 10/11、Node.js 18+ 和 `uv`。将仓库克隆到任意目录后：

1. 进入 `launcher`，双击 `安装或修复依赖.bat`。
2. 脚本会安装 Node/Python 依赖、构建项目、生成本机安全白名单，并把启动器更新到桌面的 `Grayson电脑助手`。
3. 双击桌面目录中的 `启动电脑助手.bat`。
4. 首次出现浏览器授权页时完成授权；状态显示绿色后再让 ChatGPT 操作。
5. 不再使用时双击 `停止电脑助手.bat`。

默认白名单模板位于 `windows-ui/config/allowlist.example.json`。本机实际使用的 `allowlist.json` 不进入 Git；需要控制新程序时只添加必要的进程名或窗口标题，不要把整个系统放开。

## 给接手安装的 AI

- 先读取本文件、`launcher/README.txt` 与 `windows-ui/config/allowlist.example.json`。
- 优先运行现成的 `launcher/安装或修复依赖.bat`，不要另造一套安装流程。
- 启动后用 `launcher/查看运行状态.bat` 验证 bridge、Windows UI、远程连接与控制状态。
- 修改白名单前向主人解释新增程序和风险；不得放开支付、聊天、密码管理器或系统安全窗口。
- 发布前运行 `npm run build`，再在 `windows-ui` 目录执行核心 pytest。
- 不执行 `npm publish`，也不向上游远程直接推送本分支。

## 已知限制

- 只能操作当前可见的 Windows 桌面；被遮挡或最小化窗口通常需要先恢复。
- 自绘游戏/编辑器可能没有完整 UIA 节点，此时使用截图和实时坐标兜底。
- UAC 安全桌面、锁屏和更高权限窗口无法也不应该被远程控制。
- 当前不包含 OCR、录屏、语音、自动支付、密码输入或任意 PowerShell UI 工具。
