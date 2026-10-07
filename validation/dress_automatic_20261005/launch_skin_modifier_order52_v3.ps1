$ErrorActionPreference = 'Stop'
$probeMemory = Get-CimInstance Win32_OperatingSystem
if ($probeMemory.FreePhysicalMemory -lt 204800) { throw 'Current available memory is below 200 MiB.' }
if (@(Get-CimInstance Win32_Process -Filter "Name = 'blender.exe'" | Where-Object { $_.CommandLine -match '--background' }).Count) { throw 'Another background Blender is running.' }
$probeRoot = 'D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005'
$probeScript = Join-Path $probeRoot 'probe_skin_modifier_order52_v3.py'
$probeSha = '388c6ce264648bec4755c4054478299eab86ff23e8245c98ffd926a1c9ad3aab'
if ((Get-FileHash -LiteralPath $probeScript -Algorithm SHA256).Hash.ToLowerInvariant() -ne $probeSha) { throw 'Diagnostic source changed.' }
$probeRun = Join-Path $probeRoot ('actual_skin_modifier_order_v3_52_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '_' + [guid]::NewGuid().ToString('N'))
$probeTemp = Join-Path $probeRun 'native_temp'
New-Item -ItemType Directory -Path $probeTemp | Out-Null
$probeOut = Join-Path $probeRun 'stdout.log'
$probeErr = Join-Path $probeRun 'stderr.log'
$probeArgs = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '1', '--python-exit-code', '2', '--python', ('"' + $probeScript + '"'), '--', '--output', ('"' + (Join-Path $probeRun 'result') + '"'), '--core-sha256', $probeSha)
$probeChild = Start-Process -FilePath 'D:\Blender5.2\blender.exe' -ArgumentList $probeArgs -WindowStyle Hidden -Environment @{ TEMP = $probeTemp; TMP = $probeTemp } -RedirectStandardOutput $probeOut -RedirectStandardError $probeErr -PassThru
Write-Output ('OWNED_CHILD_PID=' + $probeChild.Id)
Write-Output ('RUN=' + $probeRun)
$probeWatch = [Diagnostics.Stopwatch]::StartNew()
$probePeak = 0L
$probeTimedOut = $false
while (-not $probeChild.WaitForExit(1000)) {
    $probeChild.Refresh()
    $probePeak = [Math]::Max($probePeak, $probeChild.PeakWorkingSet64)
    if ($probeWatch.Elapsed.TotalSeconds -gt 150) { $probeChild.Kill(); $probeChild.WaitForExit(); $probeTimedOut = $true; break }
}
$probeChild.Refresh()
$probeReportPath = Join-Path $probeRun 'result\report.json'
$probeStatus = $null
if (Test-Path -LiteralPath $probeReportPath) { $probeReport = Get-Content -Raw -LiteralPath $probeReportPath | ConvertFrom-Json; $probeStatus = $probeReport.status }
$probeReceipt = @{ PID = $probeChild.Id; ChildGone = (-not (Get-Process -Id $probeChild.Id -ErrorAction SilentlyContinue)); ExitCode = $probeChild.ExitCode; TimedOut = $probeTimedOut; ElapsedSeconds = $probeWatch.Elapsed.TotalSeconds; PeakWorkingSetBytes = $probePeak; AvailableKiBBefore = $probeMemory.FreePhysicalMemory; ScriptSha256 = $probeSha; Run = $probeRun; ReportStatus = $probeStatus }
$probeReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $probeRun 'process.json') -Encoding utf8
$probeReceipt | ConvertTo-Json -Compress
Get-Content -LiteralPath $probeOut -Tail 5
Get-Content -LiteralPath $probeErr -Tail 7
if ($probeTimedOut -or $probeChild.ExitCode -ne 0 -or $probeStatus -ne 'measured') { exit 2 }