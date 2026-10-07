# Prepared only. Root must coordinate the native resource window before invocation.
$ErrorActionPreference='Stop'
$restMemory=Get-CimInstance Win32_OperatingSystem
if ($restMemory.FreePhysicalMemory -lt 204800) { throw 'Insufficient current memory (200 MiB minimum)' }
if (@(Get-CimInstance Win32_Process -Filter "Name = 'blender.exe'" | Where-Object {$_.CommandLine -match '--background'}).Count) { throw 'Another background Blender is running' }
$restRoot='D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005'
$restScript=Join-Path $restRoot 'verify_plain_rest_skin_fbx_component52.py'
$restScriptSha='9b93aab9edde5cbf6065e2e8ab9bf81ef27d07a79cd7cb9b792451f466e8564f'
$restSnapshot=Join-Path $restRoot 'actual_plain_native_skin_model_v4_e0b_52_20261007_123727_962_feab010a295d467eae8019cccff98ca8\result\cdesigner-unity-pns-qa\character.blend'
$restWorker='D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\unity_export_worker.py'
if ((Get-FileHash -LiteralPath $restScript).Hash.ToLowerInvariant() -ne $restScriptSha) { throw 'Prepared REST script changed' }
if ((Get-FileHash -LiteralPath $restSnapshot).Hash.ToLowerInvariant() -ne 'ab48a806f8e228f3c878da65bab59fe9cdaff2bcbca037f258cf74cacd88dc71') { throw 'Fixed completed PNS snapshot changed' }
if ((Get-FileHash -LiteralPath $restWorker).Hash.ToLowerInvariant() -ne '1716ff49a231cee8c0663fd17949583eabbfb7ce79791a459682930f40744dcb') { throw 'Pinned model worker changed' }
$restRun=Join-Path $restRoot ('actual_plain_rest_skin_fbx_component_52_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')+'_'+([guid]::NewGuid().ToString('N')))
$restTemp=Join-Path $restRun 'native_temp'
New-Item -ItemType Directory -Path $restTemp | Out-Null
$restOut=Join-Path $restRun 'native.stdout.log'
$restErr=Join-Path $restRun 'native.stderr.log'
$restResult=Join-Path $restRun 'result'
$restArgs=@('--background','--factory-startup','--disable-autoexec','--threads','1','--python-exit-code','2','--python',('"'+$restScript+'"'),'--','--output',('"'+$restResult+'"'),'--expected-script-sha',$restScriptSha,'--soft-seconds','180')
$restChild=Start-Process -FilePath 'D:\Blender5.2\blender.exe' -ArgumentList $restArgs -WindowStyle Hidden -Environment @{TEMP=$restTemp;TMP=$restTemp} -RedirectStandardOutput $restOut -RedirectStandardError $restErr -PassThru
Write-Output ('OWNED_QA_CHILD_PID='+$restChild.Id)
Write-Output ('RUN='+$restRun)
$restWatch=[Diagnostics.Stopwatch]::StartNew(); $restPeak=0L; $restSamples=0; $restTimedOut=$false
while (-not $restChild.WaitForExit(1000)) {
 $restChild.Refresh(); $restPeak=[Math]::Max($restPeak,$restChild.PeakWorkingSet64); $restSamples++
 if ($restWatch.Elapsed.TotalSeconds -gt 240) { $restChild.Kill(); $restChild.WaitForExit(); $restTimedOut=$true; break }
}
$restChild.Refresh()
$restNativePass=$false
$restReport=Join-Path $restResult 'report.json'
if (Test-Path -LiteralPath $restReport) {
 $restNative=Get-Content -LiteralPath $restReport -Raw | ConvertFrom-Json
 $restNativePass=$true
 foreach($restFlag in @('native_component_verified','FBX_reimport_verified','owned_native_cleanup','private_scene_disposed','original_raw_keys_Rest_pose_exact','pinned_files_unchanged')) {
  if (($restNative.$restFlag -isnot [bool]) -or $restNative.$restFlag -ne $true) { $restNativePass=$false }
 }
 if (@($restNative.errors).Count -ne 0) { $restNativePass=$false }
}
$restReceipt=@{Stage='actual_plain_rest_skin_fbx_component';Case='REST_model_only';PID=$restChild.Id;ExitCode=$restChild.ExitCode;TimedOut=$restTimedOut;ElapsedSeconds=$restWatch.Elapsed.TotalSeconds;PeakSampledWorkingSetBytes=$(if($restSamples){$restPeak}else{$null});MemorySamples=$restSamples;AvailableKiBBefore=$restMemory.FreePhysicalMemory;ScriptSha256=$restScriptSha;SnapshotSha256='ab48a806f8e228f3c878da65bab59fe9cdaff2bcbca037f258cf74cacd88dc71';Run=$restRun;NativeReportPassed=$restNativePass;ChildGone=(-not (Get-Process -Id $restChild.Id -ErrorAction SilentlyContinue))}
$restReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $restRun 'process.json') -Encoding utf8
$restReceipt | ConvertTo-Json -Compress
Get-Content -LiteralPath $restOut -Tail 8
Get-Content -LiteralPath $restErr -Tail 8
if ($restTimedOut -or $restChild.ExitCode -ne 0 -or -not $restNativePass -or -not $restReceipt.ChildGone) { exit 2 }
