# Fetches the Workday boards from this PC and publishes them for the daily run (the user, 2026-11-22: GitHub's runner is blocked by Cloudflare).
# Run by the Windows scheduled task "job-radar-workday" twice a day; polite (one request every 2 s, stops when refused). Log: work\workday_pc.log
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$log = Join-Path $root "work\workday_pc.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
try {
    Set-Location $root
    $out = & python tools/workday_pc.py 2>&1 | Out-String
    Add-Content -Path $log -Value ("{0:u} {1}" -f (Get-Date).ToUniversalTime(), $out.Trim())
} catch {
    Add-Content -Path $log -Value ("{0:u} error: {1}" -f (Get-Date).ToUniversalTime(), $_.Exception.Message)
    exit 1
}
