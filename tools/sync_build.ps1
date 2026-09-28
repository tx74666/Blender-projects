param([string]$ManifestPath = (Join-Path $PSScriptRoot 'build_sources.json'))

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repoRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$repoPrefix = $repoRoot.TrimEnd('\') + '\'
$packageRoot = Join-Path $repoRoot '.codex-package'

function Assert-RepositoryPath([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Destination is outside the repository: $Path"
    }
    $probe = $full
    while ($probe.Length -ge $repoRoot.Length) {
        if (Test-Path -LiteralPath $probe) {
            $item = Get-Item -LiteralPath $probe -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Refusing a destination through a link or junction: $probe"
            }
        }
        $probe = Split-Path -Parent $probe
    }
    return $full
}

function Resolve-Destination([string]$RelativePath, [bool]$IsScene) {
    if ([string]::IsNullOrWhiteSpace($RelativePath) -or [IO.Path]::IsPathRooted($RelativePath)) {
        throw "Destination must be a repository-relative path: $RelativePath"
    }
    $full = Assert-RepositoryPath (Join-Path $repoRoot $RelativePath)
    $relative = $full.Substring($repoPrefix.Length)
    if ($IsScene) {
        if ($relative -ine 'Build.blend') { throw 'The scene destination must be Build.blend.' }
    } elseif (-not $relative.StartsWith('textures\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Build dependencies must stay under textures/: $RelativePath"
    }
    if (Test-Path -LiteralPath $full -PathType Container) { throw "Destination is a directory: $full" }
    return $full
}

function Get-SourceStamp([string]$Path) {
    $file = Get-Item -LiteralPath $Path
    if ($file.PSIsContainer) { throw "Expected a source file: $Path" }
    $length = $file.Length
    $ticks = $file.LastWriteTimeUtc.Ticks
    $hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    $after = Get-Item -LiteralPath $Path
    if ($length -ne $after.Length -or $ticks -ne $after.LastWriteTimeUtc.Ticks) {
        throw "Source changed while being read; save it and run sync again: $Path"
    }
    return [pscustomobject]@{ Length = $length; Ticks = $ticks; SHA256 = $hash }
}

function Assert-StableSources($Records) {
    foreach ($record in $Records) {
        $now = Get-SourceStamp $record.Source
        if ($now.Length -ne $record.Stamp.Length -or $now.Ticks -ne $record.Stamp.Ticks -or
            $now.SHA256 -ne $record.Stamp.SHA256) {
            throw "Source changed during sync; Build.blend was not published: $($record.Source)"
        }
    }
}

function Publish-StagedFile([string]$Staged, [string]$Destination) {
    $null = Assert-RepositoryPath $Destination
    $null = [IO.Directory]::CreateDirectory((Split-Path -Parent $Destination))
    if ([IO.File]::Exists($Destination)) {
        [IO.File]::Replace($Staged, $Destination, [NullString]::Value)
    } else {
        [IO.File]::Move($Staged, $Destination)
    }
}

$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$sceneSource = [string]$manifest.sourceScene
if (-not [IO.Path]::IsPathRooted($sceneSource)) { $sceneSource = Join-Path $repoRoot $sceneSource }
$sceneSource = [IO.Path]::GetFullPath($sceneSource)
$inputs = @()
foreach ($dependency in @($manifest.dependencies)) {
    if (-not [IO.Path]::IsPathRooted([string]$dependency.source)) {
        throw "Dependency source must be absolute: $($dependency.source)"
    }
    $inputs += [pscustomobject]@{
        Source = [IO.Path]::GetFullPath([string]$dependency.source)
        Destination = Resolve-Destination ([string]$dependency.destination) $false
        IsScene = $false
    }
}
$inputs += [pscustomobject]@{
    Source = $sceneSource
    Destination = Resolve-Destination ([string]$manifest.sceneDestination) $true
    IsScene = $true
}
$seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
foreach ($inputFile in $inputs) {
    if (-not $seen.Add($inputFile.Destination)) { throw "Duplicate destination: $($inputFile.Destination)" }
    if ($inputFile.Source -ieq $inputFile.Destination) { throw 'Source and destination must be different files.' }
}

$null = Assert-RepositoryPath $packageRoot
$null = [IO.Directory]::CreateDirectory($packageRoot)
$stageRoot = Join-Path $packageRoot ('build-sync-' + [Guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($stageRoot)
$records = @()
try {
    # The manifest contains approved Build-owned destinations; never scan or copy entire folders.
    foreach ($inputFile in $inputs) {
        $records += [pscustomobject]@{
            Source = $inputFile.Source; Destination = $inputFile.Destination
            IsScene = $inputFile.IsScene; Stamp = Get-SourceStamp $inputFile.Source
            Staged = $null; Updated = $false
        }
    }
    foreach ($record in $records) {
        $unchanged = [IO.File]::Exists($record.Destination) -and
            ((Get-FileHash -LiteralPath $record.Destination -Algorithm SHA256).Hash -eq $record.Stamp.SHA256)
        if ($unchanged) { continue }
        $record.Staged = Join-Path $stageRoot ([Guid]::NewGuid().ToString('N') + '.tmp')
        [IO.File]::Copy($record.Source, $record.Staged)
        if ((Get-FileHash -LiteralPath $record.Staged -Algorithm SHA256).Hash -ne $record.Stamp.SHA256) {
            throw "Copied bytes differ from the saved source: $($record.Source)"
        }
    }
    Assert-StableSources $records
    foreach ($record in $records | Where-Object { -not $_.IsScene }) {
        if ($record.Staged) {
            Publish-StagedFile $record.Staged $record.Destination
            $record.Updated = $true
        }
    }
    # Recheck after dependency publication, before replacing the scene.
    Assert-StableSources $records
    $scene = $records | Where-Object IsScene
    if ($scene.Staged) {
        Publish-StagedFile $scene.Staged $scene.Destination
        $scene.Updated = $true
    }
    $receiptFiles = @()
    foreach ($record in $records) {
        $destinationHash = (Get-FileHash -LiteralPath $record.Destination -Algorithm SHA256).Hash
        if ($destinationHash -ne $record.Stamp.SHA256) { throw "Destination verification failed: $($record.Destination)" }
        $receiptFiles += [pscustomobject]@{
            source = $record.Source
            destination = $record.Destination.Substring($repoPrefix.Length).Replace('\', '/')
            sourceSHA256 = $record.Stamp.SHA256; destinationSHA256 = $destinationHash
            sourceBytes = $record.Stamp.Length
            sourceLastWriteTimeUtc = [DateTime]::new($record.Stamp.Ticks, [DateTimeKind]::Utc).ToString('o')
            updated = $record.Updated
        }
    }
    $receipt = [pscustomobject]@{ syncedAtUtc = [DateTime]::UtcNow.ToString('o'); files = $receiptFiles }
    $receiptTemp = Join-Path $stageRoot 'receipt.tmp'
    [IO.File]::WriteAllText($receiptTemp, ($receipt | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding $false))
    Publish-StagedFile $receiptTemp (Join-Path $packageRoot 'build-sync-receipt.json')
    $updatedCount = @($records | Where-Object Updated).Count
    Write-Host "Build sync complete: $updatedCount updated, $($records.Count - $updatedCount) unchanged."
    Write-Host 'Only saved files were read. No Blender save, Git staging, commit, or upload was performed.'
} finally {
    # This invocation owns only these flat temporary files; preserve every recovery directory.
    Get-ChildItem -LiteralPath $stageRoot -File | Remove-Item -Force
    Remove-Item -LiteralPath $stageRoot
}
