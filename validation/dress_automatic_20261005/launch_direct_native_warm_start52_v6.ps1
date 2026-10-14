# SOURCE_PREPARED v6. Frozen v5/actual budget failure; 420soft/480hard owned lifecycle.
# Private callable timers only; public FK/full rollback/native75/paired200 remain frozen.
# Current full tree is re-prepared for five sealed animation/worklist sources; no historical runtime-equivalence claim.
# Current source input is re-prepared for the Tuning readiness fix; no historical runtime-equivalence claim.
# Scene is a request for this exact copy, with no fallback: the runner writes
# available.scenes and rejects before requesting any Scene when it is absent.
# Fresh pinned metadata derives one Scene named Scene from this saved copy:
# SC block 2815649/payload 2815681, length 6928, SDNA 767; id 0/name 40.
# This is saved-disk evidence; no live-unsaved/current-Artist or effect acceptance.
#Requires -Version 7.4
param([Parameter(Mandatory=$true)][switch]$HeavyWindowConfirmed)
$ErrorActionPreference='Stop'
if (-not $HeavyWindowConfirmed) { throw 'Root must confirm this current exclusive heavy window.' }

$warmRoot='D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005'
$warmScript=Join-Path $warmRoot 'verify_direct_native_warm_start52_v6.py'
$warmScriptSha='e9a19ccc23e2ebd29dc91b88787c924d829b6b3410f97d6830c99be1ff2ea2ef'
$warmManifestSha='1beec2ae5443048da510529377f165f2a47a66a0e6f37a62ce22b5e3eb903ef1'
$warmInput=Join-Path $warmRoot 'private_saved_input_20261008_181852_135_49beaefcb07040dda907599d2118b163\X.saved-input.blend'
$warmInputSha='377140234b0354966d8e3ac4776aa936fd0921aacc53be630cac3b040727ff8d'
$warmInputReceipt=Join-Path ([IO.Path]::GetDirectoryName($warmInput)) 'input-receipt.json'
$warmInputReceiptSha='fb1ed14128515864c991626303a4f6b92fb506448ca6598b3f169e9aa7e2a39f'
$warmInputMetadata=Join-Path ([IO.Path]::GetDirectoryName($warmInput)) 'source-file-metadata.json'
$warmInputMetadataSha='f93c44ba0b7c6506ae3106467c990009ff794b9f0fedc300097dab6e42626bf7'
$warmScene='Scene'
$warmPython='C:\Program Files\Python312\python.exe'
$warmBinary='D:\Blender5.2\blender.exe'
function Get-WarmHash([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
foreach ($warmPin in @(@{Path=$warmScript;Sha=$warmScriptSha},@{Path=$warmInput;Sha=$warmInputSha},@{Path=$warmInputReceipt;Sha=$warmInputReceiptSha},@{Path=$warmInputMetadata;Sha=$warmInputMetadataSha})) {
 if ((Get-WarmHash $warmPin.Path) -ne $warmPin.Sha) { throw 'Fixed runner/copy/receipt hash changed.' }
}
# Only standard Python and the frozen file readers; this never imports bpy or
# calls the runner main. It verifies the actual current manifest before a child.
$warmManifestCode=@'
import importlib.util,json
from pathlib import Path
p=Path(r'D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005\verify_direct_native_warm_start52_v6.py')
s=importlib.util.spec_from_file_location('warm_launcher_fs_guard',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
v6=m;v5=v6.previous();m=v5.previous().previous().previous().previous()
n,_,_,_=v6.prepared_namespace();base=n['load'](n['BASE'],n['BASE_SHA'],'warm_launch_reader');cold=n['load'](base.COLD,base.COLD_SHA,'warm_launch_cold');q=n['load'](cold.COMPARATOR,cold.COMPARATOR_SHA,'warm_launch_raw');manifest=n['load'](q.SOURCE,q.SOURCE_SHA,'warm_launch_manifest')
_,execution,_,_=v6.namespace();current_pins=execution['main'].__globals__['CURRENT_PINS']
value=manifest.current_manifest();inputs=m.disk_inputs()
input_readers=(execution['main'].__globals__,execution['disk_inputs'].__globals__,vars(execution['_APPEND_SCENE'].__globals__['previous']()))
m.need(all(all(reader[name]==value for name,value in v5.CURRENT_INPUT_PINS.items()) for reader in input_readers),'Actual main/disk_inputs/append input bindings differ')
m.need(current_pins==execution['CURRENT_PINS'] and all(m.sha(path)==sha for path,sha in n['_EXTRA_PINS'].items()) and m.sha(m.PARENT_REPORT)==m.PARENT_REPORT_SHA and all(m.sha(m.RUNTIME/name)==sha for name,sha in current_pins.items()),'Frozen historical or re-prepared current endpoints changed')
print(json.dumps(dict(manifest_sha256=n['digest'](value),manifest=value,input=inputs,input_preparation=v5.input_preparation(),fresh_input_three_closures_exact=True,source_endpoint_pins_verified=True,current_runtime_pins=current_pins,current_pin_updates=v5.CURRENT_PIN_OVERRIDES,current_source_input_reprepared=True,historical_runtime_equivalence_claimed=False),ensure_ascii=False,allow_nan=False))
'@
$warmProofText=& $warmPython -B -c $warmManifestCode
if ($LASTEXITCODE -ne 0) { throw 'Read-only source/input preflight refused; no Native child.' }
$warmProof=($warmProofText -join "`n") | ConvertFrom-Json
if ($warmProof.manifest_sha256 -ne $warmManifestSha -or $warmProof.source_endpoint_pins_verified -isnot [bool] -or -not $warmProof.source_endpoint_pins_verified) { throw 'Prepared complete current manifest changed; no Native child.' }

function Get-WarmMemory {
 $warmOS=Get-CimInstance Win32_OperatingSystem -OperationTimeoutSec 1
 return [ordered]@{FreePhysicalKiB=[long]$warmOS.FreePhysicalMemory;TotalPhysicalKiB=[long]$warmOS.TotalVisibleMemorySize;FreeCommitKiB=[long]$warmOS.FreeVirtualMemory;UsedPercent=(100.0*(1.0-[double]$warmOS.FreePhysicalMemory/[double]$warmOS.TotalVisibleMemorySize))}
}
$warmMemoryBefore=Get-WarmMemory; $warmAdmissionReads=@($warmMemoryBefore)
if ($warmMemoryBefore.FreePhysicalKiB -lt 204800 -or $warmMemoryBefore.UsedPercent -ge 98.0) {
 Start-Sleep -Seconds 1
 $warmMemoryBefore=Get-WarmMemory; $warmAdmissionReads+=,$warmMemoryBefore
}
if ($warmMemoryBefore.FreePhysicalKiB -lt 204800 -or $warmMemoryBefore.UsedPercent -ge 98.0) { throw 'Current resource guard: 200 MiB available and below 98% after reread; no child.' }
if (@(Get-CimInstance Win32_Process -Filter "Name = 'blender.exe'" | Where-Object {$_.CommandLine -match '(?i)(--background|(?:^|\s)-b(?:\s|$))'}).Count) { throw 'Another background Blender is running; no overlap.' }

$warmRun=Join-Path $warmRoot ('actual_direct_native_warm_start_v6_52_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')+'_'+([guid]::NewGuid().ToString('N')))
$warmRun=[IO.Path]::GetFullPath($warmRun)
if (-not $warmRun.StartsWith(($warmRoot+'\'),[StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $warmRun)) { throw 'Fresh owned validation directory required.' }
$warmTemp=Join-Path $warmRun 'native_temp'; New-Item -ItemType Directory -Path $warmTemp | Out-Null
$warmOut=Join-Path $warmRun 'native.stdout.log'; $warmErr=Join-Path $warmRun 'native.stderr.log'; $warmResult=Join-Path $warmRun 'result'
$warmLauncherSha=Get-WarmHash $PSCommandPath
function Write-WarmReceipt([string]$Path,$Value) {
 $warmPart=$Path+'.part'
 [IO.File]::WriteAllText($warmPart,($Value | ConvertTo-Json -Depth 32),[Text.UTF8Encoding]::new($false))
 [IO.File]::Move($warmPart,$Path,$true)
}
$warmReceipt=[ordered]@{Stage='actual_direct_native_warm_start_v6_52';Status='LaunchPending';PID=$null;ProcessStartedUtc=$null;ProcessStartedUtcTicks=$null;OwnedProcessHandleHeld=$false;ChildGone=$null;ExitCode=$null;TimedOut=$false;ForcedTermination=$false;NativeReportPassed=$false;ElapsedSeconds=$null;PeakSampledWorkingSetBytes=$null;MemorySamples=0;MemoryAdmissionReads=$warmAdmissionReads;MemoryPressureSeen=$false;MinimumAvailableKiBDuringPoll=$null;MaximumUsedPercentDuringPoll=$null;LauncherSha256=$warmLauncherSha;ScriptSha256=$warmScriptSha;ExpectedSourceManifestSha256=$warmManifestSha;SourceBefore=$warmProof.manifest;SavedCopy=$warmInput;SavedCopySha256=$warmInputSha;InputReceipt=$warmInputReceipt;InputReceiptSha256=$warmInputReceiptSha;SavedSceneRequest=$warmScene;InputMetadata=$warmInputMetadata;InputMetadataSha256=$warmInputMetadataSha;SavedSceneFsEvidence=$warmProof.input_preparation.filesystem_metadata;FreshInputThreeClosuresExact=$warmProof.fresh_input_three_closures_exact;NativeSceneMembershipVerified=$false;SoftSeconds=420;HardSeconds=480;SingleThread=$true;Run=$warmRun;CurrentLiveUnsavedVerified=$false;EffectAccepted=$false;UnityVerified=$false;ExportAccepted=$false;Errors=@()}
Write-WarmReceipt (Join-Path $warmRun 'launch.json') $warmReceipt
$warmArgs=@('--background','--factory-startup','--disable-autoexec','--threads','1','--python-exit-code','2','--python',('"'+$warmScript+'"'),'--','--output',('"'+$warmResult+'"'),'--expected-source-manifest-sha',$warmManifestSha,'--scene',$warmScene,'--body-object','Cosha','--dress-object','Dress','--soft-seconds','420')
$warmChild=$null; $warmOwnedHandle=$null; $warmPeak=0L; $warmSamples=0; $warmWatch=[Diagnostics.Stopwatch]::StartNew(); $warmNextMemoryRead=5.0; $warmAfterProof=$null
try {
 # Repeat the source and overlap guard immediately before the only launch.
 if ((Get-WarmHash $warmScript) -ne $warmScriptSha -or (Get-WarmHash $warmInput) -ne $warmInputSha -or (Get-WarmHash $warmInputReceipt) -ne $warmInputReceiptSha -or (Get-WarmHash $PSCommandPath) -ne $warmLauncherSha) { throw 'Prepared launch artifacts changed.' }
 if (@(Get-CimInstance Win32_Process -Filter "Name = 'blender.exe'" | Where-Object {$_.CommandLine -match '(?i)(--background|(?:^|\s)-b(?:\s|$))'}).Count) { throw 'A background Blender appeared before launch.' }
 $warmChild=Start-Process -FilePath $warmBinary -ArgumentList $warmArgs -WindowStyle Hidden -Environment @{TEMP=$warmTemp;TMP=$warmTemp;OMP_NUM_THREADS='1';OPENBLAS_NUM_THREADS='1';MKL_NUM_THREADS='1'} -RedirectStandardOutput $warmOut -RedirectStandardError $warmErr -PassThru
 $warmOwnedHandle=$warmChild.Handle # Retain this process instance through finally; never look up a PID to kill.
 if ($warmOwnedHandle -eq [IntPtr]::Zero) { throw 'Owned child process handle unavailable.' }
 $warmReceipt.PID=$warmChild.Id; $warmReceipt.ProcessStartedUtc=$warmChild.StartTime.ToUniversalTime().ToString('o'); $warmReceipt.ProcessStartedUtcTicks=$warmChild.StartTime.ToUniversalTime().Ticks; $warmReceipt.OwnedProcessHandleHeld=$true; $warmReceipt.Status='Running'
 Write-WarmReceipt (Join-Path $warmRun 'launch.json') $warmReceipt
 Write-Output ('OWNED_QA_CHILD_PID='+$warmChild.Id); Write-Output ('RUN='+$warmRun)
 while (-not $warmChild.HasExited) {
  $warmRemainingMs=[Math]::Ceiling(480000-$warmWatch.Elapsed.TotalMilliseconds)
  if ($warmRemainingMs -le 0) { $warmReceipt.TimedOut=$true; $warmReceipt.ForcedTermination=$true; $warmChild.Kill(); if (-not $warmChild.WaitForExit(5000)) {throw 'Owned child did not exit within 5 seconds after its timeout Kill.'}; break }
  if ($warmChild.WaitForExit([int][Math]::Min(1000,$warmRemainingMs))) { break }
  $warmChild.Refresh(); $warmPeak=[Math]::Max($warmPeak,$warmChild.PeakWorkingSet64); $warmSamples++
  if ($warmWatch.Elapsed.TotalSeconds -ge $warmNextMemoryRead) {
   $warmReading=Get-WarmMemory; $warmNextMemoryRead=$warmWatch.Elapsed.TotalSeconds+5.0
   if ($null -eq $warmReceipt.MinimumAvailableKiBDuringPoll -or $warmReading.FreePhysicalKiB -lt $warmReceipt.MinimumAvailableKiBDuringPoll) {$warmReceipt.MinimumAvailableKiBDuringPoll=$warmReading.FreePhysicalKiB}
   if ($null -eq $warmReceipt.MaximumUsedPercentDuringPoll -or $warmReading.UsedPercent -gt $warmReceipt.MaximumUsedPercentDuringPoll) {$warmReceipt.MaximumUsedPercentDuringPoll=$warmReading.UsedPercent}
   if ($warmReading.FreePhysicalKiB -lt 204800 -or $warmReading.UsedPercent -ge 98.0) {$warmReceipt.MemoryPressureSeen=$true}
  }
 }
 $warmChild.Refresh()
 $warmReportPath=Join-Path $warmResult 'report.json'
 if (Test-Path -LiteralPath $warmReportPath) {
  $warmNative=Get-Content -LiteralPath $warmReportPath -Raw | ConvertFrom-Json
  $warmReceipt.NativeReportPassed=$true
  foreach ($warmFlag in @('native_component_verified','native_stages_completed','initial_factory_empty','private_authored_before_registration_exact','complete_final_contacts','source_files_input_Artist_exact','private_scene_disposed')) {if ($warmNative.$warmFlag -isnot [bool] -or $warmNative.$warmFlag -ne $true) {$warmReceipt.NativeReportPassed=$false}}
  foreach ($warmFlag in @('accepted','effect_accepted','ART_accepted','current_artist_verified','current_live_unsaved_verified','Unity_verified','export_accepted','public_Recalculate_supported','artist_saved','deployed','material_texture_verified','rendered','full_walk_run_squat_stop_final_surface_accepted','all_time_contact_verified','closed_Body_volume_verified','self_intersection_verified','Manual_fidelity_accepted')) {if ($warmNative.$warmFlag -isnot [bool] -or $warmNative.$warmFlag -ne $false) {$warmReceipt.NativeReportPassed=$false}}
  if (@($warmNative.errors).Count -or $warmNative.stage -ne 'PRIVATE_SAVED_DISK_NATIVE_WARM_START_V6_52' -or $warmNative.runtime.process_id -ne $warmChild.Id -or $warmNative.source_manifest_sha256 -ne $warmManifestSha -or $warmNative.paired_body_exact.exact -ne $true -or @($warmNative.seed_checks).Count -ne 2 -or $warmNative.input_native_preflight.completed -ne $true -or $warmNative.owned_native_input_preflight.completed -ne $true -or $warmNative.owned_native_input_preflight.inventory_complete -ne $true -or $warmNative.owned_native_input_preflight.user_map_complete -ne $true -or $warmNative.owned_native_input_preflight.all_actual_data_IDs_local -ne $true -or $warmNative.owned_scene_closure.input_sha256 -ne $warmInputSha -or @($warmNative.available_saved_scenes) -notcontains $warmScene) {$warmReceipt.NativeReportPassed=$false}
  if ($warmNative.Body_FK_transition.public_finished -isnot [bool] -or $warmNative.Body_FK_transition.public_finished -ne $true -or $warmNative.Body_FK_transition.all_four_FK -isnot [bool] -or $warmNative.Body_FK_transition.all_four_FK -ne $true -or $warmNative.Body_FK_transition.capture_AuthorRestoration.status -ne 'Measured' -or $warmNative.Body_FK_transition.rollback.completed -isnot [bool] -or $warmNative.Body_FK_transition.rollback.completed -ne $true -or $warmNative.Body_FK_transition.rollback.status -ne 'MeasuredRestored' -or @($warmNative.Body_FK_transition.before).Count -ne 4 -or @($warmNative.Body_FK_transition.after).Count -ne 4) {$warmReceipt.NativeReportPassed=$false}
  $warmReceipt.NativeSceneMembershipVerified=(@($warmNative.available_saved_scenes) -contains $warmScene -and $warmNative.owned_scene_closure.input_sha256 -eq $warmInputSha)
  $warmReceipt.NativeReportSha256=Get-WarmHash $warmReportPath
 }
} catch {
 $warmReceipt.NativeReportPassed=$false; $warmReceipt.Errors+=,$_.Exception.ToString()
} finally {
 # Only the held launched Process is owned. GUI/shared tasks are never stopped.
 if ($null -ne $warmChild) {
  try {if (-not $warmChild.HasExited) {$warmReceipt.ForcedTermination=$true; $warmChild.Kill(); if (-not $warmChild.WaitForExit(5000)) {throw 'Owned child did not exit within 5 seconds after finally Kill.'}}; $warmChild.Refresh(); $warmReceipt.ChildGone=$warmChild.HasExited; $warmReceipt.ExitCode=$warmChild.ExitCode} catch {$warmReceipt.ChildGone=$null; $warmReceipt.NativeReportPassed=$false; $warmReceipt.Errors+=,$_.Exception.ToString()}
 }
 try {
  $warmAfterText=& $warmPython -B -c $warmManifestCode
  if ($LASTEXITCODE -ne 0) {throw 'Final source/input read failed; no preservation success inferred.'}
  $warmAfterProof=($warmAfterText -join "`n") | ConvertFrom-Json
  $warmInputAfterMatches=(($warmProof.input | ConvertTo-Json -Depth 16 -Compress) -ceq ($warmAfterProof.input | ConvertTo-Json -Depth 16 -Compress))
  $warmReceipt.SourceAfter=$warmAfterProof.manifest; $warmReceipt.SourceAndInputAfterExact=($warmAfterProof.manifest_sha256 -eq $warmManifestSha -and $warmAfterProof.source_endpoint_pins_verified -eq $true -and $warmInputAfterMatches -and (Get-WarmHash $warmScript) -eq $warmScriptSha -and (Get-WarmHash $warmInputReceipt) -eq $warmInputReceiptSha -and (Get-WarmHash $warmInputMetadata) -eq $warmInputMetadataSha -and (Get-WarmHash $PSCommandPath) -eq $warmLauncherSha)
  if (-not $warmReceipt.SourceAndInputAfterExact) {throw 'Final protected source/input changed.'}
 } catch {$warmReceipt.SourceAndInputAfterExact=$null; $warmReceipt.NativeReportPassed=$false; $warmReceipt.Errors+=,$_.Exception.ToString()}
 if ($warmReceipt.TimedOut -or $warmReceipt.ForcedTermination -or $warmReceipt.ChildGone -ne $true -or $warmReceipt.ExitCode -ne 0 -or @($warmReceipt.Errors).Count) {$warmReceipt.NativeReportPassed=$false}
 $warmReceipt.Status='Terminal'; $warmReceipt.ElapsedSeconds=$warmWatch.Elapsed.TotalSeconds; $warmReceipt.MemorySamples=$warmSamples; $warmReceipt.PeakSampledWorkingSetBytes=$(if($warmSamples){$warmPeak}else{$null})
 Write-WarmReceipt (Join-Path $warmRun 'process.json') $warmReceipt
 Write-WarmReceipt (Join-Path $warmRun 'launch.json') $warmReceipt
 [ordered]@{PID=$warmReceipt.PID;ChildGone=$warmReceipt.ChildGone;ExitCode=$warmReceipt.ExitCode;NativeReportPassed=$warmReceipt.NativeReportPassed;ElapsedSeconds=$warmReceipt.ElapsedSeconds;PeakSampledWorkingSetBytes=$warmReceipt.PeakSampledWorkingSetBytes;MemorySamples=$warmReceipt.MemorySamples;AvailableKiBBefore=$warmMemoryBefore.FreePhysicalKiB;UsedPercentBefore=$warmMemoryBefore.UsedPercent;MemoryPressureSeen=$warmReceipt.MemoryPressureSeen;Run=$warmRun;Errors=$warmReceipt.Errors} | ConvertTo-Json -Depth 6 -Compress
 if ($null -ne $warmChild) {$warmChild.Dispose()}
}
if (Test-Path -LiteralPath $warmOut) {Get-Content -LiteralPath $warmOut -Tail 8}
if (Test-Path -LiteralPath $warmErr) {Get-Content -LiteralPath $warmErr -Tail 8}
if (-not $warmReceipt.NativeReportPassed) {exit 2}
