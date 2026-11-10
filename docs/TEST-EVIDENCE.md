# Validation evidence — Brave Free Origin Native Builder b1r2

**Evidence at authoring (2026-11-10).** This project was developed in a Linux-based container without a Windows desktop or functioning outbound source-fetch access for `git`. No Windows PE was produced here. A tested ZIP builder kit is NOT the same thing as a proven Windows portable release.

| Stage | Status | Evidence / next step |
|---|---|---|
| Upstream source and storage audit | SOURCE-INSPECTED | Published v2.0.2 `Brave-Free-Origin.ps1`, GUI bootstrap, settings/log paths, registry backups, advanced settings, GitHub release and source reviewed |
| Publisher pinned-action inputs | SOURCE-INSPECTED | `vhick/portable-release-publisher@v1.1.1` published `action.yml`; strict immutable full action SHA still unverified |
| Offline source-adapter regression tests | STATIC-VALIDATED | `python -m unittest discover -s tests -v` passes locally; uses controlled short fixtures, not full upstream checkout |
| Generated kit file layout and workflow YAML | STATIC-VALIDATED | Source reviewed and files included, workflow syntax checked offline |
| Windows compilation of full source-embedded EXE | NOT YET VERIFIED | Must complete GitHub Actions source build on `windows-2022`; the upstream script is PowerShell interpreted in-process, not compiled to machine code |
| PE structure and ZIP integrity | NOT YET VERIFIED | `validate_native.py` runs on a genuinely produced build ZIP; no actual compiled ZIP exists at authoring |
| Compiled EXE executing upstream sandbox self-test | NOT YET VERIFIED | `scripts/test_compiled.ps1` runs in Windows CI; must review report and exit code |
| Direct native EXE GUI / UAC / second launch | NOT YET VERIFIED | Double-click and test on Windows; no GUI runner assumed |
| Portable Data persistence and arbitrary CWD | NOT YET VERIFIED | Observe data and restart on Windows, including spaces/Unicode path and drive relocation |
| Unwanted host AppData/Document files | NOT YET VERIFIED | Compare before/after snapshots and, if available, Process Monitor activity |
| Brave HKLM policies/preview/restore | NOT YET VERIFIED | Test only on disposable profile and approved test host; user action changes HKLM intentionally |
| Advanced scriptlet and hosts/updater behavior | NOT YET VERIFIED | Controlled manual Windows tests; preserve original profile and system state |
| TraceGuard, ShellGuard, PortableApps installer | NOT APPLICABLE | Correctly excluded in NATIVE mode |
| Optional native manager/autostart | NOT APPLICABLE | Not requested and utility is an on-demand GUI |
| Publisher dry-run/release publication | NOT YET VERIFIED | Must observe `dry-run=true` then `dry-run=false` on a user-controlled builder repository |
| User-confirmed Windows functionality | NOT YET VERIFIED | User must test and confirm |

**Reminder:** tests with mocked/stub MZ payloads intentionally reject them as non-genuine compiled apps. They do not manufacture successful Windows-run evidence.


## b1r2 offline regression

- Original b1r1 GitHub Actions log was reviewed: source resolver and 5 unit
  tests passed; patched PowerShell 5.1 parser rejected two leftover `}`;
  compiler and publisher were not reached (FAILED/BLOCKED for b1r1).
- Corrected adapter to use the unique post-elevation WinForms + Drawing
  initialization pair; the additional fixture test checks two occurrences of
  WinForms initialization and rejects ambiguous/changed boundaries.
- Six local Python unit tests passed (STATIC-VALIDATED); no Windows compilation
  or interactive desktop runtime has been performed for b1r2.
