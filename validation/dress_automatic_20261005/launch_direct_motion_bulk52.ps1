param([ValidateSet('walk','run','abrupt_stop_turn')][string]$DressCase='run')
$ErrorActionPreference='Stop'
$dressMemory=Get-CimInstance Win32_OperatingSystem
if ($dressMemory.FreePhysicalMemory -lt 204800) { throw 'Insufficient current memory' }
if (@(Get-CimInstance Win32_Process -Filter "Name = 'blender.exe'" | Where-Object {$_.CommandLine -match '--background'}).Count) { throw 'Another background Blender is running' }
$dressRoot='D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005'
$dressScript=Join-Path $dressRoot 'verify_direct_cold_motion_bulk52.py'
if ((Get-FileHash -LiteralPath $dressScript).Hash.ToLowerInvariant() -ne 'dc300331042650ba46a25ea5e807ffe232ba7d559951616eec7477c1a44ac76f') { throw 'Frozen script changed' }
$dressRun=Join-Path $dressRoot ('actual_direct_motion_bulk_'+$DressCase+'_e0b_52_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')+'_'+([guid]::NewGuid().ToString('N')))
$dressTemp=Join-Path $dressRun 'native_temp'
New-Item -ItemType Directory -Path $dressTemp | Out-Null
$dressOut=Join-Path $dressRun 'native.stdout.log'
$dressErr=Join-Path $dressRun 'native.stderr.log'
$dressArgs=@('--background','--factory-startup','--disable-autoexec','--threads','1','--python-exit-code','2','--python',('"'+$dressScript+'"'),'--','--expected-direct-sha','eb1ad005da9c98082b577c4dca4ab32a111ec684fa2ba27e3612b0c396205e99','--cold-report','D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005\actual_direct_cold_e0b_bake_guards_52_20261007_062634_189\report.json','--cold-report-sha','0a016dc10d5cf706cbd529449a330d630d7e87459189b3f2cd068557a050d959','--output',('"'+(Join-Path $dressRun 'result')+'"'),'--artist-protection','D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005\artist_disk_protection_20261007_e0b30f73fc2f.json','--artist-protection-sha','4d092929664f9718241afabc1ba3a3c667b600eeeb3d8a98fac0aea322ff536f','--body-object','Cosha','--dress-object','Dress','--case',$DressCase,'--soft-seconds','150')
$dressChild=Start-Process -FilePath 'D:\Blender5.2\blender.exe' -ArgumentList $dressArgs -WindowStyle Hidden -Environment @{TEMP=$dressTemp;TMP=$dressTemp} -RedirectStandardOutput $dressOut -RedirectStandardError $dressErr -PassThru
Write-Output ('OWNED_QA_CHILD_PID='+$dressChild.Id)
Write-Output ('RUN='+$dressRun)
$dressWatch=[Diagnostics.Stopwatch]::StartNew(); $dressPeak=0L; $dressTimedOut=$false
while (-not $dressChild.WaitForExit(1000)) {
 $dressChild.Refresh(); $dressPeak=[Math]::Max($dressPeak,$dressChild.PeakWorkingSet64)
 if ($dressWatch.Elapsed.TotalSeconds -gt 210) { $dressChild.Kill(); $dressChild.WaitForExit(); $dressTimedOut=$true; break }
}
$dressChild.Refresh()
$dressReceipt=@{Stage='actual_direct_motion_bulk_e0b';Case=$DressCase;PID=$dressChild.Id;ExitCode=$dressChild.ExitCode;TimedOut=$dressTimedOut;ElapsedSeconds=$dressWatch.Elapsed.TotalSeconds;PeakWorkingSetBytes=$dressPeak;AvailableKiBBefore=$dressMemory.FreePhysicalMemory;FreeCommitKiBBefore=$dressMemory.FreeVirtualMemory;ScriptSha256=(Get-FileHash -LiteralPath $dressScript).Hash.ToLowerInvariant();Run=$dressRun;ChildGone=(-not (Get-Process -Id $dressChild.Id -ErrorAction SilentlyContinue))}
$dressReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dressRun 'process.json') -Encoding utf8
$dressReceipt | ConvertTo-Json -Compress
Get-Content -LiteralPath $dressOut -Tail 8
Get-Content -LiteralPath $dressErr -Tail 10
if ($dressTimedOut -or $dressChild.ExitCode -ne 0) { exit 2 }
