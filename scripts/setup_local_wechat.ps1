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
$StartupPath = [Environment]::GetFolderPath("Startup")

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

$DaemonScript = Join-Path $RepositoryPath "scripts\local_wechat_daemon.ps1"
$StartupFile = Join-Path $StartupPath "ProteinDesignRadar-WeChat.cmd"
$StartupCommand = '@start "" powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" -InstallRoot "{1}" -AccountName "{2}"' -f `
    $DaemonScript, $InstallRoot, $AccountName
Set-Content -LiteralPath $StartupFile -Value $StartupCommand -Encoding Ascii

Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList @(
        "-NoProfile",
        "-WindowStyle", "Hidden",
        "-ExecutionPolicy", "Bypass",
        "-File", $DaemonScript,
        "-InstallRoot", $InstallRoot,
        "-AccountName", $AccountName
    ) `
    -WindowStyle Hidden
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
