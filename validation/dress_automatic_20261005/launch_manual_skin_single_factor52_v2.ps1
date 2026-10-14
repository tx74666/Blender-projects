$ErrorActionPreference = 'Stop'
$dressFolder = $PSScriptRoot
$dressScript = Join-Path $dressFolder 'quantify_private_manual_trs_skin52_v2.py'
$dressScriptSha = '3f00b6a7593471a8cbad0099bf7e439924d12d7619eac6d14cc0bd75c623eda9'
if ((Get-FileHash -LiteralPath $dressScript -Algorithm SHA256).Hash.ToLowerInvariant() -ne $dressScriptSha) {
    throw 'The reviewed single-factor script has changed.'
}
$dressMemory = Get-CimInstance Win32_OperatingSystem
$dressFreeMiB = [math]::Round($dressMemory.FreePhysicalMemory / 1024, 1)
$dressUsedPercent = [math]::Round(100 * (1 - $dressMemory.FreePhysicalMemory / $dressMemory.TotalVisibleMemorySize), 2)
if ($dressFreeMiB -lt 200 -or $dressUsedPercent -ge 98) {
    throw 'Defer this owned background test until the current memory pressure drops.'
}
$dressRun = Join-Path $dressFolder ('actual_private_manual_skin_single_factor_52_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $dressRun | Out-Null
$dressStdout = Join-Path $dressRun 'stdout.txt'
$dressStderr = Join-Path $dressRun 'stderr.txt'
$dressArguments = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '1', '--python-exit-code', '2',
    '--python', ('"' + $dressScript + '"'), '--', '--output', ('"' + (Join-Path $dressRun 'result') + '"'),
    '--expected-script-sha', $dressScriptSha, '--soft-seconds', '90')
$dressWatch = [Diagnostics.Stopwatch]::StartNew()
$dressChild = Start-Process -FilePath 'D:\Blender5.2\blender.exe' -ArgumentList $dressArguments -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $dressStdout -RedirectStandardError $dressStderr
$dressPid = $dressChild.Id
$dressPeakMiB = 0.0
$dressTimedOut = $false
while (-not $dressChild.WaitForExit(1000)) {
    $dressChild.Refresh()
    $dressPeakMiB = [math]::Max($dressPeakMiB, $dressChild.PeakWorkingSet64 / 1MB)
    if ($dressWatch.Elapsed.TotalSeconds -gt 120) {
        # This Process handle belongs only to the child created above.
        $dressChild.Kill()
        $dressChild.WaitForExit()
        $dressTimedOut = $true
        break
    }
}
$dressWatch.Stop()
$dressAfterMemory = Get-CimInstance Win32_OperatingSystem
$dressReceipt = [ordered]@{
    scope = 'Private Blender single-factor DQ/LBS observation; no artist or Unity operations'
    script = $dressScript
    scriptSha256 = $dressScriptSha
    executable = 'D:\Blender5.2\blender.exe'
    ownedChildPid = $dressPid
    ownedChildExited = $dressChild.HasExited
    timedOut = $dressTimedOut
    exitCode = $dressChild.ExitCode
    elapsedSeconds = $dressWatch.Elapsed.TotalSeconds
    sampledPeakWorkingSetMiB = [math]::Round($dressPeakMiB, 1)
    freeMiBBefore = $dressFreeMiB
    usedPercentBefore = $dressUsedPercent
    freeMiBAfter = [math]::Round($dressAfterMemory.FreePhysicalMemory / 1024, 1)
    usedPercentAfter = [math]::Round(100 * (1 - $dressAfterMemory.FreePhysicalMemory / $dressAfterMemory.TotalVisibleMemorySize), 2)
    output = $dressRun
    artistSceneLoaded = $false
    artistSceneSaved = $false
    UnityOperated = $false
}
$dressReceipt | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $dressRun 'launch-receipt.json') -Encoding utf8
$dressReceipt | ConvertTo-Json -Compress
if ($dressTimedOut -or $dressChild.ExitCode -ne 0) { exit 2 }
