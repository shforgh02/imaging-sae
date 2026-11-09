# Phase 1 launcher for the Windows laptop (replaces the Mac `prun` runner and the `macperf` pre-check).
#   powershell -File scripts\run_phase1.ps1            start (or resume) Phase 1 in the background
#   powershell -File scripts\run_phase1.ps1 -Status    is it running? last log lines + GPU state
# Machine rules (plan): one GPU job at a time, normal priority, <= 4 threads, completion line in the log, never stop another job.
param([switch]$Status, [switch]$Force)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root '.venv\Scripts\python.exe'
$Log = Join-Path $Root 'logs\phase1.log'
$PidFile = Join-Path $Root 'logs\phase1.pid'

function Get-Runner {
    if (-not (Test-Path $PidFile)) { return $null }
    $p = Get-Process -Id ([int](Get-Content $PidFile)) -ErrorAction SilentlyContinue
    if ($p -and $p.ProcessName -match 'python|cmd') { return $p } else { return $null }
}

# On Windows (WDDM) nvidia-smi lists every desktop app that touches the GPU (browser, Telegram, VPN, ...).
# Only processes that look like compute jobs count as "another GPU job".
$JobPattern = '\\(python|pythonw|julia|matlab|Rscript|ollama|java)\.exe$'
function Get-GpuJobs {
    nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader | Where-Object { ($_ -split ',', 2)[1].Trim() -match $JobPattern }
}

function Show-Gpu {
    nvidia-smi --query-gpu=name,utilization.gpu,clocks.sm,clocks.max.sm,memory.used,memory.total,temperature.gpu,clocks_throttle_reasons.sw_power_cap --format=csv
    $apps = Get-GpuJobs
    if ($apps) { "compute jobs on GPU:"; $apps } else { "no compute jobs on GPU" }
}

if ($Status) {
    $r = Get-Runner
    if ($r) { "RUNNING  pid $($r.Id)  started $($r.StartTime)" } else { "NOT RUNNING" }
    if (Test-Path $Log) { "--- last lines of logs\phase1.log"; Get-Content $Log -Tail 12 }
    "--- GPU"; Show-Gpu
    exit 0
}

if (Get-Runner) { Write-Host "Phase 1 is already running (pid $(Get-Content $PidFile)). Use -Status."; exit 1 }
$apps = Get-GpuJobs
if ($apps -and -not $Force) {
    Write-Host "Another compute job is using the GPU; not starting (rule: one GPU job at a time). Re-run with -Force to override:"; $apps; exit 1
}
if (-not (Test-Path $Py)) { Write-Host "venv missing: $Py"; exit 1 }

New-Item -ItemType Directory -Force (Split-Path $Log) | Out-Null
$cmd = "set OMP_NUM_THREADS=4&& set MKL_NUM_THREADS=4&& set VECLIB_MAXIMUM_THREADS=4&& set PYTHONUTF8=1&& set PYTHONUNBUFFERED=1&& " +
       "`"$Py`" scripts\run_phase1.py >> `"$Log`" 2>&1"
$p = Start-Process -FilePath cmd.exe -ArgumentList '/c', $cmd -WorkingDirectory $Root -WindowStyle Hidden -PassThru
$p.Id | Set-Content $PidFile
"started Phase 1 (pid $($p.Id)); log: $Log"
"progress: Get-Content `"$Log`" -Tail 20     status: powershell -File scripts\run_phase1.ps1 -Status"
"finished when the log ends with 'PHASE1 DONE' or a 'STOP ...' line."
