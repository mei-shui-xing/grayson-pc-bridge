# AI Desktop Control Bridge

> [!WARNING]
> Do **not** install this fork with the upstream Desktop Commander `npx` command. This Alpha must be cloned from this repository and installed through the bundled Windows launcher.

[中文说明](README.zh-CN.md)

AI Desktop Control Bridge is a Windows-focused, safety-gated fork of [Desktop Commander MCP](https://github.com/wonderwhy-er/DesktopCommanderMCP). It preserves the upstream file, terminal, process, search, and preview tools, and adds a Windows UI sidecar for reading visible windows, taking screenshots, and operating allowlisted applications with mouse and keyboard input.

This repository is an early `v0.1.0-alpha.1` source release for a small technical tester group. It is **GPT-first, not GPT-only** and can be used by compatible MCP clients.

## Alpha operating policy

- **Structured first, visual fallback:** prefer file, terminal, window, and UI Automation tools. Use screenshots and coordinates only when structured tools cannot identify the target.
- **One input controller:** only one AI/client may control the mouse and keyboard at a time. The in-process queue is not a computer-wide lease.
- **Owner confirmation for sensitive actions:** sending, publishing, deletion, purchases, payments, credential entry, and account or permission changes must pause for the computer owner.
- **Not a security sandbox:** file and terminal tools run with the current Windows user's permissions. Review [SECURITY.md](SECURITY.md) before use.

## What it adds

- Visible-window inspection, screenshots, and UI Automation node reading.
- Click, scroll, drag, key, text-input, and wait actions for allowlisted applications.
- A serial Windows UI queue to prevent direct concurrent input execution.
- Local emergency stop and explicit local recovery.
- Windows launcher scripts for dependency repair, start, stop, and status checks.

## Install on Windows

Requirements: Windows 10/11, Node.js 18 or newer, and `uv`.

1. Clone this repository to any local folder.
2. Open `launcher` and run `安装或修复依赖.bat`.
3. Start the installed desktop launcher with `启动电脑助手.bat`.
4. Complete the browser authorization step when prompted.
5. Wait until the status view reports that remote control is allowed before asking an AI client to operate the computer.
6. Run `停止电脑助手.bat` when remote control is no longer needed.

The local allowlist is generated at `windows-ui/config/allowlist.json` and is excluded from Git. Its tracked template is `windows-ui/config/allowlist.example.json`.

## Safety boundary

- Password fields, payment and banking pages, private chat applications, password managers, UAC, the lock screen, and configured high-risk shortcuts are blocked.
- Use `Ctrl + Alt + Pause` for emergency stop. If that shortcut is occupied, use `Ctrl + Alt + F12`.
- A serial queue prevents simultaneous input execution, but it cannot make two conversations acting from stale screenshots logically safe. Keep one conversation as the active desktop controller.
- The tool can only operate the visible Windows desktop. Minimized, covered, elevated, UAC, and lock-screen surfaces are outside the supported boundary.

## Dependency status

This Alpha has documented unresolved upstream dependency advisories. Review [DEPENDENCY_AUDIT_ALPHA.md](DEPENDENCY_AUDIT_ALPHA.md) before installation. Do not build or install it from untrusted registries, package caches, or source archives.

## Development verification

```powershell
npm ci
npm run build
npm test
```

Then run the core Python tests from the `windows-ui` directory. Live mouse, keyboard, screenshot, and authorization behavior still requires owner-authorized manual acceptance on Windows.

## Upstream and licensing

This project is a derivative fork of Desktop Commander MCP. Upstream authorship, Git history, and the MIT license are retained. See [UPSTREAM.md](UPSTREAM.md), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), and [LICENSE](LICENSE).

This fork is distributed as source code only and does not publish under the upstream npm package name.

## Known limitations

- No computer-wide controller lease, release signing, automatic update channel, or complete SBOM platform yet.
- Self-rendered games and editors may not expose complete UI Automation nodes and may require screenshot/coordinate fallback.
- OCR, screen recording, voice control, automatic payment, password entry, registry editing, and arbitrary PowerShell UI automation are not included.
