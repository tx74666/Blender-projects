# SOURCE_PREPARED only. Root reviews and owns the single Native window.
param(
 [Parameter(Mandatory=$true)][string]$ModelReport,
 [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ModelReportSha,
 [Parameter(Mandatory=$true)][string]$ManualReport,
 [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManualReportSha
)
$ErrorActionPreference='Stop'
$pairRoot='D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005'
$pairScript=Join-Path $pairRoot 'verify_private_paired_manual_model_fbx_component52.py'
$pairScriptSha='9d17257560f686142ac658c1ed0ac37bd5e8e152b3f3f61eb6f4abf02299a084'
if ((Get-FileHash -LiteralPath $pairScript).Hash.ToLowerInvariant() -ne $pairScriptSha) { throw 'Prepared paired wrapper changed' }
$ModelReport=(Resolve-Path -LiteralPath $ModelReport).ProviderPath
$ManualReport=(Resolve-Path -LiteralPath $ManualReport).ProviderPath
if ($ModelReport -eq $ManualReport) { throw 'Paired inputs must be two distinct actual component reports' }
foreach($pairInput in @(@{Path=$ModelReport;Sha=$ModelReportSha},@{Path=$ManualReport;Sha=$ManualReportSha})) {
 if ((Get-FileHash -LiteralPath $pairInput.Path).Hash.ToLowerInvariant() -ne $pairInput.Sha) { throw 'Actual report hash differs from explicitly frozen CLI input' }
 if (-not $pairInput.Path.StartsWith(($pairRoot+'\'),[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($pairInput.Path) -ne 'report.json' -or [IO.Path]::GetFileName([IO.Path]::GetDirectoryName($pairInput.Path)) -ne 'result') { throw 'Use actual component result/report.json under the fixed validation directory' }
 $pairSource=Get-Content -LiteralPath $pairInput.Path -Raw | ConvertFrom-Json
 if (($pairSource.native_component_verified -isnot [bool]) -or $pairSource.native_component_verified -ne $true -or @($pairSource.errors).Count) { throw 'An input component is not an actual Native PASS' }
 $pairSourceRun=[IO.Path]::GetDirectoryName([IO.Path]::GetDirectoryName($pairInput.Path))
 $pairSourceProcess=Get-Content -LiteralPath (Join-Path $pairSourceRun 'process.json') -Raw | ConvertFrom-Json
 if ($pairSourceProcess.ExitCode -ne 0 -or $pairSourceProcess.TimedOut -ne $false -or $pairSourceProcess.NativeReportPassed -ne $true -or $pairSourceProcess.ChildGone -ne $true -or $pairSourceProcess.SnapshotSha256 -ne 'ab48a806f8e228f3c878da65bab59fe9cdaff2bcbca037f258cf74cacd88dc71') { throw 'Input owned-child receipt is not successful and terminal for fixed ab48' }
}
$pairMemory=Get-CimInstance Win32_OperatingSystem
if ($pairMemory.FreePhysicalMemory -lt 204800) { throw 'Insufficient current memory (200 MiB minimum)' }
if (@(Get-CimInstance Win32_Process -Filter "Name = 'blender.exe'" | Where-Object {$_.CommandLine -match '--background'}).Count) { throw 'Another background Blender is running' }
$pairRun=Join-Path $pairRoot ('actual_private_paired_manual_model_fbx_component_52_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')+'_'+([guid]::NewGuid().ToString('N')))
$pairTemp=Join-Path $pairRun 'native_temp'
New-Item -ItemType Directory -Path $pairTemp | Out-Null
$pairOut=Join-Path $pairRun 'native.stdout.log'
$pairErr=Join-Path $pairRun 'native.stderr.log'
$pairResult=Join-Path $pairRun 'result'
$pairArgs=@('--background','--factory-startup','--disable-autoexec','--threads','1','--python-exit-code','2','--python',('"'+$pairScript+'"'),'--',
 '--model-report',('"'+$ModelReport+'"'),'--model-report-sha',$ModelReportSha,
 '--manual-report',('"'+$ManualReport+'"'),'--manual-report-sha',$ManualReportSha,
 '--output',('"'+$pairResult+'"'),'--expected-script-sha',$pairScriptSha,'--soft-seconds','180')
$pairChild=$null; $pairTimedOut=$false; $pairPeak=0L; $pairSamples=0; $pairNativePass=$false
$pairWatch=[Diagnostics.Stopwatch]::StartNew()
try {
 $pairChild=Start-Process -FilePath 'D:\Blender5.2\blender.exe' -ArgumentList $pairArgs -WindowStyle Hidden -Environment @{TEMP=$pairTemp;TMP=$pairTemp;OMP_NUM_THREADS='1';OPENBLAS_NUM_THREADS='1';MKL_NUM_THREADS='1'} -RedirectStandardOutput $pairOut -RedirectStandardError $pairErr -PassThru
 Write-Output ('OWNED_QA_CHILD_PID='+$pairChild.Id)
 Write-Output ('RUN='+$pairRun)
 while (-not $pairChild.HasExited) {
  $pairRemainingMs=[Math]::Ceiling(240000-$pairWatch.Elapsed.TotalMilliseconds)
  if ($pairRemainingMs -le 0) { $pairChild.Kill(); $pairChild.WaitForExit(); $pairTimedOut=$true; break }
  if ($pairChild.WaitForExit([int][Math]::Min(1000,$pairRemainingMs))) { break }
  $pairChild.Refresh(); $pairPeak=[Math]::Max($pairPeak,$pairChild.PeakWorkingSet64); $pairSamples++
 }
 $pairChild.Refresh()
 $pairReport=Join-Path $pairResult 'report.json'
 if (Test-Path -LiteralPath $pairReport) {
  $pairNative=Get-Content -LiteralPath $pairReport -Raw | ConvertFrom-Json
  $pairNativePass=$true
  foreach($pairFlag in @('native_component_verified','actual_reports_and_processes_verified','full_Rest_binding_verified','full_Action_paths_verified','four_frame_paired_matrices_verified','observable_Dress_skin_motion','owned_native_cleanup','private_scene_disposed','pinned_files_unchanged','canonical_source_files_exact')) {
   if (($pairNative.$pairFlag -isnot [bool]) -or $pairNative.$pairFlag -ne $true) { $pairNativePass=$false }
  }
  foreach($pairFlag in @('current_X_loaded','dynamic_source_surface_equivalent','input_oracle_dynamic_surface_measured','Unity_verified','public_export_verified','export_accepted','final_surface_equivalent','vertex_Cloth_carried_by_bones','material_texture_verified','whole_character_replacement')) {
   if (($pairNative.$pairFlag -isnot [bool]) -or $pairNative.$pairFlag -ne $false) { $pairNativePass=$false }
  }
  if (@($pairNative.errors).Count -ne 0 -or $pairNative.current_artist_validation -ne 'Unmeasured' -or $pairNative.scope -ne 'PRIVATE_ACTUAL_MODEL_MANUAL_FBX_PAIR_COMPONENT_ONLY') { $pairNativePass=$false }
 }
} finally {
 # Only this launched process instance is owned; never stop GUI or another task.
 if ($null -ne $pairChild -and -not $pairChild.HasExited) { $pairChild.Kill(); $pairChild.WaitForExit() }
 if ($null -ne $pairChild) {
  $pairChild.Refresh()
  $pairReceipt=@{Stage='actual_private_paired_manual_model_fbx_component';Case='PRIVATE_fixed_ab48_actual_normal_model_and_Manual_FBX_pair';PID=$pairChild.Id;ExitCode=$pairChild.ExitCode;TimedOut=$pairTimedOut;ElapsedSeconds=$pairWatch.Elapsed.TotalSeconds;PeakSampledWorkingSetBytes=$(if($pairSamples){$pairPeak}else{$null});MemorySamples=$pairSamples;AvailableKiBBefore=$pairMemory.FreePhysicalMemory;ScriptSha256=$pairScriptSha;SnapshotSha256='ab48a806f8e228f3c878da65bab59fe9cdaff2bcbca037f258cf74cacd88dc71';ModelReport=$ModelReport;ModelReportSha256=$ModelReportSha;ManualReport=$ManualReport;ManualReportSha256=$ManualReportSha;Run=$pairRun;NativeReportPassed=$pairNativePass;CurrentArtistValidation='Unmeasured';UnityVerified=$false;ExportAccepted=$false;ChildGone=(-not (Get-Process -Id $pairChild.Id -ErrorAction SilentlyContinue))}
  $pairReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $pairRun 'process.json') -Encoding utf8
  $pairReceipt | ConvertTo-Json -Compress
 }
}
Get-Content -LiteralPath $pairOut -Tail 8
Get-Content -LiteralPath $pairErr -Tail 8
if ($pairTimedOut -or $null -eq $pairChild -or $pairChild.ExitCode -ne 0 -or -not $pairNativePass -or -not $pairReceipt.ChildGone) { exit 2 }
