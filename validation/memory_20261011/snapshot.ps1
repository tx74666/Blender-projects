param([Parameter(Mandatory=$true)][string]$OutputName)
$taskDirectory = $PSScriptRoot
$outputFile = [IO.Path]::GetFullPath((Join-Path $taskDirectory $OutputName))
if ([IO.Path]::GetDirectoryName($outputFile) -ne $taskDirectory) { throw 'Output must stay in this task directory' }
$operatingState = Get-CimInstance Win32_OperatingSystem
$cimProcesses = @(Get-CimInstance Win32_Process)
$nativeProcesses = @{}
Get-Process | ForEach-Object { $nativeProcesses[$_.Id] = $_ }
$processMap = @{}
foreach ($item in $cimProcesses) { $processMap[[int]$item.ProcessId] = $item }
$records = foreach ($item in $cimProcesses) {
    $native = $nativeProcesses[[int]$item.ProcessId]
    $parent = $processMap[[int]$item.ParentProcessId]
    $parentValid = $null -ne $parent -and $parent.CreationDate -le $item.CreationDate
    $chain = [Collections.Generic.List[int]]::new()
    $cursor = $item
    while ($cursor -and $chain.Count -lt 20 -and -not $chain.Contains([int]$cursor.ProcessId)) {
        $chain.Add([int]$cursor.ProcessId)
        $ancestor = $processMap[[int]$cursor.ParentProcessId]
        if (-not $ancestor -or $ancestor.CreationDate -gt $cursor.CreationDate) { break }
        $cursor = $ancestor
    }
    [pscustomobject]@{
        pid = [int]$item.ProcessId; parent_pid = [int]$item.ParentProcessId; name = $item.Name
        created = $item.CreationDate; parent_valid = $parentValid; parent_name = if ($parentValid) { $parent.Name } else { $null }
        ancestor_pids = @($chain.ToArray()); executable = $item.ExecutablePath
        working_set_mb = if ($native) { [math]::Round($native.WorkingSet64/1MB,2) } else { $null }
        private_mb = if ($native) { [math]::Round($native.PrivateMemorySize64/1MB,2) } else { $null }
        cpu_seconds = if ($native) { $native.CPU } else { $null }
        handle_count = if ($native) { $native.HandleCount } else { $null }
        kind = if ($item.Name -eq 'blender.exe') { if ($item.CommandLine -match '--background') { 'blender-background' } else { 'blender-artist' } }
               elseif ($item.CommandLine -match 'mcp-for-unity') { 'unity-mcp' }
               elseif ($item.CommandLine -match 'server.mjs') { 'cua-server' }
               elseif ($item.CommandLine -match 'cua-repl.mjs') { 'cua-repl' }
               elseif ($item.CommandLine -match 'app-server') { 'codex-app-server' }
               elseif ($item.CommandLine -match '--type=renderer') { 'app-renderer' }
               else { $item.Name }
    }
}
$snapshot = [pscustomobject]@{
    schema = 'x.memory.windows-processes/1'; captured = [DateTimeOffset]::Now.ToString('o')
    total_mb = [math]::Round($operatingState.TotalVisibleMemorySize/1024,2)
    available_mb = [math]::Round($operatingState.FreePhysicalMemory/1024,2)
    used_percent = [math]::Round(100*(1-$operatingState.FreePhysicalMemory/$operatingState.TotalVisibleMemorySize),2)
    processes = @($records)
}
$snapshot | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $outputFile -Encoding utf8
$summary = [pscustomobject]@{
    captured = $snapshot.captured; available_mb = $snapshot.available_mb; used_percent = $snapshot.used_percent
    orphan_helpers = @($records | Where-Object { -not $_.parent_valid -and $_.name -match '^(node|python|uvx|uv|node_repl|cmd|powershell|pwsh|codex)\.exe$' })
    family_totals = @($records | Where-Object { $_.kind -match 'mcp|cua|codex|blender|renderer' } | Group-Object kind | ForEach-Object {
        [pscustomobject]@{kind=$_.Name; count=$_.Count; working_set_mb=[math]::Round(($_.Group | Measure-Object working_set_mb -Sum).Sum,2);private_mb=[math]::Round(($_.Group | Measure-Object private_mb -Sum).Sum,2)}
    })
}
$summary | ConvertTo-Json -Depth 5 -Compress
