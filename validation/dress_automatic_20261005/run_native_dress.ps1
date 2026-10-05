param(
    [string[]]$Cases = @('abrupt_stop'),
    [int]$Frames = 60,
    [int]$CollisionStride = 6,
    [int]$TimeoutSeconds = 600
)
$ErrorActionPreference = 'Stop'
$dressMemory = Get-CimInstance Win32_OperatingSystem
if ($dressMemory.FreePhysicalMemory -lt 204800) {
    Write-Output 'DEFERRED_RESOURCE_CHECK'
    $dressMemory | Select-Object TotalVisibleMemorySize,FreePhysicalMemory | ConvertTo-Json -Compress
    exit 0
}
$dressRoot = 'D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005'
$dressScript = Join-Path $dressRoot 'validate_real_dress.py'
$dressExpectedSha = '613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046'
if ((Get-FileHash -LiteralPath $dressScript -Algorithm SHA256).Hash.ToLowerInvariant() -ne $dressExpectedSha) {
    throw 'Reviewed QA source changed'
}
$dressRun = Join-Path $dressRoot ('native_51_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $dressRun | Out-Null
$dressTemp = Join-Path $dressRun 'native_temp'
New-Item -ItemType Directory -Path $dressTemp | Out-Null
$dressStdout = Join-Path $dressRun 'native.stdout.log'
$dressStderr = Join-Path $dressRun 'native.stderr.log'
$dressArgs = @('--background','--factory-startup','--disable-autoexec','--threads','1',
    '--python-exit-code','2','--python',('"' + $dressScript + '"'),'--','--cases')
$dressArgs += $Cases
$dressArgs += @('--frames',[string]$Frames,'--collision-stride',[string]$CollisionStride,
    '--output',('"' + $dressRun + '"'))
$dressLaunch = @{FilePath='D:\Blender5.1\blender.exe';ArgumentList=$dressArgs;
    WindowStyle='Hidden';Environment=@{TEMP=$dressTemp;TMP=$dressTemp};
    RedirectStandardOutput=$dressStdout;RedirectStandardError=$dressStderr;PassThru=$true}
$dressChild = Start-Process @dressLaunch
Write-Output ('OWNED_QA_CHILD_PID=' + $dressChild.Id)
Write-Output ('RUN=' + $dressRun)
$dressWatch = [Diagnostics.Stopwatch]::StartNew()
$dressPeak = 0L
$dressTimedOut = $false
while (-not $dressChild.WaitForExit(1000)) {
    $dressChild.Refresh()
    $dressPeak = [Math]::Max($dressPeak, $dressChild.PeakWorkingSet64)
    if ($dressWatch.Elapsed.TotalSeconds -gt $TimeoutSeconds) {
        # This PID is the exact disposable child just created above.
        $dressChild.Kill()
        $dressChild.WaitForExit()
        $dressTimedOut = $true
        Write-Output 'OWNED_QA_CHILD_TIMEOUT'
        break
    }
}
$dressChild.Refresh()
$dressProcessResult = @{PID=$dressChild.Id;ExitCode=$dressChild.ExitCode;
    TimedOut=$dressTimedOut;ElapsedSeconds=$dressWatch.Elapsed.TotalSeconds;
    PeakWorkingSetBytes=$dressPeak;AvailableKiBBefore=$dressMemory.FreePhysicalMemory;
    ScriptSha256=$dressExpectedSha;Run=$dressRun;Cases=$Cases;Frames=$Frames}
$dressProcessResult | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dressRun 'process.json') -Encoding utf8
$dressProcessResult | ConvertTo-Json -Compress
Get-Content -LiteralPath $dressStdout -Tail 24
Get-Content -LiteralPath $dressStderr -Tail 35
$dressReport = Join-Path $dressRun 'real_dress_effect_qa.json'
if (Test-Path -LiteralPath $dressReport) {
    $dressData = Get-Content -LiteralPath $dressReport -Raw | ConvertFrom-Json
    $dressData | Select-Object success,production_effect_accepted,exception,saved_cache_preflight,checks |
        ConvertTo-Json -Depth 5
    $dressData.cases | Select-Object name,success,exception,checks,collider_summary,
        registered_body_diagnostic_summary,stop_settling | ConvertTo-Json -Depth 5
}
