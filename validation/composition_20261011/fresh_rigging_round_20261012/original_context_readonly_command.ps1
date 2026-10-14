param([Parameter(Mandatory=$true)][string]$ResourceStart,
      [Parameter(Mandatory=$true)][string]$ResourceStartSha256,
      [Parameter(Mandatory=$true)][string]$ExpectedToken)
$ErrorActionPreference='Stop'
$taskRound='D:\Blender\Projects\Character\X\validation\composition_20261011\fresh_rigging_round_20261012'
if((Get-FileHash -LiteralPath $ResourceStart).Hash.ToLowerInvariant() -cne $ResourceStartSha256){throw 'Grant changed'}
$taskGrant=Get-Content -LiteralPath $ResourceStart -Raw|ConvertFrom-Json -DateKind String
if($taskGrant.schema -cne 'x.validation.fresh-native-resource-start/1' -or
   $taskGrant.scope -cne 'latest-original-context-readonly' -or $taskGrant.owner -cne 'Root' -or
   $taskGrant.status -cne 'ACTUAL_START' -or $taskGrant.token -cne $ExpectedToken -or
   $taskGrant.owner_thread -cne '01a12751-d08f-7630-b790-18db26fe3186' -or
   $taskGrant.parent_thread -cne '01a12305-aada-7273-b72c-54a41aad77e4' -or
   $taskGrant.sdk_allowed -isnot [bool] -or $taskGrant.sdk_allowed -ne $true){throw 'Grant identity invalid'}
foreach($taskFlag in @('worker_allowed','gui_allowed','new_blender_allowed','Unity_allowed','live_source_writes_allowed','artist_original_save_allowed','install_allowed','deployment_allowed')){
 if($taskGrant.$taskFlag -isnot [bool] -or $taskGrant.$taskFlag -ne $false){throw ('Forbidden flag '+$taskFlag)}
}
foreach($taskTime in @($taskGrant.created_utc,$taskGrant.actual_start_utc,$taskGrant.deadline_utc)){
 if($taskTime -isnot [string] -or $taskTime -cnotmatch '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'){throw 'Explicit UTC required'}
}
$taskNow=[DateTimeOffset]::UtcNow
$taskCreated=[DateTimeOffset]::Parse($taskGrant.actual_start_utc)
$taskDeadline=[DateTimeOffset]::Parse($taskGrant.deadline_utc)
if($taskGrant.actual_start_utc -cne $taskGrant.created_utc -or $taskCreated -gt $taskNow -or $taskNow -ge $taskDeadline -or ($taskDeadline-$taskCreated).TotalSeconds -gt 180){throw 'Expired window'}
$taskSource=Join-Path $taskRound 'read_original_context_identity.py'
if((Get-FileHash -LiteralPath $taskSource).Hash.ToLowerInvariant() -cne '3a9f4952d1834a3aefbee4581929b6dd0ac7e4b21a8f0a7ec210014b11e30f6d'){throw 'Source changed'}
$taskOutput=[IO.Path]::GetFullPath($taskGrant.output_path)
if(-not $taskOutput.StartsWith($taskRound+'\',[StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $taskOutput)){throw 'Fresh owned output required'}
$taskEvidence=$taskOutput+'.sdk_response.json'
$taskProc=Get-Process -Id 27676 -ErrorAction Stop
$taskHandle=$taskProc.Handle
try{
 if($taskProc.HasExited -or $taskProc.StartTime.ToFileTimeUtc() -ne [Int64]134359355330496074 -or $taskProc.MainModule.FileName -cne 'D:\Blender5.2\blender.exe'){throw 'Original identity mismatch'}
 if((Get-FileHash -LiteralPath 'D:\Blender\Projects\Character\X\X.blend').Hash.ToLowerInvariant() -cne '3cd5619d70e8b4e21c2483884a04d352a2405f0eab02f00d34d306c81c5aa4b0'){throw 'Original disk changed'}
 $taskPorts=@(Get-NetTCPConnection -State Listen -OwningProcess 27676|Where-Object {$_.LocalAddress -eq '127.0.0.1'})
 if($taskPorts.Count -ne 1){throw 'Endpoint ambiguous'}
 $taskOS=Get-CimInstance Win32_OperatingSystem
 if(100*(1-$taskOS.FreePhysicalMemory/$taskOS.TotalVisibleMemorySize) -ge 98){$taskOS=Get-CimInstance Win32_OperatingSystem}
 if($taskOS.FreePhysicalMemory/1024 -lt 200){throw 'Memory insufficient'}
 if(($taskDeadline-[DateTimeOffset]::UtcNow).TotalSeconds -lt 50){throw 'Insufficient remaining window for bounded single request'}
 $taskCode=@'
import hashlib,json,socket,sys,time
from pathlib import Path
source=Path(sys.argv[1]);output=Path(sys.argv[2]);evidence=Path(sys.argv[3]);port=int(sys.argv[4]);raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='3a9f4952d1834a3aefbee4581929b6dd0ac7e4b21a8f0a7ec210014b11e30f6d'
code='_x_read_ns={"__name__":"__original_context_readonly__"}\nexec(compile('+repr(raw.decode('utf-8-sig'))+','+repr(str(source))+',"exec"),_x_read_ns)\n_x_read_ns["run"]('+repr(str(output))+')\n'
request=json.dumps(dict(type='execute_code',params=dict(code=code)),ensure_ascii=False).encode('utf-8');started=time.monotonic();response=None
with socket.create_connection(('127.0.0.1',port),timeout=5) as connection:
 connection.settimeout(1)
 with Path(str(output)+'.request_attempted.json').open('x',encoding='utf-8') as stream:json.dump({'SDK_requests':1,'source_sha256':hashlib.sha256(raw).hexdigest(),'port':port},stream)
 connection.sendall(request);payload=b''
 while response is None:
  if time.monotonic()-started>45:raise RuntimeError('UNKNOWN outcome; no retry')
  try:part=connection.recv(65536)
  except socket.timeout:continue
  if not part:raise RuntimeError('UNKNOWN closed response; no retry')
  payload+=part
  if len(payload)>1024*1024:raise RuntimeError('UNKNOWN oversized response; no retry')
  try:response=json.loads(payload.decode('utf-8'))
  except (json.JSONDecodeError,UnicodeDecodeError):continue
with evidence.open('x',encoding='utf-8') as stream:json.dump(response,stream,ensure_ascii=False,indent=2)
report=json.loads(output.read_bytes()) if output.exists() else {}
print(json.dumps({'actual_end_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'SDK_status':response.get('status'),'report':report},ensure_ascii=True))
sys.exit(0 if report.get('completed') is True and report.get('current_context_unchanged') is True and response.get('status')!='error' else 1)
'@
 & 'C:\Users\Randy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -c $taskCode $taskSource $taskOutput $taskEvidence ([string]$taskPorts[0].LocalPort)
 $taskExit=$LASTEXITCODE
 if($taskProc.HasExited -or $taskProc.StartTime.ToFileTimeUtc() -ne [Int64]134359355330496074){throw 'Original identity lost'}
 [pscustomobject]@{actual_caller_end_utc=[DateTime]::UtcNow.ToString('o');caller_exit=$taskExit;original_retained_live=$true;original_disk_sha256=(Get-FileHash -LiteralPath 'D:\Blender\Projects\Character\X\X.blend').Hash.ToLowerInvariant();output_path=$taskOutput;scope=$taskGrant.scope}|ConvertTo-Json -Compress
 exit $taskExit
}finally{$taskProc.Dispose()}
