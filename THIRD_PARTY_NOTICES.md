# Third-party notices

AI Desktop Control Bridge `v0.1.0-alpha.1` is a derivative fork. This file is a concise Alpha notice, not a replacement for the license files shipped by each dependency.

## Primary upstream

- **Desktop Commander MCP** — https://github.com/wonderwhy-er/DesktopCommanderMCP — MIT. The Node.js file, terminal, process, search, preview, and remote-bridge implementation is derived from this project. Copyright (c) 2024-2025 Eduard Ruzga and Desktop Commander contributors. The upstream Git history and root `LICENSE` are retained.

## Windows UI runtime

- MCP Python SDK — MIT.
- pywin32 — PSF License.
- pywinauto — BSD-3-Clause.
- psutil — BSD-3-Clause.
- Pillow — HPND.
- mss — MIT.
- dxcam — MIT.
- pystray — LGPL-3.0. It is loaded as an unmodified Python package for the optional tray UI. Binary or virtual-environment redistribution must retain its license and LGPL replacement/source rights.

## Major Node.js runtime dependencies

- MCP TypeScript SDK, Supabase JS, Tiptap packages, pdf-lib, ExcelJS, markdown-it, remark/unified, zod, and most other direct dependencies — MIT.
- sharp and Playwright-derived tooling where present — Apache-2.0.
- highlight.js — BSD-3-Clause.
- glob and zod-to-json-schema — ISC.
- pizzip — dual `(MIT OR GPL-3.0)`; this distribution elects the MIT option and must retain the applicable license text.

Before a public binary release, regenerate the dependency inventory from `package-lock.json` and the Python environment and include all applicable license texts. See [DEPENDENCY_AUDIT_ALPHA.md](DEPENDENCY_AUDIT_ALPHA.md) for the current vulnerability disposition.
