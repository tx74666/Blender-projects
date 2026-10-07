# Prepared only. Root must coordinate the native resource window before invocation.
$ErrorActionPreference='Stop'
$restMemory=Get-CimInstance Win32_OperatingSystem
if ($restMemory.FreePhysicalMemory -lt 204800) { throw 'Insufficient current memory (200 MiB minimum)' }
if (@(Get-CimInstance Win32_Process -Filter "Name = 'blender.exe'" | Where-Object {$_.CommandLine -match '--background'}).Count) { throw 'Another background Blender is running' }
$restRoot='D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005'
$restScript=Join-Path $restRoot 'verify_private_manual_action_fbx_component52_v2.py'
$restScriptSha='10bae6fd1a042bce5ca60344371e1e4de54a379518e0fe8d6ba0a02a928ac373'
$restSnapshot=Join-Path $restRoot 'actual_plain_native_skin_model_v4_e0b_52_20261007_123727_962_feab010a295d467eae8019cccff98ca8\result\cdesigner-unity-pns-qa\character.blend'
$restWorker='D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\unity_export_worker.py'
if ((Get-FileHash -LiteralPath $restScript).Hash.ToLowerInvariant() -ne $restScriptSha) { throw 'Prepared REST script changed' }
if ((Get-FileHash -LiteralPath $restSnapshot).Hash.ToLowerInvariant() -ne 'ab48a806f8e228f3c878da65bab59fe9cdaff2bcbca037f258cf74cacd88dc71') { throw 'Fixed completed PNS snapshot changed' }
if ((Get-FileHash -LiteralPath $restWorker).Hash.ToLowerInvariant() -ne '1716ff49a231cee8c0663fd17949583eabbfb7ce79791a459682930f40744dcb') { throw 'Pinned model worker changed' }
$restRun=Join-Path $restRoot ('actual_private_manual_action_fbx_component_v2_52_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')+'_'+([guid]::NewGuid().ToString('N')))
$restTemp=Join-Path $restRun 'native_temp'
New-Item -ItemType Directory -Path $restTemp | Out-Null
$restOut=Join-Path $restRun 'native.stdout.log'
$restErr=Join-Path $restRun 'native.stderr.log'
$restResult=Join-Path $restRun 'result'
$restArgs=@('--background','--factory-startup','--disable-autoexec','--threads','1','--python-exit-code','2','--python',('"'+$restScript+'"'),'--','--output',('"'+$restResult+'"'),'--expected-script-sha',$restScriptSha,'--soft-seconds','180')
$restChild=$null; $restPeak=0L; $restSamples=0; $restTimedOut=$false; $restNativePass=$false
$restWatch=[Diagnostics.Stopwatch]::StartNew()
try {
 $restChild=Start-Process -FilePath 'D:\Blender5.2\blender.exe' -ArgumentList $restArgs -WindowStyle Hidden -Environment @{TEMP=$restTemp;TMP=$restTemp;OMP_NUM_THREADS='1';OPENBLAS_NUM_THREADS='1';MKL_NUM_THREADS='1'} -RedirectStandardOutput $restOut -RedirectStandardError $restErr -PassThru
 Write-Output ('OWNED_QA_CHILD_PID='+$restChild.Id)
 Write-Output ('RUN='+$restRun)
 while (-not $restChild.HasExited) {
  $restRemainingMs=[Math]::Ceiling(240000-$restWatch.Elapsed.TotalMilliseconds)
  if ($restRemainingMs -le 0) { $restChild.Kill(); $restChild.WaitForExit(); $restTimedOut=$true; break }
  if ($restChild.WaitForExit([int][Math]::Min(1000,$restRemainingMs))) { break }
  $restChild.Refresh(); $restPeak=[Math]::Max($restPeak,$restChild.PeakWorkingSet64); $restSamples++
 }
 $restChild.Refresh()
 $restReport=Join-Path $restResult 'report.json'
 if (Test-Path -LiteralPath $restReport) {
  $restNative=Get-Content -LiteralPath $restReport -Raw | ConvertFrom-Json
  $restNativePass=$true
  foreach($restFlag in @('native_component_verified','FBX_roundtrip_verified','input_author_restored','snapshot_raw_named_weights_Rest_Body12_assets_exact','sampled_source_protected','owned_native_cleanup','private_scene_disposed','pinned_files_unchanged')) {
   if (($restNative.$restFlag -isnot [bool]) -or $restNative.$restFlag -ne $true) { $restNativePass=$false }
  }
  foreach($restFlag in @('public_admission_verified','public_export_verified','production_model_binding_verified','Unity_verified','Magica_verified','simulation_baked','vertex_Cloth_carried_by_bones','final_surface_equivalent','export_accepted','material_texture_roundtrip_verified','current_X_loaded')) {
   if (($restNative.$restFlag -isnot [bool]) -or $restNative.$restFlag -ne $false) { $restNativePass=$false }
  }
  if (@($restNative.errors).Count -ne 0 -or $restNative.scope -ne 'PRIVATE_MANUAL_BONE_ACTION_FBX_COMPONENT_V2_FIXED_ROOT_CLOSURE_ONLY') { $restNativePass=$false }
 }
} finally {
 # Only the process instance launched above is owned; GUI and other tasks stay intact.
 if ($null -ne $restChild -and -not $restChild.HasExited) { $restChild.Kill(); $restChild.WaitForExit() }
 if ($null -ne $restChild) {
  $restChild.Refresh()
  $restReceipt=@{Stage='actual_private_manual_action_fbx_component';Case='Private_Manual_bone_Action';PID=$restChild.Id;ExitCode=$restChild.ExitCode;TimedOut=$restTimedOut;ElapsedSeconds=$restWatch.Elapsed.TotalSeconds;PeakSampledWorkingSetBytes=$(if($restSamples){$restPeak}else{$null});MemorySamples=$restSamples;AvailableKiBBefore=$restMemory.FreePhysicalMemory;ScriptSha256=$restScriptSha;SnapshotSha256='ab48a806f8e228f3c878da65bab59fe9cdaff2bcbca037f258cf74cacd88dc71';Run=$restRun;NativeReportPassed=$restNativePass;ChildGone=(-not (Get-Process -Id $restChild.Id -ErrorAction SilentlyContinue))}
  $restReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $restRun 'process.json') -Encoding utf8
  $restReceipt | ConvertTo-Json -Compress
 }
}
Get-Content -LiteralPath $restOut -Tail 8
Get-Content -LiteralPath $restErr -Tail 8
if ($restTimedOut -or $null -eq $restChild -or $restChild.ExitCode -ne 0 -or -not $restNativePass -or -not $restReceipt.ChildGone) { exit 2 }
