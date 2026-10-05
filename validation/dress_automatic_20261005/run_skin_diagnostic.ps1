$ErrorActionPreference = 'Stop'
$diagnosticMemory = Get-CimInstance Win32_OperatingSystem
if ($diagnosticMemory.FreePhysicalMemory -lt 204800) {
    Write-Output 'DEFERRED_RESOURCE_CHECK'
    exit 0
}
$diagnosticRoot = 'D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005'
$diagnosticScript = Join-Path $diagnosticRoot 'diagnose_skin_transfer.py'
$diagnosticSha = '9ad85213c41c62393b34cd5f5a45f0508bbef2ccfdf3a520f92dcf0e836f6a28'
if ((Get-FileHash -LiteralPath $diagnosticScript -Algorithm SHA256).Hash.ToLowerInvariant() -ne $diagnosticSha) {
    throw 'Reviewed diagnostic source changed'
}
$diagnosticRun = Join-Path $diagnosticRoot ('skin_transfer_51_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $diagnosticRun | Out-Null
$diagnosticTemp = Join-Path $diagnosticRun 'native_temp'
New-Item -ItemType Directory -Path $diagnosticTemp | Out-Null
$diagnosticInput = Join-Path $diagnosticRoot 'native_51_20261005_042802_905\Cosha_Dress_QA_abrupt_stop.blend'
$diagnosticStdout = Join-Path $diagnosticRun 'native.stdout.log'
$diagnosticStderr = Join-Path $diagnosticRun 'native.stderr.log'
$diagnosticArgs = @('--background','--factory-startup','--disable-autoexec','--threads','1',
    '--python-exit-code','2','--python',('"' + $diagnosticScript + '"'),'--',
    '--input',('"' + $diagnosticInput + '"'),'--output',('"' + $diagnosticRun + '"'),'--render','--probe')
$diagnosticLaunch = @{FilePath='D:\Blender5.1\blender.exe';ArgumentList=$diagnosticArgs;
    WindowStyle='Hidden';Environment=@{TEMP=$diagnosticTemp;TMP=$diagnosticTemp};
    RedirectStandardOutput=$diagnosticStdout;RedirectStandardError=$diagnosticStderr;PassThru=$true}
$diagnosticChild = Start-Process @diagnosticLaunch
Write-Output ('OWNED_DIAGNOSTIC_CHILD_PID=' + $diagnosticChild.Id)
Write-Output ('RUN=' + $diagnosticRun)
$diagnosticWatch = [Diagnostics.Stopwatch]::StartNew()
$diagnosticPeak = 0L
$diagnosticTimedOut = $false
while (-not $diagnosticChild.WaitForExit(1000)) {
    $diagnosticChild.Refresh()
    $diagnosticPeak = [Math]::Max($diagnosticPeak,$diagnosticChild.PeakWorkingSet64)
    if ($diagnosticWatch.Elapsed.TotalSeconds -gt 360) {
        $diagnosticChild.Kill()
        $diagnosticChild.WaitForExit()
        $diagnosticTimedOut = $true
        break
    }
}
$diagnosticChild.Refresh()
$diagnosticResult = @{PID=$diagnosticChild.Id;ExitCode=$diagnosticChild.ExitCode;
    TimedOut=$diagnosticTimedOut;ElapsedSeconds=$diagnosticWatch.Elapsed.TotalSeconds;
    PeakWorkingSetBytes=$diagnosticPeak;AvailableKiBBefore=$diagnosticMemory.FreePhysicalMemory;
    ScriptSha256=$diagnosticSha;Run=$diagnosticRun;Input=$diagnosticInput}
$diagnosticResult | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $diagnosticRun 'process.json') -Encoding utf8
$diagnosticResult | ConvertTo-Json -Compress
Get-Content -LiteralPath $diagnosticStdout -Tail 16
Get-Content -LiteralPath $diagnosticStderr -Tail 20
