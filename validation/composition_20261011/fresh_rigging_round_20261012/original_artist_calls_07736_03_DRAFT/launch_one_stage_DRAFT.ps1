param(
    [Parameter(Mandatory=$true)][ValidateSet('Refresh','Integration','Reader')][string]$Stage,
    [Parameter(Mandatory=$true)][string]$RequestPath,
    [Parameter(Mandatory=$true)][string]$RequestSha256,
    [Parameter(Mandatory=$true)][string]$CallerOutput,
    [Parameter(Mandatory=$true)][string]$ResourceToken,
    [switch]$RootResourceAdmitted,
    [int]$ArtistPid = 14500,
    [string]$ArtistFileTime = 'PENDING_FRESH_ARTIST_FILETIME',
    [int]$SdkPort = 0
)
# SOURCE PREPARATION ONLY. Invoke once only after actual native PASS/END, fresh
# SaveCopy and per-phase source/evidence admission. No automatic next phase/retry.
$ErrorActionPreference = 'Stop'
$taskRound = 'D:\Blender\Projects\Character\X\validation\composition_20261011\fresh_rigging_round_20261012'
$taskPython = 'C:\Users\Randy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskBlender = 'D:\Blender5.2\blender.exe'
$taskSdkCaller = Join-Path $taskRound 'call_original20_artist_sdk_long.py'
if (-not $RootResourceAdmitted -or -not $ResourceToken -or $ResourceToken.Contains('PENDING')) { throw 'Fresh root resource admission required' }
if ($RequestSha256 -notmatch '^[0-9a-f]{64}$') { throw 'Final materialized request SHA required' }
$taskRequest = (Resolve-Path -LiteralPath $RequestPath).Path
$taskOut = [IO.Path]::GetFullPath($CallerOutput)
$taskPrefix = [IO.Path]::GetFullPath($taskRound).TrimEnd('\') + '\'
if (-not $taskRequest.StartsWith($taskPrefix,[StringComparison]::OrdinalIgnoreCase) -or -not $taskOut.StartsWith($taskPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Request/caller must stay in owned ROUND' }
if ((Get-FileHash -LiteralPath $taskRequest -Algorithm SHA256).Hash.ToLower() -ne $RequestSha256) { throw 'Request source changed' }
$taskRequestText = Get-Content -LiteralPath $taskRequest -Raw
if ($taskRequestText -notmatch "CONFIG_SHA256 = '[0-9a-f]{64}'") { throw 'Draft config binding remains unresolved' }
if (Test-Path -LiteralPath $taskOut) { throw 'Use unique absent caller directory; do not retry unknown previous outcome' }
$taskOs = Get-CimInstance Win32_OperatingSystem
$taskFree = [math]::Round($taskOs.FreePhysicalMemory / 1024,1)
if ($taskFree -lt 200) { throw 'Free RAM below 200 MiB; do not start' }
$taskUsedPercent = 100 * (1 - $taskOs.FreePhysicalMemory / $taskOs.TotalVisibleMemorySize)
if ($taskUsedPercent -ge 97.5) {
    $taskOs = Get-CimInstance Win32_OperatingSystem
    $taskFree = [math]::Round($taskOs.FreePhysicalMemory / 1024,1)
    if ($taskFree -lt 200) { throw 'Fresh near-98% memory reread is below threshold; do not start' }
}
if (@(Get-Process blender -ErrorAction SilentlyContinue | Where-Object Id -ne $ArtistPid).Count -ne 0) { throw 'Another Blender child owns the serial slot' }
$taskArtist = Get-Process -Id $ArtistPid
if ($taskArtist.Path -ne $taskBlender -or -not $taskArtist.Responding) { throw 'Original Blender process/executable is not admitted' }
if ($Stage -ne 'Reader') {
    if ($ArtistFileTime -notmatch '^\d+$' -or $taskArtist.StartTime.ToUniversalTime().ToFileTimeUtc().ToString() -ne $ArtistFileTime) { throw 'Original PID/FILETIME changed' }
    if ($SdkPort -le 0 -or $SdkPort -gt 65535) { throw 'Fresh artist listener required' }
    $taskListeners = @(Get-NetTCPConnection -State Listen -LocalPort $SdkPort)
    if (-not $taskListeners.Count -or @($taskListeners | Where-Object OwningProcess -ne $ArtistPid).Count) { throw 'SDK listener belongs to another process' }
    if ((Get-FileHash -LiteralPath $taskSdkCaller -Algorithm SHA256).Hash.ToLower() -ne '7cc0c9fa722e1c76a8c35c9c0d5dfed6d6f09b73e999a3e3b832c18a127691b1') { throw 'SDK caller source changed' }
    $taskExe = $taskPython
    $taskArgv = @('-B',$taskSdkCaller,$taskRequest,$taskOut,$SdkPort.ToString(),$RequestSha256)
} else {
    $taskExpectedCaller = Join-Path $taskRound 'original_artist_calls_07736_03_DRAFT\reader_caller'
    if ($taskOut -ne $taskExpectedCaller) { throw 'Reader entry identity path must match its reviewed launcher path' }
    $taskExe = $taskBlender
    $taskArgv = @('--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',$taskRequest)
}
New-Item -ItemType Directory -Path $taskOut | Out-Null
$taskStartUtc = [DateTime]::UtcNow.ToString('o')
$taskWatch = [Diagnostics.Stopwatch]::StartNew()
$taskChild = Start-Process -FilePath $taskExe -ArgumentList $taskArgv -WindowStyle Hidden -WorkingDirectory $taskRound -RedirectStandardOutput (Join-Path $taskOut 'stdout.txt') -RedirectStandardError (Join-Path $taskOut 'stderr.txt') -PassThru
$taskPid = $taskChild.Id
$taskFileTime = $taskChild.StartTime.ToUniversalTime().ToFileTimeUtc().ToString()
$taskStart = [ordered]@{schema='x.validation.process-start/1';stage=$Stage;pid=$taskPid;process_filetime=$taskFileTime;started_utc=$taskStartUtc;resource_token=$ResourceToken;free_mib=$taskFree;request_sha256=$RequestSha256;argv=$taskArgv;retained_handle=$true}
$taskStart | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskOut 'start.json') -Encoding utf8
if ($Stage -eq 'Reader') {
    # Atomic external identity handoff; the entry is still blank before this check.
    $taskIdentity = [ordered]@{pid=$taskPid;process_filetime=$taskFileTime;resource_token=$ResourceToken;request_sha256=$RequestSha256}
    $taskIdentity | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOut 'launch_identity.tmp') -Encoding utf8
    Move-Item -LiteralPath (Join-Path $taskOut 'launch_identity.tmp') -Destination (Join-Path $taskOut 'launch_identity.json')
}
$taskStart | ConvertTo-Json -Compress -Depth 8
$taskChild.WaitForExit()
$taskChild.Refresh()
$taskWatch.Stop()
$taskLive = Get-Process -Id $taskPid -ErrorAction SilentlyContinue
$taskGone = ($null -eq $taskLive) -or ($taskLive.StartTime.ToUniversalTime().ToFileTimeUtc().ToString() -ne $taskFileTime)
$taskEnd = [ordered]@{schema='x.validation.process-end/1';stage=$Stage;pid=$taskPid;process_filetime=$taskFileTime;retained_handle_natural_exit=$true;exit_code=$taskChild.ExitCode;ended_utc=[DateTime]::UtcNow.ToString('o');elapsed_seconds=$taskWatch.Elapsed.TotalSeconds;owned_process_gone=$taskGone;process_termination_performed=$false;operation_success_inferred=$false}
$taskEnd | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskOut 'end.json') -Encoding utf8
$taskEnd | ConvertTo-Json -Compress -Depth 8
# Exit0 alone is not acceptance: inspect the pinned helper result/report and
# preservation/save fields. SDK UNKNOWN or failure must never trigger retry here.
exit $taskChild.ExitCode

