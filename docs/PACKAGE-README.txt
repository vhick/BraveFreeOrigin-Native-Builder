Brave Free Origin - NATIVE Portable (Source-embedded Windows EXE)
================================================================
This is a Brave browser configuration/debloating utility, NOT a Brave browser.
Publisher of the upstream software: TahaHydra / Xhydra (independent of Brave).
Repackaged via an independent, unsigned, user-maintained native source build.

FIRST USE:
1. Extract the complete ZIP to a writable folder such as D:\Portable\BFO.
2. Double-click BraveFreeOrigin.exe; accept Windows UAC (Brave policies need HKLM).
3. Read a policy's description, risk, and preview before clicking Apply.
4. Fully exit Brave and reopen it; check brave://policy.
5. Use the application's Restore stock to reverse application-owned policies.

LOCAL DATA (created on first run):
- Data\settings.json             user preferences and BFO policy-ownership ledger
- Data\logs\                   application and native-host diagnostic logs
- Data\Backups\                exported .reg/hosts backups before changes
- Data\ScriptletBackups\       advanced scriptlet backup files and path manifest
- Data\TempShortcuts\         temporary local URL launch shortcuts
- locales\                     included translations (application resource files)

IMPORTANT HOST EFFECTS (INTENTIONAL, OPT-IN):
- Brave policies: HKLM\SOFTWARE\Policies\BraveSoftware\Brave.
- Advanced tool pages can change Windows hosts file, Brave updater scheduled
  tasks/services, and Brave profile scriptlet files. These are NOT made portable.
- Changing Brave updates can leave the browser without important security fixes.
- Windows may leave shell caches, recent-file history, UAC history, etc.
- Existing host/organization policies are NOT owned by this portable application.

UPGRADE:
- Exit the app completely before upgrading.
- Back up the entire package, particularly Data and Brave policies/hosts as applicable.
- Extract a new release to a NEW folder, then COPY your Data directory into it.
- Keep older folder until GUI, settings, backups and Brave configuration verified.
- Do NOT delete Data or assume a binary rollback reverses registry policies.

DEPENDENCIES:
Windows 10/11 x64; built-in Windows PowerShell 5.1 engine; .NET Framework 4.x;
Windows Forms and a separately installed Brave browser for policy effectiveness.
Uses in-process embedded PowerShell source and a compiled .NET GUI host (not
machine-code recompilation of PowerShell). No external BAT/PS1 launcher needed.

No PortableApps integration, PAF installer, registered startup, manager, or
post-exit host scavenger is included or required. No auto-updater is installed.

These unsigned builds require manual Windows testing before trusting them to
change Brave policies. Check included build-identity.json for exact source SHA.
The original upstream MIT license is in LICENSES\UPSTREAM-MIT.txt.
