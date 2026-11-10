[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$exe=Join-Path $repo 'work/stage/BraveFreeOrigin-NativePortable/BraveFreeOrigin.exe'
$upstreamTest=Join-Path $repo 'work/upstream/tools/Test-App.ps1'
if (!(Test-Path $exe) -or !(Test-Path $upstreamTest)) { throw 'Expected built executable and upstream test source' }
# The selftest does NOT run the real Brave policy/apply UI and does not require UAC.
$testOut=Join-Path $repo 'work/selftest-report'
New-Item -ItemType Directory -Path $testOut -Force | Out-Null
$env:BFO_TEST_OUT=$testOut
$env:BFO_TEST_SHOTS='0'
$psi=New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName=$exe
$psi.Arguments='-SelfTest "'+$upstreamTest+'"'
$psi.UseShellExecute=$false
$psi.WorkingDirectory=Join-Path $repo 'work/stage/BraveFreeOrigin-NativePortable'
$proc=[System.Diagnostics.Process]::Start($psi)
if (!$proc.WaitForExit(240000)) { try { $proc.Kill() } catch {} ; throw 'Upstream sandbox self-test exceeded timeout' }
if ($proc.ExitCode -ne 0) { throw "Compiled EXE upstream self-test failed, exit=$($proc.ExitCode), report: $testOut" }
$report=Join-Path $testOut 'report.txt'
if (!(Test-Path $report)) { throw 'Compiled EXE ran but no upstream sandbox report was produced' }
if (Select-String -Path $report -Pattern '^FAIL\s') { throw 'Upstream sandbox report includes failure(s)' }
Write-Host 'AUTOMATED-RUNTIME-TESTED: compiled EXE executed upstream sandbox tests successfully'
Write-Host 'NOT YET VERIFIED: interactive GUI, live HKLM/hosts/Brave modifications, relocation and UAC on user desktop'

# Original upstream's other developer tests exercise locale catalog and
# one-line bootstrap (against a local fake server, without touching real Brave).
foreach ($suite in @('Test-Locales.ps1','Test-Bootstrap.ps1')) {
    $file = Join-Path $repo ("work/upstream/tools/" + $suite)
    if (!(Test-Path $file)) { throw "Missing upstream test suite: $suite" }
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $file
    if ($LASTEXITCODE -ne 0) { throw "Upstream $suite failed, exit=$LASTEXITCODE" }
    Write-Host "AUTOMATED-RUNTIME-TESTED: $suite passed"
}
