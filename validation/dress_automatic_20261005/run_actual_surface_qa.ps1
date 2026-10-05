param(
    [ValidateSet('install','motion','export','worker','collider')][string]$Stage = 'install',
    [string]$InputBlend = 'D:\Blender\Projects\Character\X\X.blend',
    [string]$InstallReport,
    [string]$ExpectedSurfaceSha,
    [string]$ExpectedWorkerSha,
    [string[]]$Cases = @('abrupt_stop'),
    [int]$Frames = 60,
    [int]$TimeoutSeconds = 600,
    [switch]$NoRender
)
$ErrorActionPreference = 'Stop'
# The caller must hold the current cross-chat serial resource window.
# This launcher never stops an artist application or a shared process.
$dressMemory = Get-CimInstance Win32_OperatingSystem
if ($dressMemory.FreePhysicalMemory -lt 204800) {
    Write-Output 'DEFERRED_RESOURCE_CHECK'
    exit 0
}
$dressRoot = 'D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005'
$dressRepository = 'D:\MyRepository\Blender-addons-by-Randy'
$dressScripts = @{
    install = Join-Path $dressRoot 'verify_actual_surface_workflow.py'
    motion = Join-Path $dressRoot 'verify_actual_surface_workflow.py'
    export = Join-Path $dressRoot 'verify_actual_surface_export.py'
    worker = Join-Path $dressRepository 'tests\test_unity_export_worker_blender.py'
    collider = Join-Path $dressRepository 'tests\test_skirt_collider_fitting_blender.py'
}
$dressScript = $dressScripts[$Stage]
$dressRun = Join-Path $dressRoot ('actual_' + $Stage + '_51_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
$dressTemp = Join-Path $dressRun 'native_temp'
New-Item -ItemType Directory -Path $dressTemp | Out-Null
$dressStdout = Join-Path $dressRun 'native.stdout.log'
$dressStderr = Join-Path $dressRun 'native.stderr.log'
$dressSurfaceHash = (Get-FileHash -LiteralPath (Join-Path $dressRepository 'addons\character_designer\skirt_surface.py')).Hash.ToLowerInvariant()
$dressWorkerHash = (Get-FileHash -LiteralPath (Join-Path $dressRepository 'addons\character_designer\unity_export_worker.py')).Hash.ToLowerInvariant()
$dressArgs = @('--background','--factory-startup','--disable-autoexec','--threads','1',
    '--python-exit-code','2','--python',('"' + $dressScript + '"'))
if ($Stage -ne 'worker') {
    $dressOutput = if ($Stage -eq 'collider') { Join-Path $dressRun 'result' } else { $dressRun }
    $dressArgs += @('--','--input',('"' + $InputBlend + '"'),'--output',('"' + $dressOutput + '"'),'--source','Dress')
    if ($Stage -in @('install','motion')) { $dressArgs += @('--stage',$Stage) }
    if ($Stage -in @('motion','export','collider')) {
        if (-not $InstallReport) { throw 'Motion/export require the passing installation report.' }
        # Default to the exact code accepted by this installation gate. A
        # later reviewed surface/worker change must be supplied explicitly.
        $dressInstalled = Get-Content -LiteralPath $InstallReport -Raw | ConvertFrom-Json
        if ($dressInstalled.success -ne $true) { throw 'The installation gate did not pass.' }
        if (-not $ExpectedSurfaceSha) {
            $ExpectedSurfaceSha = $dressInstalled.source_manifest_after.PSObject.Properties |
                Where-Object { $_.Name -eq (Join-Path $dressRepository 'addons\character_designer\skirt_surface.py') } |
                ForEach-Object { $_.Value.sha256 }
        }
        if (-not $ExpectedWorkerSha) {
            $ExpectedWorkerSha = $dressInstalled.source_manifest_after.PSObject.Properties |
                Where-Object { $_.Name -eq (Join-Path $dressRepository 'addons\character_designer\unity_export_worker.py') } |
                ForEach-Object { $_.Value.sha256 }
        }
        if ($ExpectedSurfaceSha -ne $dressSurfaceHash -or $ExpectedWorkerSha -ne $dressWorkerHash) {
            throw 'Runtime differs from the installation gate or explicitly reviewed hashes.'
        }
        if ($Stage -eq 'collider') {
            if ((Get-FileHash -LiteralPath $InputBlend).Hash.ToLowerInvariant() -ne $dressInstalled.prepared_candidate.sha256) {
                throw 'Collider fitting requires the exact passing installation QA bytes.'
            }
        } else {
            $dressArgs += @('--install-report',('"' + $InstallReport + '"'),
                '--expected-surface-sha',$ExpectedSurfaceSha,'--expected-worker-sha',$ExpectedWorkerSha)
        }
    }
    if ($Stage -eq 'motion') {
        $dressArgs += @('--frames',[string]$Frames,'--cases') + $Cases
        if ($NoRender) { $dressArgs += '--no-render' }
    }
}
$dressChild = Start-Process -FilePath 'D:\Blender5.1\blender.exe' -ArgumentList $dressArgs `
    -WindowStyle Hidden -Environment @{TEMP=$dressTemp;TMP=$dressTemp} `
    -RedirectStandardOutput $dressStdout -RedirectStandardError $dressStderr -PassThru
Write-Output ('OWNED_QA_CHILD_PID=' + $dressChild.Id)
Write-Output ('RUN=' + $dressRun)
$dressWatch = [Diagnostics.Stopwatch]::StartNew()
$dressPeak = 0L
$dressTimedOut = $false
while (-not $dressChild.WaitForExit(1000)) {
    $dressChild.Refresh()
    $dressPeak = [Math]::Max($dressPeak, $dressChild.PeakWorkingSet64)
    if ($dressWatch.Elapsed.TotalSeconds -gt $TimeoutSeconds) {
        $dressChild.Kill() # Exact disposable process returned by Start-Process.
        $dressChild.WaitForExit()
        $dressTimedOut = $true
        break
    }
}
$dressChild.Refresh()
$dressResult = @{Stage=$Stage;PID=$dressChild.Id;ExitCode=$dressChild.ExitCode;TimedOut=$dressTimedOut;
    ElapsedSeconds=$dressWatch.Elapsed.TotalSeconds;PeakWorkingSetBytes=$dressPeak;
    AvailableKiBBefore=$dressMemory.FreePhysicalMemory;ScriptSha256=(Get-FileHash -LiteralPath $dressScript).Hash.ToLowerInvariant();
    SurfaceSha256=$dressSurfaceHash;WorkerSha256=$dressWorkerHash;Run=$dressRun;Input=$InputBlend;
    InstallReport=$InstallReport;Cases=$Cases;Frames=$Frames;NoRender=[bool]$NoRender}
$dressResult | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $dressRun 'process.json') -Encoding utf8
$dressResult | ConvertTo-Json -Compress
Get-Content -LiteralPath $dressStdout -Tail 10
Get-Content -LiteralPath $dressStderr -Tail 16
if ($dressTimedOut -or $dressChild.ExitCode -ne 0) { exit 2 }
