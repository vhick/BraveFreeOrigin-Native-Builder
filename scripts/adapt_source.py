#!/usr/bin/env python3
"""Exact, fail-closed source patch for upstream Brave-Free-Origin v2.x.

Patch only application-owned storage and bootstrap; never intercept Brave policies,
hosts, updater or scriptlets. Inputs are Git-verified tag source, not a ZIP binary.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
from patch_expert import patch_expert_paths


def exactly_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Refusing unexpected upstream change: {label}: expected 1, found {count}")
    return source.replace(old, new, 1)


def adapt(original: str) -> str:
    if not original.isascii():
        raise RuntimeError("Expected ASCII upstream script, refusing encoding change")
    s = original
    s = exactly_once(
        s,
        "else { Join-Path $env:LOCALAPPDATA 'Brave-Free-Origin\\settings.json' }",
        "else { Join-Path ([System.AppDomain]::CurrentDomain.BaseDirectory) 'Data\\settings.json' }",
        "local BFO settings")
    s = exactly_once(s,
        "$script:LocaleDir       = Join-Path $PSScriptRoot 'locales'",
        "$script:LocaleDir       = Join-Path ([System.AppDomain]::CurrentDomain.BaseDirectory) 'locales'",
        "locale resource root")
    # Upstream reruns powershell.exe and -File $PSCommandPath under UAC.
    # The native C# EXE now owns UAC; never spawn a script-based wrapper.
    preface = "# Elevation. Policies live under HKLM, so the app needs administrator rights."
    after = "Add-Type -AssemblyName System.Windows.Forms"
    beg = s.find(preface)
    end = s.find(after, beg)
    if beg < 0 or end < 0 or s[beg:end].count("Start-Process -FilePath 'powershell.exe'") != 1:
        raise RuntimeError("Unexpected UAC bootstrap; source audit must be repeated")
    s = s[:beg] + (
        "# NATIVE: the compiled same-executable host performs UAC elevation.\n"
        "# Self-tests remain unelevated and isolated in the upstream sandbox.\n"
        "if (-not $script:SelfTestMode -and -not (Test-IsAdministrator)) {\n"
        "    throw 'Elevation is required for Brave policies; native host UAC did not complete.'\n"
        "}\n"
    ) + s[end:]
    old_backup = ("    $docs = [Environment]::GetFolderPath('MyDocuments')\n"
                  "    if (-not $docs) { $docs = Join-Path $env:USERPROFILE 'Documents' }\n"
                  "    $dir = Join-Path $docs 'Brave-Free-Origin-Backups'\n"
                  "    if ($script:SelfTestMode) { $dir = Join-Path ([System.IO.Path]::GetTempPath()) 'bfo-selftest-backups' }")
    new_backup = ("    $dir = Join-Path ([System.AppDomain]::CurrentDomain.BaseDirectory) 'Data\\Backups'\n"
                  "    if ($script:SelfTestMode) { $dir = Join-Path ([System.IO.Path]::GetTempPath()) 'bfo-selftest-backups' }")
    s = exactly_once(s, old_backup, new_backup, "user Documents backups")
    s = patch_expert_paths(s)
    # -BfoSettingsPath is retained in upstream signature for internal test support.
    # Host intentionally NEVER exposes it to consumers, preventing external writes.
    s = exactly_once(s,
        "    exit $script:SelfTestExit\n}",
        "    if ($script:SelfTestExit -ne 0) { throw 'Upstream application self-tests failed' }\n    return\n}",
        "test exit result for in-process host")
    # Match the app's internal exception handler to the host's error reporting.
    s = exactly_once(s,
        "trap { Show-FatalError $_; exit 1 }",
        "trap { Show-FatalError $_; throw }",
        "in-process fatal error propagation")
    if "$PSCommandPath" in s or "Join-Path $PSScriptRoot 'locales'" in s:
        raise RuntimeError("Unexpected unadapted script execution dependency")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--upstream', required=True)
    ap.add_argument('--output', required=True)
    a = ap.parse_args()
    data = Path(a.upstream).read_bytes()
    if b'\r\n' in data:
        # Source was written with CRLF: canonicalize before exact text adapter.
        data = data.replace(b'\r\n', b'\n')
    converted = adapt(data.decode('ascii'))
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_bytes(converted.encode('ascii'))
    print('SOURCE-INSPECTED adaptation applied:', a.output)


if __name__ == '__main__':
    main()
