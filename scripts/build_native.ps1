<#!
Build complete NATIVE portable product from a verified upstream Git release.
Runs unattended on GitHub's hosted Windows runner, not on user's local PC.
No third-party script-to-exe compiler or unverified binary download required.
!#>
[CmdletBinding()]
param([string]$Version='latest')
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repo
New-Item -ItemType Directory -Path 'work','dist' -Force | Out-Null
if (Test-Path 'work/upstream') { throw 'Refusing to overwrite pre-existing work/upstream. Use a fresh runner or remove it manually.' }
& python 'scripts/resolve_source.py' --version $Version --destination 'work/upstream'
if ($LASTEXITCODE -ne 0) { throw 'Release/source resolver failed' }
$resolved = Get-Content 'work/build_identity.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$inputs = @('host/BraveFreeOriginHost.cs','host/app.manifest','scripts/adapt_source.py','scripts/patch_expert.py','scripts/build_native.ps1','docs/PACKAGE-README.txt')
$builderHash = [System.Security.Cryptography.SHA256]::Create()
try {
    $concatenated = New-Object System.IO.MemoryStream
    foreach ($path in $inputs) {
        $data = [System.IO.File]::ReadAllBytes((Resolve-Path $path).Path)
        $concatenated.Write($data,0,$data.Length)
    }
    $packageHash = ([BitConverter]::ToString($builderHash.ComputeHash($concatenated.ToArray()))).Replace('-','').ToLowerInvariant().Substring(0,8)
} finally { $builderHash.Dispose(); $concatenated.Dispose() }
$preTag = "portable-bfo-$($resolved.upstream_release)-native-b1r2-g$($resolved.upstream_commit.Substring(0,8))-p$packageHash"
# Protect an existing verified release from recompilation with different PE timestamps.
if ($env:GITHUB_ACTIONS -eq 'true') {
    $oldError = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { $oldRelease = & gh release view $preTag --repo $env:GITHUB_REPOSITORY --json 'body,isDraft,assets' 2>&1; $oldExit = $LASTEXITCODE }
    finally { $ErrorActionPreference = $oldError }
    if ($oldExit -eq 0) {
        $record = $oldRelease | ConvertFrom-Json
        if ($record.isDraft -or ($record.body -notlike '*portable-release-publisher:managed:v2*')) {
            throw "An unverified/manual/draft release already uses $preTag; refusing replacement"
        }
        $hasZip = @($record.assets | Where-Object { $_.name -match '^BraveFreeOrigin-NativePortable-.*\.zip$' }).Count -eq 1
        $hasChecksum = @($record.assets | Where-Object { $_.name -eq 'SHA256SUMS.txt' }).Count -eq 1
        if (-not $hasZip -or -not $hasChecksum) {
            throw "Existing release $preTag is missing expected assets; refusing skip or overwrite"
        }
        Write-Host "Already published by pinned publisher: $preTag. Identical build identity; skipping compile and republish."
        if ($env:GITHUB_OUTPUT) {
            $utf8 = New-Object System.Text.UTF8Encoding($false)
            [System.IO.File]::AppendAllText($env:GITHUB_OUTPUT, "skip=true`nrelease_tag=$preTag`n",$utf8)
        }
        return
    }
    $errorText = ($oldRelease | Out-String)
    if ($errorText -notmatch '(?i)not found|404|release not found') {
        throw "Could not verify existing release state: $errorText"
    }
}
& python 'scripts/adapt_source.py' --upstream 'work/upstream/Brave-Free-Origin.ps1' --output 'work/Brave-Free-Origin-Native.ps1'
if ($LASTEXITCODE -ne 0) { throw 'Fail-closed application adapter failed' }
$tokens=$null; $parseErrors=$null
[void][System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path 'work/Brave-Free-Origin-Native.ps1').Path, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) {
    # Report the actual broken lines, not just the closing brace's token.
    # This makes adapter regressions much easier to pinpoint from Actions logs.
    $lines = [System.IO.File]::ReadAllLines((Resolve-Path 'work/Brave-Free-Origin-Native.ps1').Path, [System.Text.Encoding]::ASCII)
    foreach ($parseError in $parseErrors) {
        $lineNum = $parseError.Extent.StartLineNumber
        $colNum = $parseError.Extent.StartColumnNumber
        Write-Host ("PowerShell 5.1 parser: line {0}, column {1}: {2}" -f $lineNum,$colNum,$parseError.Message)
        if ($lineNum -gt 0 -and $lineNum -le $lines.Length) {
            Write-Host ("  SOURCE: " + $lines[$lineNum - 1].Trim())
        }
    }
    throw 'Patched source does not parse in Windows PowerShell 5.1'
}

# Build using Microsoft's compiler and built-in Windows PowerShell engine API.
# No NuGet, PowerShell Gallery, third-party PS2EXE, or network package needed.
$csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (!(Test-Path $csc)) { throw 'Windows .NET Framework 4.x C# compiler is missing on runner' }
$automation = [PSObject].Assembly.Location
if (!(Test-Path $automation)) { throw 'Missing Windows PowerShell engine assembly' }
$stage = Join-Path $repo 'work/stage/BraveFreeOrigin-NativePortable'
if (Test-Path $stage) { throw 'Existing stage; refusing to overwrite without review' }
New-Item -ItemType Directory -Path $stage,(Join-Path $stage 'Data'),(Join-Path $stage 'LICENSES'),(Join-Path $stage 'locales') -Force | Out-Null
$target = Join-Path $stage 'BraveFreeOrigin.exe'
$patched = (Resolve-Path 'work/Brave-Free-Origin-Native.ps1').Path
$source = (Resolve-Path 'host/BraveFreeOriginHost.cs').Path
$manifest = (Resolve-Path 'host/app.manifest').Path
& $csc /nologo /target:winexe /platform:x64 /optimize+ "/out:$target" "/reference:$automation" '/reference:System.dll' '/reference:System.Core.dll' '/reference:System.Windows.Forms.dll' "/resource:$patched,BFO_SOURCE" "/win32manifest:$manifest" $source
if ($LASTEXITCODE -ne 0) { throw "Windows C# compiler failed (exit $LASTEXITCODE)" }
if (!(Test-Path $target)) { throw 'Compiled native exe does not exist' }
Copy-Item -LiteralPath 'work/upstream/LICENSE' -Destination (Join-Path $stage 'LICENSES/UPSTREAM-MIT.txt') -ErrorAction Stop
$loc = @(Get-ChildItem 'work/upstream/locales' -File -Filter '*.json' -ErrorAction Stop)
if ($loc.Count -lt 1) { throw 'No upstream locale data; refusing incomplete GUI release' }
foreach ($f in $loc) { Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $stage 'locales' $f.Name) -ErrorAction Stop }
Copy-Item -LiteralPath 'docs/PACKAGE-README.txt' -Destination (Join-Path $stage 'README.txt') -ErrorAction Stop
$identity = Get-Content 'work/build_identity.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$identity | Add-Member -NotePropertyName 'builder_package_hash' -NotePropertyValue $packageHash
$identity | Add-Member -NotePropertyName 'source_adapter_sha256' -NotePropertyValue ((Get-FileHash 'scripts/adapt_source.py' -Algorithm SHA256).Hash.ToLowerInvariant())
$identity | Add-Member -NotePropertyName 'host_source_sha256' -NotePropertyValue ((Get-FileHash 'host/BraveFreeOriginHost.cs' -Algorithm SHA256).Hash.ToLowerInvariant())
$identity | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $stage 'build-identity.json') -Encoding UTF8
# Preserve local Data in place on upgrades: this *staging* Data is deliberately empty.
$version = $identity.upstream_release
$shortSha = $identity.upstream_commit.Substring(0,8)
$tag = $preTag
$name = "BraveFreeOrigin-NativePortable-$version-b1r2-g$shortSha-p$packageHash.zip"
$zip = Join-Path $repo ('dist/' + $name)
if (Test-Path $zip) { throw 'Refusing to overwrite an existing native artifact' }
# Python zipfile creates explicit Data/ directory entry, preserving empty folder.
@'
from pathlib import Path
import sys,zipfile
stage=Path(sys.argv[1]); out=Path(sys.argv[2]); base=stage.parent
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
    for p in sorted(stage.rglob('*')):
        arc=p.relative_to(base).as_posix()
        name=arc+'/' if p.is_dir() else arc
        info=zipfile.ZipInfo(name,date_time=(2020,1,1,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=((0o40755 if p.is_dir() else 0o100644)<<16)
        if p.is_dir():z.writestr(info,b'')
        elif p.is_file():
            if p.is_symlink():raise RuntimeError('Refusing symlink: '+str(p))
            z.writestr(info,p.read_bytes())
print(out)
'@ | Set-Content -LiteralPath 'work/package.py' -Encoding UTF8
& python 'work/package.py' $stage $zip
if ($LASTEXITCODE -ne 0) { throw 'ZIP creation failed' }
& python 'scripts/validate_native.py' $zip
if ($LASTEXITCODE -ne 0) { throw 'ZIP/PE validation failed; release blocked' }
$hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $name" | Set-Content -LiteralPath 'dist/LOCAL-SHA256SUMS.txt' -Encoding ASCII
if ($env:GITHUB_OUTPUT) {
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::AppendAllText($env:GITHUB_OUTPUT, "skip=false`nrelease_tag=$tag`nzip_name=$name`nupstream_version=$version`nsource_sha=$($identity.upstream_commit)`n",$utf8)
}
Write-Host "Validated native ZIP: dist/$name"
Write-Host "SHA256: $hash"
Write-Host "Publisher tag: $tag"
