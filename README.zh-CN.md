# AI Desktop Control Bridge

> [!WARNING]
> 不要使用上游 Desktop Commander 的 `npx` 命令安装本分支。本 Alpha 必须从当前仓库克隆，并通过仓库自带的 Windows 启动器安装。

AI Desktop Control Bridge（AI 电脑控制桥）是基于 [`wonderwhy-er/DesktopCommanderMCP`](https://github.com/wonderwhy-er/DesktopCommanderMCP) 的 Windows 安全增强分支。它保留上游的文件、终端、进程、搜索和预览工具，并增加受白名单约束的 Windows UI sidecar，让兼容 MCP 的 AI 客户端能够读取可见窗口、截图，并执行鼠标键盘操作。

当前版本是面向小范围技术测试者的源码 Alpha：`v0.1.0-alpha.2`。项目遵循 **GPT-first, not GPT-only**，并不绑定某一个 AI 客户端。

## Alpha 使用原则

- **结构化优先、视觉兜底：**优先使用文件、终端、窗口和 UI Automation；只有结构化能力无法识别目标时，才使用截图和坐标。
- **单一输入主控：**任何时刻只允许一个 AI/客户端操作鼠标键盘。进程内串行队列不是电脑级全局租约。
- **敏感操作由主人确认：**发布、发送、删除、购买、支付、密码输入、账号和权限变更必须暂停并交给主人确认。
- **这不是安全沙箱：**文件和终端工具仍以当前 Windows 用户权限运行，使用前请阅读 [SECURITY.md](SECURITY.md)。

## 能做什么

- 访问 Desktop Commander 提供的文件、终端、进程、搜索和预览能力。
- 读取当前可见窗口、截图和 UI Automation 节点。
- 对白名单程序执行点击、滚动、拖动、按键、文本输入和等待。
- 将 Windows UI 动作放入同一串行队列，避免鼠标键盘指令直接并发执行。
- 使用本地紧急停止和明确的本机恢复流程。
- 通过 Windows 启动器安装或修复依赖、启动、停止并查看状态。

## Windows 安装

要求 Windows 10/11、Node.js 18+ 和 `uv`。

1. 将本仓库克隆到任意本地目录。
2. 进入 `launcher`，双击 `安装或修复依赖.bat`。
3. 脚本会安装 Node/Python 依赖、构建项目、生成本机白名单，并把启动器更新到桌面的 `AI电脑助手`。
4. 双击桌面目录中的 `启动电脑助手.bat`。
5. 首次出现浏览器授权页时完成授权；状态显示允许远程控制后，再让 AI 操作电脑。
6. 不再使用时双击 `停止电脑助手.bat`。

默认白名单模板位于 `windows-ui/config/allowlist.example.json`。本机实际使用的 `windows-ui/config/allowlist.json` 不进入 Git；需要控制新程序时，只添加必要的进程名或窗口标题，不要把整个系统放开。

## 安全边界

- 密码框、支付和银行页面、私人聊天软件、密码管理器、UAC、锁屏和配置的高风险快捷键会被拦截。
- 本机可通过 `Ctrl + Alt + Pause` 紧急停止；若该快捷键被占用，则使用 `Ctrl + Alt + F12`。
- 串行队列只能避免输入指令同时执行，不能保证两个对话基于旧截图做出的计划仍然正确。操作桌面时仍应只保留一个主控对话。
- 只能操作当前可见的 Windows 桌面；被遮挡、最小化、高权限、UAC 和锁屏界面不在支持边界内。

## 给接手安装的 AI

- 先读取本文件、`launcher/README.txt` 和 `windows-ui/config/allowlist.example.json`。
- 优先运行现成的 `launcher/安装或修复依赖.bat`，不要另造安装流程，也不要执行上游 npm 安装命令。
- 启动后用 `launcher/查看运行状态.bat` 验证主桥、Windows UI、远程连接、截图和控制状态。
- 修改白名单前，向主人解释新增程序及风险；不得放开支付、私人聊天、密码管理器或系统安全窗口。
- 发布前运行 `npm ci`、`npm run build` 和 `npm test`，再进入 `windows-ui` 执行核心 Python 测试。
- 不执行 `npm publish`，也不向上游远程直接推送本分支。

## 依赖安全状态

当前 Alpha 仍包含已记录的上游依赖安全告警，安装前请阅读 [DEPENDENCY_AUDIT_ALPHA.md](DEPENDENCY_AUDIT_ALPHA.md)。不要从不可信的注册表、缓存或源码压缩包安装和构建。

## 上游与许可证

本项目是 Desktop Commander MCP 的衍生分支，上游作者归属、Git 历史和 MIT 许可证均保留。详见 [UPSTREAM.md](UPSTREAM.md)、[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 [LICENSE](LICENSE)。

本分支只在 GitHub 分发源码，不使用上游 npm 包名发布。

## 已知限制

- 暂无电脑级全局主控租约、发布签名、自动更新通道和完整 SBOM 平台。
- 自绘游戏或编辑器可能没有完整 UI Automation 节点，此时需要截图和坐标兜底。
- 当前不包含 OCR、录屏、语音、自动支付、密码输入、注册表编辑或任意 PowerShell UI 自动化。
