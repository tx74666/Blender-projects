# SOURCE_PREPARED only. Root must hold the fresh, serial Native/heavy lease.
# Distinct projected Dress target only; no whole-Cosha/Prefab replacement.
$ErrorActionPreference = 'Stop'
$dressFolder = $PSScriptRoot
$dressScript = Join-Path $dressFolder 'verify_private_standard_target_paired_fbx52.py'
$dressScriptSha = '377423ebf7f94600dfc44cedceefd5276b5e69edfbadbf0c0d58cff22d6a786f'
$dressExecutable = 'D:\Blender5.2\blender.exe'
if ((Get-FileHash -LiteralPath $dressScript -Algorithm SHA256).Hash.ToLowerInvariant() -ne $dressScriptSha) {
    throw 'The reviewed private target component has changed.'
}
$dressLauncherSha = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
$dressMemory = Get-CimInstance Win32_OperatingSystem
$dressFreeMiB = [double]$dressMemory.FreePhysicalMemory / 1024
$dressUsedPercent = 100 * (1 - [double]$dressMemory.FreePhysicalMemory / $dressMemory.TotalVisibleMemorySize)
if ($dressFreeMiB -lt 200 -or $dressUsedPercent -ge 98) {
    throw 'Defer this owned background test until memory pressure drops.'
}
$dressProcesses = @(Get-CimInstance Win32_Process -Filter "Name = 'blender.exe'")
if (@($dressProcesses | Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) }).Count -ne 0) {
    throw 'Blender background-overlap status is unavailable; do not start another child.'
}
if (@($dressProcesses | Where-Object { $_.CommandLine -match '(?i)(?:^|\s)(?:--background|-b)(?=\s|$)' }).Count -ne 0) {
    throw 'Another background Blender is running; keep Native work serial.'
}
$dressRun = Join-Path $dressFolder ('actual_private_standard_target_paired_fbx_52_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '_' + [guid]::NewGuid().ToString('N'))
$dressTemp = Join-Path $dressRun 'native_temp'
New-Item -ItemType Directory -Path $dressTemp | Out-Null
$dressResult = Join-Path $dressRun 'result'
$dressReportPath = Join-Path $dressResult 'report.json'
$dressReceiptPath = Join-Path $dressRun 'launch-receipt.json'
$dressArguments = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '1', '--python-exit-code', '2',
    '--python', ('"' + $dressScript + '"'), '--', '--output', ('"' + $dressResult + '"'),
    '--expected-script-sha', $dressScriptSha, '--soft-seconds', '180')
$dressWatch = [Diagnostics.Stopwatch]::StartNew()
$dressChild = $null
$dressPid = $null
$dressPeakBytes = 0L
$dressMemorySamples = 0
$dressTimedOut = $false
$dressExited = $null
$dressExitCode = $null
$dressTerminationReason = $null
$dressErrors = @()
$dressAfterMemory = $null
$dressNativePassed = $false
$dressFullPins = $false
$dressFlags = [ordered]@{}
$dressReportSha = $null
$dressNativeScope = $null
$dressReceiptWritten = $false
$dressRequiredTrue = @('source_stage_native_complete', 'target_FBX_component_observation_complete',
    'source_77_mesh_Rest_Body12_Actions_assets_protected', 'source_pose_channels_restored',
    'owned_native_cleanup', 'private_scene_disposed', 'pinned_files_unchanged', 'canonical_source_files_exact',
    'non_Dress184_strict_passed', 'target_model_worker_verified', 'target_animation_worker_verified',
    'target_FBX_roundtrip_verified', 'target_pair_native_cleanup', 'target_pair_factory_disposed',
    'all33_Dress_Action_paths_preserved', 'physics_omitted')
$dressRequiredFalse = @('current_X_loaded', 'original_Manual_equivalent', 'original_Manual_export_accepted',
    'manual_original_preserved', 'simulation_baked', 'manifest_packet_created', 'target_Direct_public_export_accepted',
    'public_admission_verified', 'public_export_verified', 'production_model_binding_verified',
    'Unity_verified', 'Magica_verified', 'export_accepted', 'approximate_export_accepted',
    'final_surface_equivalent', 'vertex_Cloth_carried_by_bones')
try {
    $dressChild = Start-Process -FilePath $dressExecutable -ArgumentList $dressArguments -WindowStyle Hidden -PassThru `
        -Environment @{TEMP=$dressTemp; TMP=$dressTemp; OMP_NUM_THREADS='1'; OPENBLAS_NUM_THREADS='1'; MKL_NUM_THREADS='1'} `
        -RedirectStandardOutput (Join-Path $dressRun 'stdout.txt') -RedirectStandardError (Join-Path $dressRun 'stderr.txt')
    $dressPid = $dressChild.Id
    while (-not $dressChild.HasExited) {
        $dressRemainingMs = [math]::Ceiling(230000 - $dressWatch.Elapsed.TotalMilliseconds)
        if ($dressRemainingMs -le 0) {
            $dressTimedOut = $true
            $dressTerminationReason = 'owned_child_230_second_timeout'
            $dressChild.Kill()
            if (-not $dressChild.WaitForExit(5000)) { throw 'Owned child did not exit after timeout termination.' }
            break
        }
        if ($dressChild.WaitForExit([int][math]::Min(1000, $dressRemainingMs))) { break }
        $dressChild.Refresh()
        if (-not $dressChild.HasExited) {
            # Sample while the retained child is alive; never read peak after exit.
            $dressPeakBytes = [math]::Max($dressPeakBytes, $dressChild.PeakWorkingSet64)
            $dressMemorySamples++
        }
    }
} catch {
    $dressErrors += $_.Exception.ToString()
} finally {
    # Only this invocation's retained Process instance may be terminated.
    # No PID/name discovery, GUI closure or another owner's child termination.
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
try {
    if ($dressExited -ne $true) { throw 'Cannot accept a report from a nonterminal/unknown owned child.' }
    $dressNative = Get-Content -LiteralPath $dressReportPath -Raw | ConvertFrom-Json
    $dressReportSha = (Get-FileHash -LiteralPath $dressReportPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $dressNativeScope = $dressNative.scope
    if ($dressNativeScope -ne 'PRIVATE_DISTINCT_STANDARD_TARGET_MODEL_AND_ACTION_ACTUAL_FBX_COMPONENT_V1') { throw 'Unexpected component scope.' }
    $dressValid = $true
    foreach ($dressFlag in $dressRequiredTrue) {
        $dressValue = $dressNative.$dressFlag
        $dressFlags[$dressFlag] = $dressValue
        if ($dressValue -isnot [bool] -or $dressValue -ne $true) { $dressValid = $false }
    }
    foreach ($dressFlag in $dressRequiredFalse) {
        $dressValue = $dressNative.$dressFlag
        $dressFlags[$dressFlag] = $dressValue
        if ($dressValue -isnot [bool] -or $dressValue -ne $false) { $dressValid = $false }
    }
    if (@($dressNative.errors).Count -ne 0 -or @($dressNative.samples).Count -ne 3 -or @($dressNative.target_FBX_samples).Count -ne 4) { $dressValid = $false }
    $dressSemantics = $dressNative.distinct_target_semantics
    foreach ($dressFlag in @('manual_original_preserved', 'simulation_baked', 'source_package_verified', 'release_packet_created', 'Unity_Avatar_slot_GUID_localIDs_verified')) {
        if ($dressSemantics.$dressFlag -isnot [bool] -or $dressSemantics.$dressFlag -ne $false) { $dressValid = $false }
    }
    if ($dressSemantics.physics_omitted -isnot [bool] -or $dressSemantics.physics_omitted -ne $true -or $null -ne $dressSemantics.source_package) { $dressValid = $false }
    $dressPinProperties = @($dressNative.pins.PSObject.Properties)
    if ($dressPinProperties.Count -eq 0 -or $dressNative.pins.$dressScript -ne $dressScriptSha) { throw 'Full pin receipt/self pin is missing.' }
    foreach ($dressPin in $dressPinProperties) {
        if ($dressPin.Value -isnot [string] -or $dressPin.Value -cnotmatch '^[0-9a-f]{64}$' -or
            (Get-FileHash -LiteralPath $dressPin.Name -Algorithm SHA256).Hash.ToLowerInvariant() -ne $dressPin.Value) {
            throw ('Final full source/input pin differs: ' + $dressPin.Name)
        }
    }
    if ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $dressLauncherSha) { throw 'Launcher source changed during invocation.' }
    $dressFullPins = $true
    $dressNativePassed = $dressValid
} catch {
    $dressNativePassed = $false
    $dressErrors += $_.Exception.ToString()
}
$dressPassed = ($dressNativePassed -and $dressFullPins -and $dressExited -eq $true -and $dressExitCode -eq 0 -and -not $dressTimedOut -and $dressErrors.Count -eq 0)
$dressReceipt = [ordered]@{
    scope = 'Private distinct projected Dress target model plus Action actual FBX pair only'
    Stage = 'actual_private_standard_target_paired_fbx_component'
    Case = 'PRIVATE_fixed_derived_Dress_standard_target_only'
    script = $dressScript
    scriptSha256 = $dressScriptSha
    launcherSha256 = $dressLauncherSha
    executable = $dressExecutable
    softSeconds = 180
    hardSeconds = 230
    nativeThreads = 1
    ownedChildCreated = ($null -ne $dressChild)
    ownedChildPid = $dressPid
    ownedChildExited = $dressExited
    timedOut = $dressTimedOut
    terminationReason = $dressTerminationReason
    exitCode = $dressExitCode
    elapsedSeconds = $dressWatch.Elapsed.TotalSeconds
    sampledPeakWorkingSetBytes = $(if ($dressMemorySamples) { $dressPeakBytes } else { $null })
    memorySamples = $dressMemorySamples
    freeMiBBefore = $dressFreeMiB
    usedPercentBefore = $dressUsedPercent
    freeMiBAfter = $(if ($null -ne $dressAfterMemory) { [double]$dressAfterMemory.FreePhysicalMemory / 1024 } else { $null })
    usedPercentAfter = $(if ($null -ne $dressAfterMemory) { 100 * (1 - [double]$dressAfterMemory.FreePhysicalMemory / $dressAfterMemory.TotalVisibleMemorySize) } else { $null })
    backgroundOverlapChecked = $true
    output = $dressRun
    reportPath = $dressReportPath
    reportSha256 = $dressReportSha
    actualComponentScope = $dressNativeScope
    actualGateFlags = $dressFlags
    fullSourceInputPinsRechecked = $dressFullPins
    NativeReportPassed = $dressNativePassed
    Passed = $dressPassed
    errors = $dressErrors
    sourceStageInput = 'Fixed failed derived Action animation.blend; not current Artist X'
    sourceStageInputSha256 = 'e83ddc978a04484d8f3c6cc263c5d085e5cab1d50bb1682c71046b1d6c363cc8'
    actualTargetProofSha256 = 'f2910c70db415fd4e48a929ebfcb68b6a93e3e6e8e43010ec3dc79dc45ef8b35'
    artistSceneLoaded = $false
    artistSceneSaved = $false
    originalManualEquivalent = $false
    publicAdmissionAccepted = $false
    publicExportAccepted = $false
    UnityVerified = $false
    UnityOperated = $false
    simulationBaked = $false
    wholeCoshaReplacement = $false
    PrefabReplacement = $false
    releasePacketCreated = $false
}
try {
    $dressReceipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $dressReceiptPath -Encoding utf8
    $dressReceiptWritten = $true
} catch {
    $dressPassed = $false
    $dressErrors += $_.Exception.ToString()
}
if ($null -ne $dressChild) { $dressChild.Dispose() }
# Terminal output is a compact JSON summary; the complete receipt stays on disk.
[ordered]@{Passed=$dressPassed; NativeReportPassed=$dressNativePassed; ownedChildPid=$dressPid;
    ownedChildExited=$dressExited; exitCode=$dressExitCode; timedOut=$dressTimedOut;
    elapsedSeconds=$dressWatch.Elapsed.TotalSeconds; sampledPeakWorkingSetBytes=$dressReceipt.sampledPeakWorkingSetBytes;
    receiptWritten=$dressReceiptWritten; receiptPath=$dressReceiptPath; reportSha256=$dressReportSha;
    errorsCount=$dressErrors.Count; publicExportAccepted=$false; originalManualEquivalent=$false; UnityVerified=$false} | ConvertTo-Json -Compress
if (-not $dressPassed -or -not $dressReceiptWritten) { exit 2 }
