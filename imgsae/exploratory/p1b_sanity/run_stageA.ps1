# Stage A runner: one job at a time (peak RAM ~6-7 GB), stops at the first failure. Every step resumes from saved results.
# usage: powershell -File run_stageA.ps1          (log: logs\stageA.log; per-step logs in logs\)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path; Set-Location $here
$py = Join-Path $here "..\..\.venv\Scripts\python.exe"
$env:PYTHONUTF8 = "1"; $env:PYTHONUNBUFFERED = "1"
$steps = @(
    @{ name = "a1";     threads = "2"; args = @("a1_probe_ladder.py", "--jobs", "4") },
    @{ name = "a2";     threads = "4"; args = @("a2_sae_audit.py") },
    @{ name = "a3_cpu"; threads = "4"; args = @("a3_decomp_fair.py", "--part", "cpu") },
    @{ name = "a3_sae"; threads = "4"; args = @("a3_decomp_fair.py", "--part", "sae") },
    @{ name = "a4";     threads = "2"; args = @("a4_summarize.py") }
)
"=== Stage A start $(Get-Date -Format s)" | Out-File -Append -Encoding utf8 logs\stageA.log
foreach ($s in $steps) {
    if (Test-Path "logs\$($s.name).done") { "skip $($s.name) (done)" | Out-File -Append -Encoding utf8 logs\stageA.log; continue }
    $env:OMP_NUM_THREADS = $s.threads; $env:MKL_NUM_THREADS = $s.threads; $t0 = Get-Date
    "start $($s.name) $(Get-Date -Format s)" | Out-File -Append -Encoding utf8 logs\stageA.log
    & $py -u @($s.args) *> "logs\$($s.name)_full.log"; $rc = $LASTEXITCODE
    "done $($s.name) rc=$rc $([math]::Round(((Get-Date) - $t0).TotalMinutes, 1)) min" | Out-File -Append -Encoding utf8 logs\stageA.log
    if ($rc -ne 0) { "STOP $($s.name)" | Out-File -Append -Encoding utf8 logs\stageA.log; exit $rc }
    Get-Date -Format s | Out-File -Encoding utf8 "logs\$($s.name).done"
}
"STAGE A DONE $(Get-Date -Format s)" | Out-File -Append -Encoding utf8 logs\stageA.log
