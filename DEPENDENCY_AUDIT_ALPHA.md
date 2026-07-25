# Alpha dependency security status

Audit target: `v0.1.0-alpha.2`. This file intentionally records unresolved findings instead of presenting the Alpha as vulnerability-free.

## Direct upgrades applied

- `@modelcontextprotocol/sdk`: 1.25.1 → 1.29.0.
- `file-type`: 21.2.0 → 21.3.4.
- `sharp`: 0.34.5 → 0.35.3.
- `markdown-it`: 14.1.0 → 14.3.0.

Safe transitive lockfile updates were also applied with `npm audit fix --package-lock-only`; no `--force` change was accepted. These versions are validated by the repository build and test suite. The `v0.1.0-alpha.2` preparation does not update any dependency or transitive lockfile entry.

## Remaining findings (2026-07-25)

`npm audit --omit=dev --json` reports **16 production findings: 0 low, 3 moderate, 12 high, 1 critical**. `npm audit --json` reports **30 complete-tree findings: 4 low, 3 moderate, 19 high, 4 critical**.

These totals are the `metadata.vulnerabilities` package-entry counts reported by npm, with each vulnerable package represented at its highest severity. The **30 vulnerabilities** printed by `npm ci` are the same complete-tree total, not a third result set and not a raw count of individual GHSA advisories. Omitting development dependencies reduces the audited total to 16; optional production dependency paths remain included.

| Dependency path | Severity | Runtime reachability | Alpha disposition |
| --- | --- | --- | --- |
| `@opendocsg/pdf2md -> unpdf -> canvas -> @mapbox/node-pre-gyp -> tar / rimraf -> glob -> minimatch -> brace-expansion` | critical/high | This optional native `canvas` chain is used during installation, not while handling normal MCP calls. A malicious/untrusted package or cache in the build environment could reach the archive tooling. | Deferred: `@mapbox/node-pre-gyp` constrains `tar` to 6.x while the current advisory fix is outside that compatible range. Do not install/build from untrusted registries or caches; replace or update the PDF/native-canvas stack before beta. |
| `@modelcontextprotocol/sdk -> @hono/node-server` | moderate | Potentially reachable if the SDK's Hono HTTP/static adapter is enabled. This Alpha's primary local transport is stdio/remote bridge, but the package is present. | Deferred: npm proposes a breaking SDK downgrade from 1.29.0 to 1.24.3. Keep static serving disabled/unexposed; retest when the SDK ships a compatible Hono fix. |
| `exceljs -> archiver -> archiver-utils / readdir-glob / zip-stream -> glob / minimatch / brace-expansion` | high | Spreadsheet export can reach ExcelJS archive creation, so these findings are treated as runtime-reachable for untrusted or adversarial workbook/output workloads. | Deferred: npm proposes a breaking ExcelJS downgrade to 3.4.0. Upgrade or replace ExcelJS after compatibility testing; do not accept untrusted archive inputs during this Alpha. |
| `exceljs -> uuid` | moderate | Spreadsheet read/write is exposed, but the advisory requires UUID v3/v5/v6 with a caller-provided output buffer; this project does not directly call that API. | Deferred: npm proposes a breaking ExcelJS downgrade to 3.4.0. Replace/upgrade when ExcelJS updates `uuid`. |
| `glob -> minimatch -> brace-expansion` | high | The direct `glob` dependency can process user-selected filesystem patterns, so denial-of-service risk is potentially runtime-reachable. | Deferred: npm proposes the breaking major `glob` 13.0.6. Migrate and retest the file-search surface before beta. |
| `md-to-pdf -> serve-handler -> minimatch -> brace-expansion` | high | PDF/preview tooling is exposed to user-selected content and paths, so this chain is potentially runtime-reachable. | Deferred: npm proposes the breaking `md-to-pdf` 1.1.0 downgrade. Replace or update the PDF path after compatibility testing. |

The additional complete-tree findings are in packaging/development paths including `nexe -> download -> decompress / got -> cacheable-request -> http-cache-semantics`, `nexe -> archiver / rimraf`, `@anthropic-ai/mcpb -> @inquirer/prompts -> @inquirer/editor -> external-editor -> tmp`, `shx -> shelljs -> glob`, and `nodemon -> minimatch`. They are not part of a production-only installation's normal runtime path, but they remain relevant to the trusted release machine and are not claimed as harmless.

## Reachability policy

- Findings in file parsers/image libraries are potentially reachable because the MCP accepts user-selected files. They are not dismissed as development-only.
- Findings under packaging/build-only dependency trees may be unreachable at normal runtime, but remain relevant to the trusted release build environment.
- A finding is deferred only when the available fix requires a breaking downgrade/major change or belongs to an upstream dependency with no compatible fix. Deferral requires an explicit path and reason in the execution report.

## Deferred platform work

The Alpha does not yet implement a computer-wide lease broker, release signing, auto-update, or a full automated SBOM platform. These remain planned work and do not change the one-input-controller rule.
