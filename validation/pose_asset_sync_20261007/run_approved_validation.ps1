$ErrorActionPreference = 'Stop'
$taskFolder = $PSScriptRoot
$env:POSE_APPROVED_SOURCE_ROOT = Join-Path $taskFolder 'approved_release\addons'
$testRoot = 'D:\MyRepository\Blender-addons-by-Randy\tests'
$tests = @('test_control_pose_keymap_blender.py', 'test_control_pose_capture_blender.py',
           'test_control_pose_weights_blender.py', 'test_control_pose_activation_blender.py',
           'test_control_pose_mirror_blender.py')
$results = @()
foreach ($testName in $tests) {
    $memory = Get-CimInstance Win32_OperatingSystem
    if ($memory.FreePhysicalMemory -lt 204800) { throw 'Less than 200 MB free; no new background job started.' }
    $env:POSE_APPROVED_TEST = Join-Path $testRoot $testName
    $logPath = Join-Path $taskFolder ('approved_' + $testName + '.log')
    $began = Get-Date
    & 'D:\Blender5.2\blender.exe' --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python (Join-Path $taskFolder 'approved_suite.py') *> $logPath
    $code = $LASTEXITCODE
    $results += [PSCustomObject]@{test=$testName; exit_code=$code; seconds=((Get-Date)-$began).TotalSeconds; free_kib_before=$memory.FreePhysicalMemory; log=$logPath}
    $results | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskFolder 'approved_suite_runs.json') -Encoding utf8
    Write-Output "POSE_SUITE_EXIT $testName $code"
    if ($code -ne 0) { throw "Approved suite failed; inspect $logPath" }
}
$memory = Get-CimInstance Win32_OperatingSystem
if ($memory.FreePhysicalMemory -lt 204800) { throw 'Less than 200 MB free; Cosha integration not started.' }
& 'D:\Blender5.2\blender.exe' --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python (Join-Path $taskFolder 'actual_cosha.py') *> (Join-Path $taskFolder 'approved_actual_cosha.log')
if ($LASTEXITCODE -ne 0) { throw 'Actual Cosha integration failed; inspect approved_actual_cosha.log' }
Write-Output 'POSE_APPROVED_VALIDATION_COMPLETE'
