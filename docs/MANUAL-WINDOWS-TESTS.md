# Manual Windows Acceptance (MUST be completed by a Windows tester)

Do NOT treat a green GitHub Actions check as proof that the live GUI or user profiles were tested.

1. On a Windows 10/11 x64 PC with a test Brave installation, download a verified release ZIP and verify SHA-256. Extract fully to a writable non-system folder with spaces and Unicode in the path. Do not run as administrator from untrusted media.
2. Observe original system state **before** app launch: capture relevant `%LOCALAPPDATA%\Brave-Free-Origin`, Documents backups, Brave policy registry key, hosts file, Brave updater tasks/services, Brave profile `User Data`, Start Menu shortcuts and startup entries. Do not delete anything.
3. Direct double-click `BraveFreeOrigin.exe`; check same-EXE UAC approval and GUI. With UAC declined, check clean failure (no Brave changes). Verify a second launch detects running instance.
4. Change GUI language to available localizations, change a harmless in-app preference. Exit completely. Verify `Data\settings.json` and `Data\logs` exist; reopen and confirm persistence. Confirm no new BFO-owned settings/logs/backups are written to the original user paths.
5. **Only on a test machine with backup:** use Preview on a low-risk Brave policy, Apply, exit/reopen Brave, inspect `brave://policy` for actual acceptance. Confirm a registry backup appears in `Data\Backups` and original external policies are not altered without explicit approval.
6. Test Restore stock and confirm app-owned changes are undone, while unrelated existing policies remain untouched. For hosts/updater/scriptlet advanced pages, test ONLY on a disposable test Brave profile and restore each independently.
7. Use Microsoft Process Monitor if possible; filter to the test EXE and child processes. Distinguish app-owned persistent writes from Windows-managed caches and deliberate Brave configuration writes. Record remaining external paths rather than deleting them.
8. Test relocation: fully close GUI, copy entire folder to a different path and drive, start directly from the new location, confirm saved settings and backups; no stale path required. Do not copy another PC's sensitive credentials.
9. Test upgrade: with app shut down, copy existing Data into a freshly extracted later release and confirm settings/backups; test downgrade from a full saved backup, check schema compatibility.
10. Crash test on disposable setup: close forcibly after changing harmless in-app preference, check log and settings load again; NEVER forcibly terminate mid-registry or hosts modifications unless isolated test system.
11. Verify no accidental PortableApps metadata, PAF installers, startup services, tasks or program installation from this builder. Windows system caches are expected exceptions.
12. Document screenshots, app version, commit SHA, SHA256SUMS, actual Windows build version, tests, failures and whether the executable was tested without external `.ps1`/`.bat`.

### Evidence categories

- SOURCE-INSPECTED: upstream logic and intended paths studied.
- STATIC-VALIDATED: patches/files/ZIP structure inspected or tested.
- WINDOWS-COMPILED: Microsoft compiler produced a PE on Windows CI.
- AUTOMATED-RUNTIME-TESTED: embedded source GUI executable passed upstream sandbox suite.
- MANUAL-WINDOWS-TESTED: explicit Windows desktop observation completed.
- USER-CONFIRMED: user personally tested and reported it works.
- NOT YET VERIFIED: no valid evidence yet.
- FAILED/BLOCKED: evidence of noncompliance/failed stage.
