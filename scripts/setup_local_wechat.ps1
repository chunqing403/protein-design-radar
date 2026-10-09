param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "ProteinDesignRadar"),
    [string]$RepositoryUrl = "https://github.com/chunqing403/protein-design-radar.git",
    [string]$AccountName = "CAOM"
)

$ErrorActionPreference = "Stop"
$WechRssCommit = "412d316073228ce7b306e25de6a21ea730b059fb"
$RepositoryPath = Join-Path $InstallRoot "repository"
$WechRssPath = Join-Path $InstallRoot "wechrss"
$VenvPath = Join-Path $InstallRoot "venv"
$PythonPath = Join-Path $VenvPath "Scripts\python.exe"
$LogPath = Join-Path $InstallRoot "logs"
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

function Assert-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Assert-Command "git"
Assert-Command "python"
New-Item -ItemType Directory -Force -Path $InstallRoot, $LogPath | Out-Null

if (-not (Test-Path (Join-Path $RepositoryPath ".git"))) {
    git clone $RepositoryUrl $RepositoryPath
}
else {
    git -C $RepositoryPath pull --ff-only
}

if (-not (Test-Path (Join-Path $WechRssPath ".git"))) {
    git clone https://github.com/johamwon/wechrss.git $WechRssPath
}
git -C $WechRssPath fetch origin $WechRssCommit
git -C $WechRssPath checkout --detach $WechRssCommit

if (-not (Test-Path $PythonPath)) {
    python -m venv $VenvPath
}
& $PythonPath -m pip install --disable-pip-version-check -r (Join-Path $RepositoryPath "requirements-site.txt")

$WechRssLog = Join-Path $LogPath "wechrss.log"
$WechRssArguments = '/d /c "start.bat >> ""{0}"" 2>&1"' -f $WechRssLog
$WechRssAction = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument $WechRssArguments `
    -WorkingDirectory $WechRssPath
$WechRssTrigger = New-ScheduledTaskTrigger -AtLogOn -User $CurrentUser
$Principal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask `
    -TaskName "ProteinDesignRadar-WechRss" `
    -Action $WechRssAction `
    -Trigger $WechRssTrigger `
    -Principal $Principal `
    -Settings $Settings `
    -Force | Out-Null

$SyncScript = Join-Path $RepositoryPath "scripts\local_wechat_sync.py"
$SyncLog = Join-Path $LogPath "sync.log"
$SyncArguments = '/d /c ""{0}" "{1}" --account "{2}" >> "{3}" 2>&1"' -f `
    $PythonPath, $SyncScript, $AccountName, $SyncLog
$SyncAction = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument $SyncArguments `
    -WorkingDirectory $RepositoryPath
$SyncTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(5) `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
Register-ScheduledTask `
    -TaskName "ProteinDesignRadar-WeChatSync" `
    -Action $SyncAction `
    -Trigger $SyncTrigger `
    -Principal $Principal `
    -Settings $Settings `
    -Force | Out-Null

Start-ScheduledTask -TaskName "ProteinDesignRadar-WechRss"
$deadline = (Get-Date).AddMinutes(5)
do {
    Start-Sleep -Seconds 3
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/health" -TimeoutSec 3
    }
    catch {
        $health = $null
    }
} while (-not $health -and (Get-Date) -lt $deadline)

if (-not $health) {
    throw "WechRss did not become ready. Check $LogPath\wechrss.log"
}

Start-Process "http://127.0.0.1:8080"
Write-Host "Local WeChat automation is installed."
Write-Host "1. In the opened WechRss page, scan the QR code in Settings."
Write-Host "2. Add one CAOM article URL as the source."
Write-Host "3. The repository will be checked every 30 minutes."
Write-Host "Logs: $LogPath"
