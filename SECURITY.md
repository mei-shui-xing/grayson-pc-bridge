# Security Policy

## AI Desktop Control Bridge Alpha additions

AI Desktop Control Bridge adds screenshot, visible-window inspection, UI Automation, and mouse/keyboard tools to the upstream Desktop Commander capabilities.

During `v0.1.0-alpha.1`:

- Only one AI/client may control desktop input at a time. The local serial queue is not a computer-wide lock or lease.
- Screenshot and coordinate fallback should be used only when structured file, terminal, window, or UI Automation tools cannot identify the target.
- Sending, publishing, deletion, purchases, payments, credential entry, and account or permission changes require the computer owner's confirmation.
- Password fields, payment and banking pages, private chat applications, password managers, UAC, the lock screen, and configured high-risk windows remain blocked by the Windows UI sidecar.
- Emergency stop is available locally through `Ctrl + Alt + Pause`, with `Ctrl + Alt + F12` as the fallback shortcut.

## Security model

Desktop Commander is a privileged local automation tool. It lets an authorized AI client read and write files, start processes, and execute terminal commands on the host machine. AI Desktop Control Bridge additionally lets that client observe and operate parts of the visible Windows desktop.

These capabilities are the purpose of the project. Built-in restrictions are safety guardrails that reduce accidental or unintended actions; they are **not a security sandbox** that can contain a malicious or compromised AI client.

### Core assumption

The project assumes that the connected AI client, the account driving it, and the local authorization channel are trusted and uncompromised. It does not determine whether a request originated from the owner, prompt injection, a malicious webpage, or a compromised AI account.

Protecting the connected account, reviewing sensitive steps, and ending remote-control sessions when they are no longer needed are part of the owner's security responsibilities.

## What the built-in controls do

| Control | Purpose | Security boundary? |
| --- | --- | --- |
| Allowed directories | Reduce accidental file access | No |
| Command blocklist | Reduce accidental command execution | No |
| Symlink traversal prevention | Block a class of unintended path escapes | No |
| Windows application allowlist | Limit ordinary UI actions to configured windows and processes | No |
| Password/payment/private-window blocks | Stop recognized high-risk UI targets | No |
| Owner confirmation gates | Pause defined sensitive actions for human review | No |
| VM or separate workstation | Contain the tool to an isolated operating environment | Yes |

Terminal execution can launch other programs and interpreters. Directory, command, window, and process restrictions can therefore be bypassed by a sufficiently capable or malicious trusted client. Treat them as guardrails, not containment.

## Recommended deployment

For work where the AI client must not reach the wider machine, run the project on a virtual machine or separate/dedicated Windows workstation with only the required files and accounts available.

Additional practical steps:

- Enable MFA on connected AI accounts.
- Connect only clients you trust and remove authorizations you no longer use.
- Keep one conversation as the active desktop controller.
- Scope file access and the Windows UI allowlist to the smallest necessary set.
- Do not expose payment, password, private-chat, identity-verification, or system-security workflows.
- Use the local stop launcher or emergency shortcut when control is no longer expected.

## Known limitations

- The serial input queue prevents simultaneous execution but does not protect against multiple clients planning from stale screenshots.
- File and terminal tools can reach beyond advisory restrictions through normal program execution.
- UI classification cannot guarantee that every sensitive custom-rendered surface will be recognized.
- The project does not protect against a compromised AI account or prompt injection reaching an authorized client.
- `v0.1.0-alpha.1` has unresolved dependency advisories documented in [DEPENDENCY_AUDIT_ALPHA.md](DEPENDENCY_AUDIT_ALPHA.md).

## Reporting a vulnerability

Open a security-labeled issue in this repository with technical details and, where safe, a minimal proof of concept. Do not include real credentials, private connector URLs, access tokens, personal screenshots, or sensitive local paths in a public report.

For vulnerabilities inherited from Desktop Commander without changes in this fork, also follow the upstream project's reporting guidance.

## License and responsibility

This project is free, open-source software released under the MIT License and provided "as is," without warranty. The owner remains responsible for how it is installed, authorized, exposed, and used.

---

*Last updated: July 2026*
