$ErrorActionPreference = 'Stop'
$dressFolder = $PSScriptRoot
$dressScript = Join-Path $dressFolder 'quantify_private_manual_standard_parent_skin52.py'
$dressScriptSha = '6d6be963f798020bb11388f3140b56e61125ea562b8d1ba796098ea63bd4e0d7'
if ((Get-FileHash -LiteralPath $dressScript -Algorithm SHA256).Hash.ToLowerInvariant() -ne $dressScriptSha) {
    throw 'The reviewed standard-parent diagnostic has changed.'
}
$dressMemory = Get-CimInstance Win32_OperatingSystem
$dressFreeMiB = [math]::Round($dressMemory.FreePhysicalMemory / 1024, 1)
$dressUsedPercent = [math]::Round(100 * (1 - $dressMemory.FreePhysicalMemory / $dressMemory.TotalVisibleMemorySize), 2)
if ($dressFreeMiB -lt 200 -or $dressUsedPercent -ge 98) {
    throw 'Defer this owned background test until the current memory pressure drops.'
}
# Root must hold the fresh serial heavy lease before invoking this launcher.
$dressRun = Join-Path $dressFolder ('actual_private_manual_standard_parent_skin_52_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $dressRun | Out-Null
$dressStdout = Join-Path $dressRun 'stdout.txt'
$dressStderr = Join-Path $dressRun 'stderr.txt'
$dressArguments = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '1', '--python-exit-code', '2',
    '--python', ('"' + $dressScript + '"'), '--', '--output', ('"' + (Join-Path $dressRun 'result') + '"'),
    '--expected-script-sha', $dressScriptSha, '--soft-seconds', '90')
$dressWatch = [Diagnostics.Stopwatch]::StartNew()
$dressChild = $null
$dressPid = $null
$dressPeakMiB = 0.0
$dressTimedOut = $false
$dressExited = $null
$dressExitCode = $null
$dressTerminationReason = $null
$dressErrors = @()
$dressAfterMemory = $null
try {
    $dressChild = Start-Process -FilePath 'D:\Blender5.2\blender.exe' -ArgumentList $dressArguments -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $dressStdout -RedirectStandardError $dressStderr
    $dressPid = $dressChild.Id
    while (-not $dressChild.WaitForExit(1000)) {
        $dressChild.Refresh()
        $dressPeakMiB = [math]::Max($dressPeakMiB, $dressChild.PeakWorkingSet64 / 1MB)
        if ($dressWatch.Elapsed.TotalSeconds -gt 120) {
            # Only the retained Process handle from this invocation may be killed.
            $dressTimedOut = $true
            $dressTerminationReason = 'owned_child_120_second_timeout'
            $dressChild.Kill()
            if (-not $dressChild.WaitForExit(5000)) { throw 'Owned child did not exit after timeout termination.' }
            break
        }
    }
} catch {
    $dressErrors += $_.Exception.ToString()
} finally {
    # Unexpected launcher errors must not leave the known owned child running.
    # No process-name/PID discovery or termination of another owner's process.
    if ($null -ne $dressChild) {
        try {
            $dressChild.Refresh()
            if (-not $dressChild.HasExited) {
                if ($null -eq $dressTerminationReason) { $dressTerminationReason = 'owned_child_cleanup_after_launcher_error' }
                $dressChild.Kill()
                if (-not $dressChild.WaitForExit(5000)) { throw 'Owned child did not exit during launcher cleanup.' }
            }
            $dressExited = $dressChild.HasExited
            if ($dressExited) { $dressExitCode = $dressChild.ExitCode }
        } catch {
            $dressErrors += $_.Exception.ToString()
            $dressExited = $null
        }
    }
    $dressWatch.Stop()
    try { $dressAfterMemory = Get-CimInstance Win32_OperatingSystem } catch { $dressErrors += $_.Exception.ToString() }
}
$dressReceipt = [ordered]@{
    scope = 'Private standard FULL parent/depth TRS/3040 LBS observation; no FBX, artist or Unity operations'
    script = $dressScript
    scriptSha256 = $dressScriptSha
    executable = 'D:\Blender5.2\blender.exe'
    softSeconds = 90
    hardSeconds = 120
    nativeThreads = 1
    ownedChildCreated = ($null -ne $dressChild)
    ownedChildPid = $dressPid
    ownedChildExited = $dressExited
    timedOut = $dressTimedOut
    terminationReason = $dressTerminationReason
    exitCode = $dressExitCode
    elapsedSeconds = $dressWatch.Elapsed.TotalSeconds
    sampledPeakWorkingSetMiB = [math]::Round($dressPeakMiB, 1)
    freeMiBBefore = $dressFreeMiB
    usedPercentBefore = $dressUsedPercent
    freeMiBAfter = $(if ($null -ne $dressAfterMemory) { [math]::Round($dressAfterMemory.FreePhysicalMemory / 1024, 1) } else { $null })
    usedPercentAfter = $(if ($null -ne $dressAfterMemory) { [math]::Round(100 * (1 - $dressAfterMemory.FreePhysicalMemory / $dressAfterMemory.TotalVisibleMemorySize), 2) } else { $null })
    output = $dressRun
    errors = $dressErrors
    artistSceneLoaded = $false
    artistSceneSaved = $false
    FBXWritten = $false
    publicAdmissionAccepted = $false
    UnityOperated = $false
}
try {
    $dressReceipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $dressRun 'launch-receipt.json') -Encoding utf8
} catch {
    $dressErrors += $_.Exception.ToString()
    $dressReceipt.errors = $dressErrors
}
$dressReceipt | ConvertTo-Json -Depth 4 -Compress
if ($null -ne $dressChild) { $dressChild.Dispose() }
if ($dressTimedOut -or $dressExited -ne $true -or $dressExitCode -ne 0 -or $dressErrors.Count -ne 0) { exit 2 }
