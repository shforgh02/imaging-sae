# Stage 1a, deviation M7 (after G1, user request 2026-11-10): nonnegative dictionary learning added to the DL family.
# rep-0 rows of the 3 nonnegative DL configs -> DL family re-selected by the same rule (results/s1a_selection_m7.json) -> reps 1-2 of the
# new DL representative. Resumable like run_s1a_cpu.ps1 (rows are saved one by one; .done markers skip finished steps).
# usage (from v2_ct/): powershell -File run_s1a_m7.ps1
$ErrorActionPreference = "Continue"
$env:OMP_NUM_THREADS = "4"; $env:MKL_NUM_THREADS = "4"; $env:OPENBLAS_NUM_THREADS = "4"; $env:PYTHONUTF8 = "1"; $env:PYTHONUNBUFFERED = "1"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path; Set-Location $here
$py = Join-Path $here "..\..\.venv\Scripts\python.exe"; $log = Join-Path $here "logs\s1a_m7.log"
function L($m) { "$(Get-Date -Format s) $m" | Add-Content -Path $log -Encoding utf8 }
function Step($name, $argsList) {
  $done = Join-Path $here "logs\s1a_$name.done"
  if (Test-Path $done) { L "skip $name (done)"; return $true }
  L "start $name"; & $py s1a_run.py @argsList *>> $log
  if ($LASTEXITCODE -ne 0) { L "STOP $name exit $LASTEXITCODE"; return $false }
  Set-Content -Path $done -Value (Get-Date -Format s); L "done $name"; return $true
}
if (-not (Step "m7_rep0" @("--step", "cpu", "--reps", "0", "--names", "dl_nn_A1024_k6,dl_nn_A2048_k6,dl_nn_A1024_k27"))) { exit 1 }
if (-not (Step "m7_select" @("--step", "select_m7"))) { exit 1 }
if (-not (Step "m7_reps12" @("--step", "cpu", "--reps", "1,2", "--selected", "--selfile", "s1a_selection_m7.json", "--fams", "dl"))) { exit 1 }
L "S1A M7 DONE"
