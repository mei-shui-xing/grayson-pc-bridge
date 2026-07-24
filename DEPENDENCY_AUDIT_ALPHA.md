# Alpha dependency security status

Audit target: `v0.1.0-alpha.1`. This file intentionally records unresolved findings instead of presenting the Alpha as vulnerability-free.

## Direct upgrades applied

- `@modelcontextprotocol/sdk`: 1.25.1 → 1.29.0.
- `file-type`: 21.2.0 → 21.3.4.
- `sharp`: 0.34.5 → 0.35.3.
- `markdown-it`: 14.1.0 → 14.3.0.

Safe transitive lockfile updates were also applied with `npm audit fix --package-lock-only`; no `--force` change was accepted. These versions are validated by the repository build and test suite.

## Remaining findings (2026-07-25)

`npm audit --omit=dev` reports **6 production findings: 1 critical, 1 high, 4 moderate**. The complete tree (including packaging and test dependencies) reports **17 findings: 4 low, 4 moderate, 5 high, 4 critical**.

| Dependency path | Severity | Runtime reachability | Alpha disposition |
| --- | --- | --- | --- |
| `@opendocsg/pdf2md -> unpdf -> canvas -> @mapbox/node-pre-gyp -> tar` | critical/high | `tar` is used while installing the optional native `canvas` package, not while handling normal MCP calls. A malicious/untrusted package or cache in the release build environment could reach it. | Deferred: the compatible parent range pins `tar` 6.x while npm's advisory fix is outside it. Do not install/build from untrusted registries or caches; replace/update the PDF stack before beta. |
| `@modelcontextprotocol/sdk -> @hono/node-server` | moderate | Potentially reachable if the SDK's Hono HTTP/static adapter is enabled. This Alpha's primary local transport is stdio/remote bridge, but the package is present. | Deferred: npm proposes a breaking SDK downgrade from 1.29.0 to 1.24.3. Keep static serving disabled/unexposed; retest when the SDK ships a compatible Hono fix. |
| `exceljs -> uuid` | moderate | Spreadsheet read/write is an exposed MCP feature, but the advisory requires UUID v3/v5/v6 with a caller-provided output buffer; this project does not directly call that API. | Deferred: npm proposes a breaking ExcelJS downgrade to 3.4.0. Replace/upgrade when ExcelJS updates `uuid`. |

The extra full-tree findings are in packaging/development chains led by `nexe`, `@anthropic-ai/mcpb`, and their archive/download/prompt dependencies. They are not shipped in the source archive's runtime installation path when users install production-only dependencies, but they remain relevant to the trusted release machine and are not claimed as harmless.

## Reachability policy

- Findings in file parsers/image libraries are potentially reachable because the MCP accepts user-selected files. They are not dismissed as development-only.
- Findings under packaging/build-only dependency trees may be unreachable at normal runtime, but remain relevant to the trusted release build environment.
- A finding is deferred only when the available fix requires a breaking downgrade/major change or belongs to an upstream dependency with no compatible fix. Deferral requires an explicit path and reason in the execution report.

## Deferred platform work

The Alpha does not yet implement a computer-wide lease broker, release signing, auto-update, or a full automated SBOM platform. These remain planned work and do not change the one-input-controller rule.
