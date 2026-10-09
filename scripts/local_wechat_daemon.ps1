param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "ProteinDesignRadar"),
    [string]$AccountName = "CAOM",
    [int]$IntervalMinutes = 30
)

$ErrorActionPreference = "Continue"
$RepositoryPath = Join-Path $InstallRoot "repository"
$WechRssPath = Join-Path $InstallRoot "wechrss"
$PythonPath = Join-Path $InstallRoot "venv\Scripts\python.exe"
$SyncScript = Join-Path $RepositoryPath "scripts\local_wechat_sync.py"
$LogPath = Join-Path $InstallRoot "logs"
$WechRssLog = Join-Path $LogPath "wechrss.log"
$SyncLog = Join-Path $LogPath "sync.log"

New-Item -ItemType Directory -Force -Path $LogPath | Out-Null
$CreatedNew = $false
$Mutex = New-Object System.Threading.Mutex($true, "Local\ProteinDesignRadar-WeChat", [ref]$CreatedNew)
if (-not $CreatedNew) {
    exit 0
}

function Test-WechRss {
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/health" -TimeoutSec 3
        return $true
    }
    catch {
        return $false
    }
}

function Start-WechRss {
    $arguments = '/d /c "start.bat --no-open >> ""{0}"" 2>&1"' -f $WechRssLog
    Start-Process `
        -FilePath "cmd.exe" `
        -ArgumentList $arguments `
        -WorkingDirectory $WechRssPath `
        -WindowStyle Hidden
}

function Invoke-LocalSync {
    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = $PythonPath
    $processInfo.Arguments = '"{0}" --account "{1}"' -f $SyncScript, $AccountName
    $processInfo.WorkingDirectory = $RepositoryPath
    $processInfo.UseShellExecute = $false
    $processInfo.CreateNoWindow = $true
    $processInfo.RedirectStandardOutput = $true
    $processInfo.RedirectStandardError = $true
    $processInfo.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $processInfo.StandardErrorEncoding = [System.Text.Encoding]::UTF8

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $processInfo
    $null = $process.Start()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($stdout) {
        $stdout.TrimEnd() | Out-File -FilePath $SyncLog -Append -Encoding utf8
    }
    if ($stderr) {
        $stderr.TrimEnd() | Out-File -FilePath $SyncLog -Append -Encoding utf8
    }
}

try {
    while ($true) {
        if (-not (Test-WechRss)) {
            Start-WechRss
            $deadline = (Get-Date).AddMinutes(5)
            do {
                Start-Sleep -Seconds 5
            } while (-not (Test-WechRss) -and (Get-Date) -lt $deadline)
        }

        if (Test-WechRss) {
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            "[$timestamp] Starting local WeChat sync" | Out-File -FilePath $SyncLog -Append -Encoding utf8
            Invoke-LocalSync
        }
        else {
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            "[$timestamp] WechRss is unavailable; retrying later" | Out-File -FilePath $SyncLog -Append -Encoding utf8
        }

        Start-Sleep -Seconds ([Math]::Max(5, $IntervalMinutes) * 60)
    }
}
finally {
    $Mutex.ReleaseMutex()
    $Mutex.Dispose()
}
