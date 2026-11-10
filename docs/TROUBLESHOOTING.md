# Troubleshooting and repair — Native Builder b1r3

## GitHub Actions is not listed

Make sure `.github/workflows/native-build.yml` is committed in the repository's default branch, not within a nested extraction folder. Enable Actions in the repository settings. Use **Actions > Brave Free Origin - Build NATIVE Portable from Source > Run workflow**.

## Upstream release resolver errors

`latest` uses official published GitHub releases, not `main`. Explicit input must be a published stable semantic version like `v2.0.2`. A tag missing its source files, a differing remote commit, bad API credentials, and 403 rate limiting are fatal. Never work around a failure by removing hash/tag verification.

## `Unexpected upstream change` from source adapter

The upstream source changed and the exact patch no longer matches. Do not bypass the guard. Pin the previously audited `v2.0.2` release until the new function/path is manually audited, patch adapted, tests updated, and the builder revision incremented.

## C# Windows compiler failure

Windows PowerShell 5.1 and the .NET Framework x64 `csc.exe` must exist on the Windows runner. Inspect the first actual compiler error, rather than trying to execute the `.ps1` directly or packaging an unrelated app. The source file is intentionally embedded into the output executable.

## Native EXE exits immediately

Check `Data\logs\native-host-error.log`, Windows Event Viewer, Windows PowerShell 5.1 availability, enterprise PowerShell restrictions, UAC state and writable permissions. Self-tests can fail without Brave installed; normal GUI utility requires Brave for useful operations.

## Settings appear missing or profile is still on host

Portable settings are at `Data\settings.json`. Existing pre-conversion `%LOCALAPPDATA%\Brave-Free-Origin` settings are **not imported automatically** to avoid overwriting another installed instance's preferences. Back up originals and copy only after reviewing ownership and schema compatibility. The Brave *browser profile* is deliberately not moved: the tool configures an existing installed browser.

## Newer Brave ignores a policy

The upstream policy catalog was verified against a specific Brave version; inspect `brave://policy`. Do not automatically delete the existing policy or alter protected hosts/updater settings.

## Windows SmartScreen/unsigned warning

This independent kit compiles an unsigned executable. Do not disable antivirus, change enterprise policies or whitelist blindly. Verify the source, ZIP checksum and provenance. Prefer a controlled test machine before real HKLM changes.

## Restore, downgrade and crashes

Quit Brave Free Origin. Back up the **entire portable directory** and existing Brave policies/hosts. Keep `Data\Backups` and `Data\ScriptletBackups`. Restore the previous *directory and matching Data* if application schema regression occurs. A binary rollback does not reverse changes previously applied to HKLM or Brave profile files; use explicit app restore controls and verified backup files. Never broadly delete user profile folders or registry trees. 

## Publication did not happen

If `publish=false`, only the dry-run stage runs; the ZIP is not uploaded as a release. If the same exact release tag already exists, the workflow will avoid duplicate publication. A manual/unverified release using the same tag blocks replacement. Check publisher logs for validation errors, missing permissions (`contents: write`) and managed-release ownership.


### b1r1: `Unexpected token '}'` in patched PowerShell

The b1r1 source adapter searched for the *first* WinForms `Add-Type` inside the
upstream UAC code's catch block, rather than the *post-UAC* GUI initialization.
This left two closing braces.  Fixed in b1r2: replace all b1r1 files with b1r2
and run the same native workflow again.  No application ZIP was produced by
that failed b1r1 run, so no `Data` migration is needed.


### b1r2: `PositionalParameterNotFound` for `ar.json`

The b1r2 source adapter passed the PowerShell parser and the build continued
past the C# compilation checks, but packaging failed while copying locale JSON
files. Windows PowerShell 5.1 allows only two positional components in a
`Join-Path` call; the source line supplied `stage`, `locales`, and `ar.json`.
Fixed in b1r3 by two explicit `Join-Path` calls. Extract the whole b1r3 kit
over the builder repo, commit and rerun. No completed application ZIP was
published by that failed run.
