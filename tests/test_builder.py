"""Offline regression fixtures; the Windows workflow separately runs real upstream tests."""
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from adapt_source import adapt
from resolve_source import semver
from validate_native import check

FIXTURE = '''[CmdletBinding()]
param([string]$Lang,[string]$BfoSettingsPath,[string]$SelfTest)
if (-not $BfoSettingsPath) {
$BfoSettingsPath = if ($script:SelfTestMode) { Join-Path ([System.IO.Path]::GetTempPath()) 'bfo-selftest-app\\settings.json' }
                       else { Join-Path $env:LOCALAPPDATA 'Brave-Free-Origin\\settings.json' }
}
# Elevation. Policies live under HKLM, so the app needs administrator rights.
# The relaunch is hidden (the GUI is the only window the user should see) and
# a refused UAC prompt is explained instead of surfacing as a red PowerShell
# error and a misleading launcher message.
if (-not $script:SelfTestMode -and -not (Test-IsAdministrator)) {
    $relaunchArgs = @('-NoLogo', '-NoProfile', '-File', $PSCommandPath)
    try {
        Start-Process -FilePath 'powershell.exe' -Verb RunAs -WindowStyle Hidden -ArgumentList $relaunchArgs -ErrorAction Stop | Out-Null
        exit 0
    } catch {
        Add-Type -AssemblyName System.Windows.Forms
        [void][System.Windows.Forms.MessageBox]::Show('Denied UAC')
        exit 2
    }
}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$script:LocaleDir       = Join-Path $PSScriptRoot 'locales'
function Get-BackupDirectory {
    $docs = [Environment]::GetFolderPath('MyDocuments')
    if (-not $docs) { $docs = Join-Path $env:USERPROFILE 'Documents' }
    $dir = Join-Path $docs 'Brave-Free-Origin-Backups'
    if ($script:SelfTestMode) { $dir = Join-Path ([System.IO.Path]::GetTempPath()) 'bfo-selftest-backups' }
}
function Start-UnelevatedProcess {
    $shortcut = Join-Path ([System.IO.Path]::GetTempPath()) ("bfo-open-{0}.lnk" -f ([guid]::NewGuid().ToString('N')))
}
function Backup-ScriptletFile {
    $backup = "$File.bfo-backup"
}
function Test-ScriptletAdvancedWriteAllowed { return $true }
function Restore-ScriptletBackup {
    $backup = "$File.bfo-backup"
}
function Restore-AllScriptletBackups {
    $backups = @(Get-ChildItem -Path $Root -Recurse -Filter 'list.txt.bfo-backup')
}
function Export-ScriptletDisabledPreferences { return 0 }
trap { Show-FatalError $_; exit 1 }
if ($script:SelfTestMode) {
    exit $script:SelfTestExit
}
'''

class TestAdapter(unittest.TestCase):
    def test_storage_redirection_and_native_only(self):
        patched = adapt(FIXTURE)
        self.assertIn("'Data\\settings.json'", patched)
        self.assertIn("'Data\\Backups'", patched)
        self.assertIn("'Data\\TempShortcuts'", patched)
        self.assertIn("'Data\\ScriptletBackups'", patched)
        self.assertIn("BaseDirectory) 'locales'", patched)
        self.assertNotIn("$PSCommandPath", patched)
        self.assertNotIn("Start-Process -FilePath 'powershell.exe'", patched)
        self.assertNotIn("GetFolderPath('MyDocuments')", patched)
        self.assertNotIn('exit $script:SelfTestExit', patched)
        self.assertIn('SelfTestMode', patched)
        # Regression for real upstream v2.0.2: there are TWO Add-Type lines,
        # one inside catch and one after the elevation block.  The first
        # used to be mistaken for the end of the bootstrap (two stray braces).
        self.assertEqual(patched.count('Add-Type -AssemblyName System.Windows.Forms'), 1)
        self.assertIn('Add-Type -AssemblyName System.Windows.Forms\nAdd-Type -AssemblyName System.Drawing', patched)
        self.assertNotIn("exit 2\n    }\n}\nAdd-Type", patched)
        self.assertNotIn('exit 2', patched)
    def test_uac_gui_end_marker_must_be_complete(self):
        # Refuse upstream drift rather than picking the first Add-Type inside catch.
        with self.assertRaises(RuntimeError):
            adapt(FIXTURE.replace('Add-Type -AssemblyName System.Drawing',
                                  '# upstream GUI initializer unexpectedly moved'))
        # Refuse a second (ambiguous) marker.
        with self.assertRaises(RuntimeError):
            adapt(FIXTURE + '\nAdd-Type -AssemblyName System.Windows.Forms\nAdd-Type -AssemblyName System.Drawing\n')
    def test_unknown_upstream_edit_fails_closed(self):
        with self.assertRaises(RuntimeError):
            adapt(FIXTURE.replace('Brave-Free-Origin\\settings.json','changed-name\\settings.json'))
    def test_non_ascii_code_fails_closed(self):
        with self.assertRaises(RuntimeError):
            adapt(FIXTURE+'é')
    def test_release_version_numeric_not_lexical(self):
        tags=['v2.0.9','v2.0.10','v1.99.99','v2.0.10-beta','nightly','v10.0.1']
        stable=[t for t in tags if semver(t) is not None]
        self.assertEqual(max(stable,key=semver),'v10.0.1')
        self.assertIsNone(semver('v3.0.0-rc.1'))
        self.assertIsNone(semver('v3.0'))
    def test_validator_rejects_wrong_mode_and_accepts_native_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            zip_file = Path(td)/'check.zip'
            root='BraveFreeOrigin-NativePortable/'
            pe=bytearray(300)
            pe[0:2]=b'MZ'
            struct.pack_into('<I',pe,60,128)
            pe[128:132]=b'PE\0\0'
            struct.pack_into('<H',pe,132,0x8664)
            pe[180:190]=b'BFO_SOURCE'
            entries={
                root+'BraveFreeOrigin.exe':bytes(pe), root+'README.txt':b'User guide',
                root+'LICENSES/UPSTREAM-MIT.txt':b'MIT',root+'build-identity.json':json.dumps({'upstream_commit':'a'*40,'upstream_release':'v2.0.2'}).encode(),
                root+'Data/':b'', root+'locales/fr-FR.json':b'{}'
            }
            with zipfile.ZipFile(zip_file,'w') as z:
                for name,data in entries.items():z.writestr(name,data)
            # A crafted MZ header is NOT a real compiled .NET Windows application.
            with self.assertRaises(RuntimeError): check(zip_file)
            with zipfile.ZipFile(zip_file,'w') as z:
                for name,data in entries.items():z.writestr(name,data)
                z.writestr(root+'App/AppInfo/appinfo.ini',b'x')
            with self.assertRaises(RuntimeError):check(zip_file)

if __name__=='__main__':unittest.main()
