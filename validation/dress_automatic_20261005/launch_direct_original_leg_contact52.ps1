
$ErrorActionPreference='Stop'
$dressMemory=Get-CimInstance Win32_OperatingSystem
if ($dressMemory.FreePhysicalMemory -lt 204800) { throw 'Insufficient current memory' }
if (@(Get-CimInstance Win32_Process -Filter "Name = 'blender.exe'" | Where-Object {$_.CommandLine -match '--background'}).Count) { throw 'Another background Blender is running' }
$dressRoot='D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005'
$dressScript=Join-Path $dressRoot 'verify_direct_original_leg_contact52.py'
if ((Get-FileHash -LiteralPath $dressScript).Hash.ToLowerInvariant() -ne 'e1063eb9dab5e943661136c5f3504ada31a7cb056b6916b6d9aef40c723fd8c9') { throw 'Frozen script changed' }
$dressRun=Join-Path $dressRoot ('actual_direct_original_leg_contact_e0b_52_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')+'_'+([guid]::NewGuid().ToString('N')))
$dressTemp=Join-Path $dressRun 'native_temp'
New-Item -ItemType Directory -Path $dressTemp | Out-Null
$dressOut=Join-Path $dressRun 'native.stdout.log'
$dressErr=Join-Path $dressRun 'native.stderr.log'
$dressArgs=@('--background','--factory-startup','--disable-autoexec','--threads','1','--python-exit-code','2','--python',('"'+$dressScript+'"'),'--','--expected-source-manifest-sha','178f0c9c2a43bedf3e9b1c10b06fbac64d4ddbf60be307450011f40b8916e690','--output',('"'+(Join-Path $dressRun 'result')+'"'),'--artist-protection','D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005\artist_disk_protection_20261007_e0b30f73fc2f.json','--artist-protection-sha','4d092929664f9718241afabc1ba3a3c667b600eeeb3d8a98fac0aea322ff536f','--body-object','Cosha','--dress-object','Dress','--soft-seconds','180')
$dressChild=Start-Process -FilePath 'D:\Blender5.2\blender.exe' -ArgumentList $dressArgs -WindowStyle Hidden -Environment @{TEMP=$dressTemp;TMP=$dressTemp} -RedirectStandardOutput $dressOut -RedirectStandardError $dressErr -PassThru
Write-Output ('OWNED_QA_CHILD_PID='+$dressChild.Id)
Write-Output ('RUN='+$dressRun)
$dressWatch=[Diagnostics.Stopwatch]::StartNew(); $dressPeak=0L; $dressTimedOut=$false
while (-not $dressChild.WaitForExit(1000)) {
 $dressChild.Refresh(); $dressPeak=[Math]::Max($dressPeak,$dressChild.PeakWorkingSet64)
 if ($dressWatch.Elapsed.TotalSeconds -gt 240) { $dressChild.Kill(); $dressChild.WaitForExit(); $dressTimedOut=$true; break }
}
$dressChild.Refresh()
$dressReceipt=@{Stage='actual_direct_original_leg_contact_e0b';Case='model_only';PID=$dressChild.Id;ExitCode=$dressChild.ExitCode;TimedOut=$dressTimedOut;ElapsedSeconds=$dressWatch.Elapsed.TotalSeconds;PeakWorkingSetBytes=$dressPeak;AvailableKiBBefore=$dressMemory.FreePhysicalMemory;FreeCommitKiBBefore=$dressMemory.FreeVirtualMemory;ScriptSha256=(Get-FileHash -LiteralPath $dressScript).Hash.ToLowerInvariant();Run=$dressRun;ChildGone=(-not (Get-Process -Id $dressChild.Id -ErrorAction SilentlyContinue))}
$dressReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dressRun 'process.json') -Encoding utf8
$dressReceipt | ConvertTo-Json -Compress
Get-Content -LiteralPath $dressOut -Tail 8
Get-Content -LiteralPath $dressErr -Tail 10
if ($dressTimedOut -or $dressChild.ExitCode -ne 0) { exit 2 }
