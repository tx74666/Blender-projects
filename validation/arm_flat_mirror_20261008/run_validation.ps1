$ErrorActionPreference = 'Stop'
$mirrorFolder = 'D:\Blender\Projects\Character\X\validation\arm_flat_mirror_20261008'
$mirrorRepo = 'D:\MyRepository\Blender-addons-by-Randy'
$env:POSE_APPROVED_SOURCE_ROOT = "$mirrorFolder\approved_release_0773\addons"
$mirrorTests = @('test_control_pose_deformation_mirror_blender.py', 'test_control_pose_mirror_blender.py', 'test_control_pose_capture_blender.py', 'test_control_pose_activation_blender.py', 'test_control_pose_native_selection_blender.py', 'test_control_pose_keymap_blender.py')
$mirrorResults = @()
foreach ($mirrorTest in $mirrorTests) {
    $mirrorFree = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory
    if ($mirrorFree -lt 204800) { throw 'Insufficient physical memory for an additional Blender process' }
    $env:POSE_APPROVED_TEST = "$mirrorRepo\tests\$mirrorTest"
    if (-not (Test-Path -LiteralPath $env:POSE_APPROVED_TEST)) { throw "Missing test: $mirrorTest" }
    $mirrorLog = "$mirrorFolder\$mirrorTest.log"
    $mirrorWatch = [System.Diagnostics.Stopwatch]::StartNew()
    & 'D:\Blender5.2\blender.exe' --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python 'D:\Blender\Projects\Character\X\validation\pose_asset_sync_20261007\approved_suite.py' *> $mirrorLog
    $mirrorExit = $LASTEXITCODE
    $mirrorWatch.Stop()
    $mirrorResults += [PSCustomObject]@{test=$mirrorTest; exit_code=$mirrorExit; seconds=$mirrorWatch.Elapsed.TotalSeconds; free_before_kib=$mirrorFree; log=$mirrorLog}
    $mirrorResults | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$mirrorFolder\suite_results.json" -Encoding utf8
    Write-Output "$mirrorTest exit=$mirrorExit seconds=$($mirrorWatch.Elapsed.TotalSeconds)"
    Get-Content -LiteralPath $mirrorLog -Tail 7
    if ($mirrorExit -ne 0) { throw "Blender validation failed: $mirrorTest" }
}
