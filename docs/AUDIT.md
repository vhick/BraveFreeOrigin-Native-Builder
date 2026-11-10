# Brave Free Origin NATIVE Source Audit / Implementation Findings (b1r1)

Audit target: https://github.com/TahaHydra/Brave-Free-Origin , observed latest released **v2.0.2** (September 30, 2026), short commit `6197418` as displayed on GitHub. Actual **full** SHA and all hashes are resolved and recorded by the builder at runtime, not invented here.

## Architecture

- Upstream is one pure-ASCII, Windows PowerShell 5.1 GUI application `Brave-Free-Origin.ps1`, WinForms + Drawing. Not Brave browser and not Chromium source. MIT `LICENSE`. Upstream installation uses a `.bat`/PowerShell script instead of a compiled EXE.
- Requirements: Windows 10 or 11, Windows PowerShell 5.1, .NET Framework/WinForms, Brave browser for useful operations, UAC for HKLM writes.
- Selected NATIVE adaptation: source is patched **before invocation**; a compiled .NET Framework x64 PE embeds that exact patched source as plaintext PE resource, hosts the Microsoft Windows PowerShell engine in-process with an STA GUI thread, and owns UAC/single-instance. This is direct executable source-embedding, not translation of the upstream script into machine code; the Windows PowerShell engine remains required.
- No PortableApps launcher/metadata/installer; no TraceGuard or post-exit harvesting. Default `Data/` beside exe, with locale resource files alongside exe.
- Runtime downloads/updaters: the app itself does not download runtime dependencies or self-update. Advanced UI actions can separately manage Brave's updater components (user-driven).
- GitHub source released stable tags are resolved via verified Git objects and version-specific SHA-256. Nothing is compiled from main.

## Evidence-based findings

| Finding | Source evidence | File or registry path | Responsibility | NATIVE remedy | PORTABLEAPPS remedy (not selected) | Data safety | Tradeoff | Test | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Settings / ownership ledger | `Brave-Free-Origin.ps1` bootstrap around lines 45-53 | `%LOCALAPPDATA%\Brave-Free-Origin\settings.json` | Application | default `Data\settings.json` before GUI | N/A | preserve Data | legacy host settings not auto-imported | adapter + runtime sandbox; manual | SOURCE-INSPECTED |
| Application log | `Write-Log`, `AppDataDir`, `LogDir` | `%LOCALAPPDATA%\Brave-Free-Origin\logs` | Application | follows local settings parent -> `Data\logs` | N/A | logs remain local | no hidden global logging | adapter, manual | SOURCE-INSPECTED |
| Automatic registry backups | `Get-BackupDirectory` around lines 1623-1632 | Documents\Brave-Free-Origin-Backups | Application | `Data\Backups`; self-test temp sandbox unchanged | N/A | preserve all backups | writable portable directory required | adapter, GUI | SOURCE-INSPECTED |
| Language resources | `$script:LocaleDir = Join-Path $PSScriptRoot 'locales'` | near upstream script | Application | resolve executable directory; stage official locales | N/A | no overwrite Data | translations bundled | static / UI | SOURCE-INSPECTED |
| Original UAC relaunch | bootstrap lines 58-83 with `powershell.exe -File $PSCommandPath` | elevated child process | Application | compiled host relaunches same exe with `Verb=runas`; upstream script verifies elevation | N/A | no profile switching via new script | UAC remains necessary | test sandbox; manual UAC | SOURCE-INSPECTED |
| Brave machine policies | `Get-PolicyHivePath`, `Set-PolicyRegistryValue` | `HKLM\SOFTWARE\Policies\BraveSoftware\Brave` | Brave enterprise interface; app writes | intentional explicit action; preserve ownership ledger and backup | N/A | warn/review external policy conflicts | real host changes necessary | real Windows manual test | SOURCE-INSPECTED |
| Brave installations & profiles | `BraveInstalls`, `Get-BraveExecutable` | `%LOCALAPPDATA%\BraveSoftware\...\User Data`, Program Files | Existing Brave/browser | leave paths alone; read-only scanning unless expert user action | N/A | existing profiles not moved | machine-specific browser profiles | manual inspect | SOURCE-INSPECTED |
| Windows hosts file blocklist | `$script:HostsFile` | `%WINDIR%\System32\drivers\etc\hosts` | app, optional | retain original opt-in sentinel + backup logic | N/A | do not redirect shared hosts file | machine-wide effect | manual restore | SOURCE-INSPECTED |
| Brave updater services/tasks | Advanced updater code and README | Brave updater services/tasks | app, optional | preserve original opt-in handling; no automatic disable | N/A | installed browser settings remain | security-update risk | manual only | SOURCE-INSPECTED |
| Brave scriptlet expert edits | `Set-ScriptletRuleState`, `Backup-ScriptletFile` | Browser profile `list.txt` (intentional modification); original `list.txt.bfo-backup` | app, optional | leave explicitly edited browser-profile file in place, but write checksummed new backups to `Data\ScriptletBackups` with manifests; allow read-only legacy backup restore | N/A | preserve portable backups; never harvest installed profile | an authorized edit still changes a host Brave profile, and restoring a new machine needs matching path | unit patch + manual restore | SOURCE-INSPECTED |
| App shell shortcuts | `Start-UnelevatedProcess`, `Remove-TempShortcuts` | temp `.lnk` used to open Brave without admin rights | app | create shortcuts in `Data\TempShortcuts`; preserve cleanup on form close | N/A | no generic shell cleanup | OS-managed caches may remain | manual | SOURCE-INSPECTED |
| Runtime framework caches | .NET Framework, PowerShell, WinForms | Windows-managed caches/history | Operating system | document; do not attempt broad deletion | N/A | unrelated host data never scavenged | absolute zero host activity impossible | ProcMon manual | INFERRED |

**No original binary artifacts, local Windows interactive tests, install profile, or existing host policy snapshots were available at kit creation.** Mode-specific, source-evidenced adapter only; all other host manipulations stay explicitly user-driven.

## Pinned shared action

`vhick/portable-release-publisher@v1.1.1` `action.yml` was inspected publicly. Inputs: `files` and `tag` required; `release-title`, `tag-prefix`, `keep-releases`, `prune`, `dry-run` optional. It calls `scripts/publish.py` using GH token and validates `.zip` or `.paf.exe`. Workflow uses `dry-run=true` before publication and sets `keep-releases=3`, `prune=false` with caller repo `contents: write`. A Git tag reference is used rather than an immutable action SHA because the full verified action commit was not established during this kit authoring session. For strict production provenance, replace with independently verified immutable commit SHA for the exact v1.1.1 tag.

The separate shared Portable-Package-Builder @v1.0.0 is correctly **excluded** from NATIVE-only mode.

## Non-negotiable limitations

1. The executable is managed .NET plus an **in-process Windows PowerShell engine**, not a rewritten C++ application, and not a machine-code compilation of PowerShell. No source-binary substitution or fake app is used.
2. UAC is necessary because upstream edits Brave HKLM policies. Application-level storage containment does not make applied machine policies portable between PCs.
3. Corporate Windows PowerShell restrictions, Constrained Language Mode or endpoint security policies can prevent execution. Do not bypass enterprise protections.
4. Browser policy catalog may lag newer Brave. Check actual effects at `brave://policy`.
5. Full GUI, browser policy application, desktop notification/shell behavior, crash/rollback, moved drive and admin context require interactive Windows acceptance. Headless CI cannot certify them.
6. The expert-page backup change alters the original translated backup-help strings: English is patched, other locales may retain upstream wording until translated. Source adapter intentionally fails closed if upstream source structure changes. Update and re-audit, never automatically fall back to `main` or a .BAT package.
