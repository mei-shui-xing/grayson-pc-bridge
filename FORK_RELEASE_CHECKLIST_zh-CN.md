# Grayson PC Bridge 公开发布检查清单

## 代码与测试

- `npm run build` 通过。
- 在 `windows-ui` 目录运行核心 pytest，确认控制状态、安全策略与窗口/截图测试通过。
- 启动器的安装、启动、状态、紧急停止和正常停止各走一遍。
- 两个对话同时发 Windows UI 调用时确认按队列串行，不出现鼠标键盘并发。

## 脱敏

- `windows-ui/config/allowlist.json`、运行状态、日志、虚拟环境、测试截图和 `.codex` 不得提交。
- 只提交 `allowlist.example.json`，并保持默认白名单最小化。
- 搜索仓库内绝对用户名路径、Token、Cookie、设备 ID 和私有聊天内容。
- 不提交桌面目录中的运行副本；只提交仓库内 `launcher` 源文件。

## 上游与发布

- 保留 `wonderwhy-er/DesktopCommanderMCP` 的 MIT 许可证和作者归属。
- 将上游远程命名为 `upstream`，自己的 GitHub 仓库命名为 `origin`。
- `package.json` 保持 `private: true`，不得以 `@wonderwhy-er/desktop-commander` 名义发布。
- GitHub 首版建议标记 beta，并明确这是 Windows 修改分支，不是上游官方版本。
