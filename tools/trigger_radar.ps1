# Starts the daily radar workflow when GitHub's own schedule has not (the user, 2026-11-21: alerts reached the board late;
# GitHub dropped or delayed scheduled runs by 1-9 hours). Run by a Windows scheduled task every 2 hours ("job-radar-trigger").
# Gap-fill only: it starts a run when none has been created in the last 3 hours (or none is running), so it never doubles
# the schedule and the monthly Actions minutes stay inside the free tier (a run is about 6 minutes).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$log = Join-Path $root "work\trigger_radar.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
function Write-Log($m) { Add-Content -Path $log -Value ("{0:u} {1}" -f (Get-Date).ToUniversalTime(), $m) }
try {
    Set-Location $root
    $json = & gh run list --workflow radar.yml --limit 1 --json createdAt,status
    $last = ($json | ConvertFrom-Json) | Select-Object -First 1
    if ($last) {
        $age = (New-TimeSpan -Start ([datetime]$last.createdAt).ToUniversalTime() -End (Get-Date).ToUniversalTime()).TotalMinutes
        if ($last.status -ne "completed" -or $age -lt 180) {
            Write-Log ("skip: last run {0} min ago, status {1}" -f [int]$age, $last.status)
            exit 0
        }
    }
    & gh workflow run radar.yml
    Write-Log "started a run"
} catch {
    Write-Log ("error: " + $_.Exception.Message)
    exit 1
}
