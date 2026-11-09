# Stage 1a, local CPU part (docs/STAGE1A_PROTOCOL.md): rep-0 candidates -> selection -> reps 1-2 of the representatives -> T6 dense references.
# Resumable: every step skips finished rows; a step's .done marker skips it entirely. usage (from v2_ct/): powershell -File run_s1a_cpu.ps1
$ErrorActionPreference = "Continue"
# 4 BLAS / OpenMP threads, as Stage A (run_stageA.ps1). With the default 16 threads the sparse-varimax sanity row differs from A3 by 0.0035
# in one area (PCA / eigen-decomposition summation order); with 4 threads it is exact.
$env:OMP_NUM_THREADS = "4"; $env:MKL_NUM_THREADS = "4"; $env:OPENBLAS_NUM_THREADS = "4"; $env:PYTHONUTF8 = "1"; $env:PYTHONUNBUFFERED = "1"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path; Set-Location $here
$py = Join-Path $here "..\..\.venv\Scripts\python.exe"; $log = Join-Path $here "logs\s1a_cpu.log"
function L($m) { "$(Get-Date -Format s) $m" | Add-Content -Path $log -Encoding utf8 }
function Step($name, $argsList) {
  $done = Join-Path $here "logs\s1a_$name.done"
  if (Test-Path $done) { L "skip $name (done)"; return $true }
  L "start $name"; & $py s1a_run.py @argsList *>> $log
  if ($LASTEXITCODE -ne 0) { L "STOP $name exit $LASTEXITCODE"; return $false }
  Set-Content -Path $done -Value (Get-Date -Format s); L "done $name"; return $true
}
if (-not (Step "cpu_rep0" @("--step", "cpu", "--reps", "0"))) { exit 1 }
if (-not (Step "select" @("--step", "select"))) { exit 1 }
if (-not (Step "cpu_reps12" @("--step", "cpu", "--reps", "1,2", "--selected"))) { exit 1 }
if (-not (Step "refs" @("--step", "refs", "--reps", "0,1,2"))) { exit 1 }
L "S1A CPU DONE"
