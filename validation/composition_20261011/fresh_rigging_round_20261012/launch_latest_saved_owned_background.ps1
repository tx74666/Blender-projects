param([Parameter(Mandatory=$true)][string]$ConfigFile)
$ErrorActionPreference = 'Stop'
$cfg = Get-Content -LiteralPath $ConfigFile -Raw | ConvertFrom-Json -DateKind String
$start = Get-Content -LiteralPath $cfg.resource_start -Raw | ConvertFrom-Json -DateKind String
if ([DateTimeOffset]::UtcNow -ge [DateTimeOffset]::Parse($start.expires_utc)) { throw 'Grant expired before launch' }
if ((Get-FileHash -LiteralPath $cfg.owner -Algorithm SHA256).Hash.ToLowerInvariant() -ne $cfg.owner_sha256) {throw 'Owner pin changed'}
$owner = Get-Content -LiteralPath $cfg.owner -Raw | ConvertFrom-Json -DateKind String
foreach ($rootPath in @($cfg.caller,$cfg.output,$cfg.profile)) {if (Test-Path -LiteralPath $rootPath) {throw ('Exclusive root exists: '+$rootPath)}}
$existingBlender = @(Get-Process -Name blender -ErrorAction SilentlyContinue)
if ($cfg.artist_pid) {
    if ($existingBlender.Count -ne 1 -or $existingBlender[0].Id -ne $cfg.artist_pid -or $existingBlender[0].StartTime.ToUniversalTime().ToFileTimeUtc().ToString() -ne $cfg.artist_filetime) {throw 'Current artist process changed'}
} elseif ($existingBlender.Count -ne 0) {throw 'Unexpected Blender process before owned inspection'}
if ((Get-FileHash -LiteralPath $cfg.artist_path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $cfg.artist_sha256) {throw 'Latest saved artist changed before launch'}
$exePath = $owner.cli_argv[0]
if ((Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $cfg.exe_sha256) {throw 'Blender executable changed'}
$ram = Get-CimInstance Win32_OperatingSystem
$freeMiB = [math]::Round($ram.FreePhysicalMemory/1024,1)
if ($freeMiB -lt 200) {throw 'Fresh RAM below 200 MiB'}
$argQuoted = foreach ($part in @($owner.cli_argv | Select-Object -Skip 1)) {if ($part.Contains('"') -or $part.Contains([char]10) -or $part.EndsWith('\')) {throw 'Argument requires unsupported escaping'}; '"'+$part+'"'}
New-Item -ItemType Directory -Path $cfg.caller | Out-Null
New-Item -ItemType Directory -Path $cfg.output | Out-Null
New-Item -ItemType Directory -Path (Join-Path $cfg.profile 'CONFIG') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $cfg.profile 'DATAFILES') | Out-Null
if ((Get-ChildItem -LiteralPath $cfg.output -Force).Count -ne 0) {throw 'Output is not empty'}
foreach ($profileChild in @('CONFIG','DATAFILES')) {if ((Get-ChildItem -LiteralPath (Join-Path $cfg.profile $profileChild) -Force).Count -ne 0) {throw 'Profile is not empty'}}
$env:BLENDER_USER_CONFIG=$owner.cli_environment.BLENDER_USER_CONFIG
$env:BLENDER_USER_DATAFILES=$owner.cli_environment.BLENDER_USER_DATAFILES
$env:PYTHONDONTWRITEBYTECODE='1'
$child = Start-Process -FilePath $exePath -ArgumentList ($argQuoted -join ' ') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $cfg.caller 'stdout.log') -RedirectStandardError (Join-Path $cfg.caller 'stderr.log')
$retainedHandle=$child.Handle
$launch=[ordered]@{resource_token=$cfg.token;actual_started_utc=[DateTimeOffset]::UtcNow.ToString('o');owned_pid=$child.Id;owned_process_filetime=$child.StartTime.ToUniversalTime().ToFileTimeUtc().ToString();retained_handle_acquired=($retainedHandle -ne 0);background=$true;GUI=$false;fresh_memory_MiB=$freeMiB;artist_process_pid=$cfg.artist_pid;artist_process_filetime=$cfg.artist_filetime;protected_artist_sha256=$cfg.artist_sha256}
$launch | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $cfg.caller 'launch_observation.json') -Encoding utf8NoBOM
$launch | ConvertTo-Json -Compress | Write-Output
$remainingMs=[Math]::Max(1,[int]([DateTimeOffset]::Parse($start.expires_utc)-[DateTimeOffset]::UtcNow).TotalMilliseconds)
if (-not $child.WaitForExit($remainingMs)) {Write-Output ('TIMEOUT owned process retained: '+$child.Id); throw 'Native child reached hard deadline; no automatic retry or silent completion'}
$child.WaitForExit()
$end=[ordered]@{resource_token=$cfg.token;owned_pid=$launch.owned_pid;owned_process_filetime=$launch.owned_process_filetime;retained_handle_natural_exit=$true;native_exit_code=$child.ExitCode;native_exited_utc=[DateTimeOffset]::UtcNow.ToString('o');owned_native_gone=$true;process_termination_performed=$false;GUI=$false}
$end | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $cfg.caller 'native_end_observation.json') -Encoding utf8NoBOM
$end | ConvertTo-Json -Compress | Write-Output
$child.Dispose()
