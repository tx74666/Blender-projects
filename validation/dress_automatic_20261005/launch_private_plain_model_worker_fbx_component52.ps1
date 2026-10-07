# Prepared source only. Root reviews this file and owns the single Native window.
$ErrorActionPreference='Stop'
$modelMemory=Get-CimInstance Win32_OperatingSystem
if ($modelMemory.FreePhysicalMemory -lt 204800) { throw 'Insufficient current memory (200 MiB minimum)' }
if (@(Get-CimInstance Win32_Process -Filter "Name = 'blender.exe'" | Where-Object {$_.CommandLine -match '--background'}).Count) { throw 'Another background Blender is running' }
$modelRoot='D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005'
$modelScript=Join-Path $modelRoot 'verify_private_plain_model_worker_fbx_component52.py'
$modelScriptSha='8df942d20e2c3b52b1ca9cba3b3cfc134cfdf9748bd59ca3a3b0353a39b7ebaf'
$modelSnapshot=Join-Path $modelRoot 'actual_plain_native_skin_model_v4_e0b_52_20261007_123727_962_feab010a295d467eae8019cccff98ca8\result\cdesigner-unity-pns-qa\character.blend'
$modelWorker='D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\unity_export_worker.py'
if ((Get-FileHash -LiteralPath $modelScript).Hash.ToLowerInvariant() -ne $modelScriptSha) { throw 'Prepared private normal model wrapper changed' }
if ((Get-FileHash -LiteralPath $modelSnapshot).Hash.ToLowerInvariant() -ne 'ab48a806f8e228f3c878da65bab59fe9cdaff2bcbca037f258cf74cacd88dc71') { throw 'Fixed completed PNS snapshot changed' }
if ((Get-FileHash -LiteralPath $modelWorker).Hash.ToLowerInvariant() -ne '1716ff49a231cee8c0663fd17949583eabbfb7ce79791a459682930f40744dcb') { throw 'Pinned production model worker changed' }
$modelRun=Join-Path $modelRoot ('actual_private_plain_model_worker_fbx_component_52_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')+'_'+([guid]::NewGuid().ToString('N')))
$modelTemp=Join-Path $modelRun 'native_temp'
New-Item -ItemType Directory -Path $modelTemp | Out-Null
$modelOut=Join-Path $modelRun 'native.stdout.log'
$modelErr=Join-Path $modelRun 'native.stderr.log'
$modelResult=Join-Path $modelRun 'result'
$modelArgs=@('--background','--factory-startup','--disable-autoexec','--threads','1','--python-exit-code','2','--python',('"'+$modelScript+'"'),'--','--output',('"'+$modelResult+'"'),'--expected-script-sha',$modelScriptSha,'--soft-seconds','180')
$modelChild=$null; $modelTimedOut=$false; $modelPeak=0L; $modelSamples=0; $modelNativePass=$false
$modelWatch=[Diagnostics.Stopwatch]::StartNew()
try {
 $modelChild=Start-Process -FilePath 'D:\Blender5.2\blender.exe' -ArgumentList $modelArgs -WindowStyle Hidden -Environment @{TEMP=$modelTemp;TMP=$modelTemp;OMP_NUM_THREADS='1';OPENBLAS_NUM_THREADS='1';MKL_NUM_THREADS='1'} -RedirectStandardOutput $modelOut -RedirectStandardError $modelErr -PassThru
 Write-Output ('OWNED_QA_CHILD_PID='+$modelChild.Id)
 Write-Output ('RUN='+$modelRun)
 while (-not $modelChild.HasExited) {
  $modelRemainingMs=[Math]::Ceiling(240000-$modelWatch.Elapsed.TotalMilliseconds)
  if ($modelRemainingMs -le 0) { $modelChild.Kill(); $modelChild.WaitForExit(); $modelTimedOut=$true; break }
  if ($modelChild.WaitForExit([int][Math]::Min(1000,$modelRemainingMs))) { break }
  $modelChild.Refresh(); $modelPeak=[Math]::Max($modelPeak,$modelChild.PeakWorkingSet64); $modelSamples++
 }
 $modelChild.Refresh()
 $modelReport=Join-Path $modelResult 'report.json'
 if (Test-Path -LiteralPath $modelReport) {
  $modelNative=Get-Content -LiteralPath $modelReport -Raw | ConvertFrom-Json
  $modelNativePass=$true
  foreach($modelFlag in @('native_component_verified','FBX_component_written','FBX_reimport_verified','original_Mesh_Keys_exact','original_Action_asset_metadata_exact','owned_native_cleanup','private_scene_disposed','pinned_files_unchanged','canonical_source_files_exact','model_worker_remaining_AST_exact')) {
   if (($modelNative.$modelFlag -isnot [bool]) -or $modelNative.$modelFlag -ne $true) { $modelNativePass=$false }
  }
  foreach($modelFlag in @('material_texture_verified','public_export_verified','Unity_verified','export_accepted','animation_verified','paired_binding_verified','final_surface_equivalent','current_X_loaded','whole_character_replacement')) {
   if (($modelNative.$modelFlag -isnot [bool]) -or $modelNative.$modelFlag -ne $false) { $modelNativePass=$false }
  }
  if (@($modelNative.errors).Count -ne 0 -or $modelNative.current_artist_validation -ne 'Unmeasured') { $modelNativePass=$false }
 }
} finally {
 # Only this launched process instance is owned; never stop a GUI or another task.
 if ($null -ne $modelChild -and -not $modelChild.HasExited) { $modelChild.Kill(); $modelChild.WaitForExit() }
 if ($null -ne $modelChild) {
  $modelChild.Refresh()
  $modelReceipt=@{Stage='actual_private_plain_model_worker_fbx_component';Case='PRIVATE_frozen_ab48_partial_Dress_CoshaRig_normal_model';PID=$modelChild.Id;ExitCode=$modelChild.ExitCode;TimedOut=$modelTimedOut;ElapsedSeconds=$modelWatch.Elapsed.TotalSeconds;PeakSampledWorkingSetBytes=$(if($modelSamples){$modelPeak}else{$null});MemorySamples=$modelSamples;AvailableKiBBefore=$modelMemory.FreePhysicalMemory;ScriptSha256=$modelScriptSha;SnapshotSha256='ab48a806f8e228f3c878da65bab59fe9cdaff2bcbca037f258cf74cacd88dc71';Run=$modelRun;NativeReportPassed=$modelNativePass;CurrentArtistValidation='Unmeasured';PairedBindingVerified=$false;ChildGone=(-not (Get-Process -Id $modelChild.Id -ErrorAction SilentlyContinue))}
  $modelReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $modelRun 'process.json') -Encoding utf8
  $modelReceipt | ConvertTo-Json -Compress
 }
}
Get-Content -LiteralPath $modelOut -Tail 8
Get-Content -LiteralPath $modelErr -Tail 8
if ($modelTimedOut -or $null -eq $modelChild -or $modelChild.ExitCode -ne 0 -or -not $modelNativePass -or -not $modelReceipt.ChildGone) { exit 2 }
