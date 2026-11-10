"""Evidence-based NATIVE source changes for optional expert-feature backups.

This code is never executed by the delivered GUI. It patches audited upstream
PowerShell before the script is embedded in the compiled native executable.
"""

def replace_one(s, old, new, reason):
    found=s.count(old)
    if found != 1: raise RuntimeError('Upstream changed: '+reason+'; expected 1, got '+str(found))
    return s.replace(old,new,1)

def replace_block(s, first, last, expected, replacement):
    start=s.find(first)
    end=s.find(last,start)
    if start < 0 or end < 0 or expected not in s[start:end]:
        raise RuntimeError('Upstream changed: '+first)
    return s[:start]+replacement+s[end:]


def patch_expert_paths(s):
    s=replace_one(s,
       '''$shortcut = Join-Path ([System.IO.Path]::GetTempPath()) ("bfo-open-{0}.lnk" -f ([guid]::NewGuid().ToString('N')))''',
       '''$shortcut = Join-Path (Join-Path ([System.AppDomain]::CurrentDomain.BaseDirectory) 'Data\\TempShortcuts') ("bfo-open-{0}.lnk" -f ([guid]::NewGuid().ToString('N')))''',
       'external temporary link')
    s=replace_block(s,'function Backup-ScriptletFile {','function Test-ScriptletAdvancedWriteAllowed {',
        '$backup = "$File.bfo-backup"',r'''function Get-NativeScriptletBackupPath {
    param([string]$File)
    $full = [System.IO.Path]::GetFullPath($File)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($full.ToLowerInvariant())
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { $id = ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
    $dir = Join-Path ([System.AppDomain]::CurrentDomain.BaseDirectory) 'Data\ScriptletBackups'
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    return (Join-Path $dir ($id + '.bfo-backup'))
}
function Backup-ScriptletFile {
    param([string]$File)
    if (-not (Test-Path -LiteralPath $File -PathType Leaf)) { throw "Scriptlet list file not found: $File" }
    $backup = Get-NativeScriptletBackupPath -File $File
    if (-not (Test-Path -LiteralPath $backup)) {
        $temporary = $backup + '.pending-' + [guid]::NewGuid().ToString('N')
        try {
            Copy-Item -LiteralPath $File -Destination $temporary -ErrorAction Stop
            $from = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash
            $to = (Get-FileHash -LiteralPath $temporary -Algorithm SHA256).Hash
            if ($from -ne $to) { throw 'Scriptlet backup verification failed; original not touched' }
            Move-Item -LiteralPath $temporary -Destination $backup -ErrorAction Stop
            $meta = [ordered]@{
                originalPath = [System.IO.Path]::GetFullPath($File)
                sha256 = $to.ToLowerInvariant()
                createdUtc = [DateTime]::UtcNow.ToString('o')
            }
            [System.IO.File]::WriteAllText(($backup + '.json'), ($meta | ConvertTo-Json -Depth 3), (New-Object System.Text.UTF8Encoding($false)))
            Write-Log "Scriptlet backup created in portable Data: $backup" 'OK'
        } finally {
            if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
        }
    }
    return $backup
}
''')
    s=replace_block(s,'function Restore-ScriptletBackup {','function Export-ScriptletDisabledPreferences {',
       "'list.txt.bfo-backup'",r'''function Restore-ScriptletBackup {
    param([string]$File)
    $backup = Get-NativeScriptletBackupPath -File $File
    if (-not (Test-Path -LiteralPath $backup)) {
        # Compatibility: original BFO script stored backups next to Brave files.
        # Never create or delete a new external backup in the native edition.
        $backup = "$File.bfo-backup"
    }
    if (-not (Test-Path -LiteralPath $backup)) { throw "No backup exists for: $File" }
    $metadata = "$backup.json"
    if (Test-Path -LiteralPath $metadata) {
        $record = [System.IO.File]::ReadAllText($metadata, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        if ($record.sha256 -ne (Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash.ToLowerInvariant()) { throw 'Saved scriptlet backup checksum changed' }
    }
    Copy-Item -LiteralPath $backup -Destination $File -Force -ErrorAction Stop
}
function Restore-AllScriptletBackups {
    param([string]$Root)
    if ([string]::IsNullOrWhiteSpace($Root) -or -not (Test-Path -LiteralPath $Root)) { throw "User Data folder not found: $Root" }
    $rootPath = [System.IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    $dir = Join-Path ([System.AppDomain]::CurrentDomain.BaseDirectory) 'Data\ScriptletBackups'
    $count = 0
    if (Test-Path -LiteralPath $dir) {
        foreach ($manifest in @(Get-ChildItem -LiteralPath $dir -Filter '*.bfo-backup.json' -File -ErrorAction Stop)) {
            $record = [System.IO.File]::ReadAllText($manifest.FullName, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
            if (-not $record.originalPath) { continue }
            $target = [System.IO.Path]::GetFullPath($record.originalPath)
            if (-not $target.StartsWith($rootPath, [System.StringComparison]::OrdinalIgnoreCase)) { continue }
            if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { continue }
            $backup = $manifest.FullName.Substring(0, $manifest.FullName.Length - '.json'.Length)
            if ($record.sha256 -ne (Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash.ToLowerInvariant()) { throw 'Saved scriptlet backup checksum changed' }
            Copy-Item -LiteralPath $backup -Destination $target -Force -ErrorAction Stop
            $count++
        }
    }
    # Original upstream backups still can be restored (never deleted here).
    foreach ($old in @(Get-ChildItem -LiteralPath $Root -Recurse -Filter 'list.txt.bfo-backup' -File -ErrorAction SilentlyContinue)) {
        $target = $old.FullName.Substring(0, $old.FullName.Length - '.bfo-backup'.Length)
        Copy-Item -LiteralPath $old.FullName -Destination $target -Force -ErrorAction Stop
        $count++
    }
    return $count
}
''')
    # Only English catalog changes guaranteed. Existing translated locale strings
    # need translator review; documented as a known localization limitation.
    s = s.replace('Backups are created as list.txt.bfo-backup before the first edit.',
                  'Backups are saved under portable Data before the first edit.')
    s = s.replace('Restore every list.txt.bfo-backup under:',
                  'Restore saved scriptlet backups for:')
    s = s.replace('Restore {0} selected list file(s) from .bfo-backup?',
                  'Restore {0} selected list file(s) from BFO backup?')
    return s
