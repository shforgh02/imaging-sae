# Lung L2, plan step P4b: S4 on all dev data, in the fixed order of docs/HANDOVER_PROMPT_L2_EXEC.md (P4b item 2). Free, on the PC.
# Run only after the S3 gate (results/s3_checks_all.json) passed and the S4 code commit is logged ("S4 analysis code fixed").
# Each step logs to imgsae_data\lung_l2\logs\<step>.txt; the run stops at the first step that fails.
# usage: powershell -NoProfile -ExecutionPolicy Bypass -File imgsae\exploratory\lung_l2\run_s4_dev.ps1 [-From <step>]
param([string]$From = "")
$PY = "D:\Shayan\imgsae\.venv\Scripts\python.exe"; $L2 = "D:\Shayan\imgsae\exploratory\lung_l2"
$VOL = "D:\Shayan\imgsae_data\lung_l2_vol\l2"; $A = "D:\Shayan\imgsae_data\lung_l2\dev"; $R = "$L2\results\s4"; $LOG = "D:\Shayan\imgsae_data\lung_l2\logs"
$H = "$VOL\run_info\heads.npz"; $CAL = "$VOL\run_info\sybil_ensemble_simple_calibrator.json"
$env:PYTHONUTF8 = "1"; Remove-Item Env:L2_S4_DATA -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $A, $R, $LOG | Out-Null
$steps = [ordered]@{
  "l2_data"      = @("$L2\l2_data.py", $VOL, "dev", "$L2\results\manifest_dev.csv", "D:\Shayan\imgsae_data\idc_index_25.0.5\nlst_series_meta.csv", "D:\Shayan\imgsae_data\nlst_public\tables", "D:\Shayan\imgsae_data\nlst_public\Shetty_et_al(Google)_data_splits.p", "$L2\results\l2_form_params.json", $A)
  "s4_scores"    = @("$L2\s4_scores.py", $A, $R)
  "s4_q1a"       = @("$L2\s4_q1a.py", "$A\exams_dev.csv", "$A\arrays_dev_main.npz", $R, "dev")
  "s4_decomp_64" = @("$L2\s4_decomp.py", "$A\exams_dev.csv", "$A\arrays_dev_main.npz", $H, $R, "--K", "64", "--device", "cuda")
  "s4_decomp_128"= @("$L2\s4_decomp.py", "$A\exams_dev.csv", "$A\arrays_dev_main.npz", $H, $R, "--K", "128", "--device", "cuda")
  "s4_q1b_u"     = @("$L2\s4_q1b_u.py", $A, $R, $H)
  "s4_q1c"       = @("$L2\s4_q1c.py", $A, $R)
  "s4_q1d"       = @("$L2\s4_q1d.py", $A, $R, $H)
  "s4_q2"        = @("$L2\s4_q2.py", $A, $R)
  "s4_u1a"       = @("$L2\s4_u1a.py", $A, $R, $H, $CAL)
  "s4_u2"        = @("$L2\s4_u2.py", $A, $R)
  "s4_u3"        = @("$L2\s4_u3.py", $A, $R)
  "s4_u4"        = @("$L2\s4_u4.py", $A, $R)
  "s4_refs"      = @("$L2\s4_refs.py", $A, $R)
  "s4_gate"      = @("$L2\s4_gate.py", $R, "--assembled", $A)
  "s4_report"    = @("$L2\s4_report.py", $R, "$R\RESULTS_S4_dev_tables.md")
}
$go = ($From -eq "")
foreach ($k in $steps.Keys) {
  if (-not $go -and $k -eq $From) { $go = $true }
  if (-not $go) { continue }
  $t0 = Get-Date; "{0:u} start {1}" -f (Get-Date).ToUniversalTime(), $k
  & $PY @($steps[$k]) *> "$LOG\$k.txt"; $c = $LASTEXITCODE
  "{0:u} {1} exit {2} ({3:N0} s)" -f (Get-Date).ToUniversalTime(), $k, $c, ((Get-Date) - $t0).TotalSeconds
  if ($c -ne 0) { "STOP at $k (see $LOG\$k.txt)"; exit $c }
}
"S4 DEV RUN DONE"
