param(
    [Parameter(Mandatory=$true)][string]$ResourceStart,
    [Parameter(Mandatory=$true)][string]$ResourceStartSha256,
    [Parameter(Mandatory=$true)][string]$OutputRoot,
    [Parameter(Mandatory=$true)][string]$EvidenceRoot
)
$ErrorActionPreference = 'Stop'
$taskScopeRoot = [IO.Path]::GetFullPath('D:\Blender\Projects\Character\X\validation\composition_20261011\fresh_rigging_round_20261012')
$taskOutput = [IO.Path]::GetFullPath($OutputRoot)
$taskEvidence = [IO.Path]::GetFullPath($EvidenceRoot)
foreach ($taskPath in @($taskOutput,$taskEvidence)) {
    if (-not $taskPath.StartsWith($taskScopeRoot + '\',[StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $taskPath)) { throw 'Use unique, absent, separate persistent ROUND child directories.' }
}
if ($taskOutput -eq $taskEvidence -or $taskOutput.StartsWith($taskEvidence + '\',[StringComparison]::OrdinalIgnoreCase) -or $taskEvidence.StartsWith($taskOutput + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Snapshot and caller evidence must be disjoint.' }
if ((Get-FileHash -LiteralPath $ResourceStart -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ResourceStartSha256) { throw 'Resource START pin changed.' }
$taskStart = Get-Content -LiteralPath $ResourceStart -Raw | ConvertFrom-Json
if ($taskStart.status -ne 'ACTUAL_START' -or $taskStart.scope -ne 'latest-original-artist-savecopy' -or $taskStart.owner_thread -ne '01a12751-d08f-7630-b790-18db26fe3186' -or $taskStart.parent_thread -ne '01a12305-aada-7273-b72c-54a41aad77e4' -or $taskStart.worker_allowed -ne $false) { throw 'Use the fresh explicit original SaveCopy scope, with no worker.' }
$taskStartTime = if ($taskStart.actual_start_utc -is [DateTime]) { [DateTimeOffset]::new($taskStart.actual_start_utc.ToUniversalTime()) } else { [DateTimeOffset]::Parse([string]$taskStart.actual_start_utc) }
$taskAge = ([DateTimeOffset]::UtcNow - $taskStartTime).TotalSeconds
if ($taskAge -lt 0 -or $taskAge -gt 900) { throw 'The resource START is stale or future dated.' }
$taskScriptPath = Join-Path $taskScopeRoot 'snapshot_latest_original_artist.py'
if ((Get-FileHash -LiteralPath $taskScriptPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne '6df88f6e605a2a4e96eb1d3f261ed456dbe150c3e54a0d1e68f0f5aa962ff971') { throw 'Snapshot Source changed.' }
$taskArtistPath = 'D:\Blender\Projects\Character\X\X.blend'
if ((Get-FileHash -LiteralPath $taskArtistPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne '3cd5619d70e8b4e21c2483884a04d352a2405f0eab02f00d34d306c81c5aa4b0') { throw 'Protected artist disk changed.' }
$taskArtistProc = Get-Process -Id 27676 -ErrorAction Stop
$taskRetainedHandle = $taskArtistProc.Handle
try {
    if ($taskArtistProc.HasExited -or $taskArtistProc.StartTime.ToFileTimeUtc() -ne [Int64]134359355330496074 -or $taskArtistProc.MainModule.FileName -ne 'D:\Blender5.2\blender.exe') { throw 'The original retained process identity changed.' }
    $taskListeners = @(Get-NetTCPConnection -State Listen -OwningProcess $taskArtistProc.Id | Where-Object { $_.LocalAddress -eq '127.0.0.1' })
    if ($taskListeners.Count -ne 1) { throw 'The original SDK loopback endpoint is missing or ambiguous; none was guessed.' }
    $taskMem = Get-CimInstance Win32_OperatingSystem
    if (100*(1-$taskMem.FreePhysicalMemory/$taskMem.TotalVisibleMemorySize) -ge 98) { $taskMem = Get-CimInstance Win32_OperatingSystem }
    if ($taskMem.FreePhysicalMemory/1024 -lt 200) { throw 'Fresh available memory is below 200 MiB.' }
    $taskClaimDir = Join-Path $taskScopeRoot 'launch_claims'
    New-Item -ItemType Directory -Path $taskClaimDir -Force | Out-Null
    $taskClaimPath = Join-Path $taskClaimDir ($ResourceStartSha256 + '.original_snapshot.claim')
    $taskClaimStream = [IO.File]::Open($taskClaimPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $taskClaimStream.Dispose()
    New-Item -ItemType Directory -Path $taskOutput | Out-Null
    New-Item -ItemType Directory -Path $taskEvidence | Out-Null
    $taskBefore = [ordered]@{schema='x.validation.original-sdk-snapshot-caller/1';completed=$false;started_utc=(Get-Date).ToUniversalTime().ToString('o');resource_start=$ResourceStart;resource_start_sha256=$ResourceStartSha256;original_pid=$taskArtistProc.Id;creation_filetime=$taskArtistProc.StartTime.ToFileTimeUtc();title=$taskArtistProc.MainWindowTitle;endpoint=@{address=$taskListeners[0].LocalAddress;port=$taskListeners[0].LocalPort;owning_process=$taskListeners[0].OwningProcess};free_MiB=[math]::Round($taskMem.FreePhysicalMemory/1024,1);SDK_requests=0;worker_calls=0;new_Blender_calls=0;artist_disk_writes=0;process_termination_performed=$false}
    $taskBefore | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $taskEvidence 'caller_before.json') -Encoding utf8
    $taskCode = @'
import hashlib,json,socket,sys,time
from pathlib import Path
source=Path(sys.argv[1]); output=Path(sys.argv[2]); evidence=Path(sys.argv[3]); port=int(sys.argv[4])
raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='6df88f6e605a2a4e96eb1d3f261ed456dbe150c3e54a0d1e68f0f5aa962ff971'
params=dict(expected_pid=27676,external_process_filetime=134359355330496074,script_sha256=hashlib.sha256(raw).hexdigest(),output_root=str(output),oracle_sha256='260b2bc581df220ea861d18f6b369d104561d5a3d119e21e5e52e9e230219a5d',runtime_manifest_sha256='c72a4b8a8b0988138f40542b1a3bb0b8313e9aaac7e4ab4bd3baa1f21c05c92b')
code='_x_snapshot_ns={"__name__":"__vetted_original_snapshot__"}\nexec(compile('+repr(raw.decode('utf-8-sig'))+','+repr(str(source))+',"exec"),_x_snapshot_ns)\n_x_snapshot_ns["run"](**'+repr(params)+')\n'
request=json.dumps(dict(type='execute_code',params=dict(code=code)),ensure_ascii=False).encode('utf-8')
started=time.monotonic(); response=None
with socket.create_connection(('127.0.0.1',port),timeout=5) as connection:
    connection.settimeout(1)
    (evidence/'request_attempted.json').write_text(json.dumps({'SDK_requests':1,'source_sha256':hashlib.sha256(raw).hexdigest(),'port':port,'outcome':'UNKNOWN_UNTIL_RESPONSE'}),encoding='utf-8')
    connection.sendall(request)
    payload=b''
    while response is None:
        if time.monotonic()-started>180: raise RuntimeError('UNKNOWN SDK outcome; preserve files and inspect actual state before any retry.')
        try: part=connection.recv(65536)
        except socket.timeout: continue
        if not part: raise RuntimeError('UNKNOWN SDK outcome: connection closed before complete response; do not retry.')
        payload+=part
        if len(payload)>8*1024*1024: raise RuntimeError('UNKNOWN oversized SDK response; do not retry.')
        try: response=json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError,UnicodeDecodeError): continue
(evidence/'sdk_response.json').write_text(json.dumps(response,ensure_ascii=False,indent=2),encoding='utf-8')
receipt=output/'artist_latest_snapshot_receipt.json'
result=json.loads(receipt.read_text(encoding='utf-8')) if receipt.is_file() else {}
print(json.dumps({'completed':result.get('completed',False),'backup_verified':result.get('backup_verified',False),'receipt':str(receipt),'SDK_status':response.get('status'),'error':result.get('error')},ensure_ascii=True))
sys.exit(0 if result.get('completed') is True and result.get('backup_verified') is True and response.get('status')!='error' else 1)
'@
    & 'C:\Users\Randy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -c $taskCode $taskScriptPath $taskOutput $taskEvidence ([string]$taskListeners[0].LocalPort)
    $taskSdkExit = $LASTEXITCODE
    if ($taskArtistProc.HasExited -or $taskArtistProc.StartTime.ToFileTimeUtc() -ne [Int64]134359355330496074) { throw 'The retained original process exited or changed during snapshot.' }
    if ((Get-FileHash -LiteralPath $taskArtistPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne '3cd5619d70e8b4e21c2483884a04d352a2405f0eab02f00d34d306c81c5aa4b0') { throw 'Protected artist disk changed during snapshot.' }
    $taskBefore.completed = ($taskSdkExit -eq 0)
    $taskBefore.SDK_requests = [int](Test-Path -LiteralPath (Join-Path $taskEvidence 'request_attempted.json'))
    $taskBefore['python_exit_code'] = $taskSdkExit
    $taskBefore['original_retained_handle_still_live'] = -not $taskArtistProc.HasExited
    $taskBefore['original_disk_unchanged'] = $true
    $taskBefore['finished_utc'] = (Get-Date).ToUniversalTime().ToString('o')
    $taskBefore | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $taskEvidence 'caller_after.json') -Encoding utf8
    exit $taskSdkExit
}
finally {
    $taskArtistProc.Dispose() # Release only this read-only OS handle, never the app.
}
