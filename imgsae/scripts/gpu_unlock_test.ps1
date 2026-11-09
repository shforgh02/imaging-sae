# GPU power-cap workaround test (ASUS M7600QE, RTX 3050 Ti; see docs/EXECUTION_LOG.md "GPU diagnosis").
# RUN AS ADMINISTRATOR:  right-click Start > "Terminal (Admin)", then:
#   powershell -ExecutionPolicy Bypass -File D:\Shayan\imgsae\scripts\gpu_unlock_test.ps1
# Every step is reversible. A step that does not help is undone at once; a step that helps is kept and reported.
# Output also goes to D:\Shayan\imgsae\logs\gpu_unlock_test.log.
#   Undo clock lock:      nvidia-smi -rgc        (also cleared by a restart)
#   Re-enable NVPCF:      pnputil /enable-device "ACPI\NVDA0820\NPCF"
$ErrorActionPreference = 'Continue'
$Root = 'D:\Shayan\imgsae'; $Py = "$Root\.venv\Scripts\python.exe"; $Log = "$Root\logs\gpu_unlock_test.log"
$NPCF = 'ACPI\NVDA0820\NPCF'
Start-Transcript -Path $Log -Force | Out-Null

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Write-Host "NOT ADMIN: open 'Terminal (Admin)' and run this again."; Stop-Transcript | Out-Null; exit 1 }

function Test-Gpu([string]$label) {
    Write-Host "`n=== $label"
    $out = & $Py "$Root\scripts\gpu_check.py" 2>&1 | Where-Object { $_ -notmatch 'Warning|warn' }
    $out | Select-Object -Last 4 | ForEach-Object { Write-Host $_ }
    $line = ($out | Select-String 'seconds per').Line
    $spw = [double](($line -split ':')[1].Trim() -split '\s')[0]
    $capped = $line -match 'POWER-CAPPED'
    Write-Host ("RESULT {0}: {1:N3} s per window, {2}" -f $label, $spw, ($(if ($capped) {'still capped'} else {'NOT capped'})))
    return [pscustomobject]@{ label = $label; spw = $spw; capped = $capped }
}

$base = Test-Gpu 'baseline'
$keep = @()

# Step 1: lock graphics clock to 1200-2100 MHz
Write-Host "`n--- step 1: nvidia-smi -lgc 1200,2100"; nvidia-smi -lgc 1200,2100
$t1 = Test-Gpu 'clock lock'
if ($t1.spw -lt 0.8 * $base.spw) { $keep += 'clock lock (undo: nvidia-smi -rgc)' } else { nvidia-smi -rgc | Out-Null; Write-Host 'no gain -> clock lock removed' }

# Step 2: disable NVIDIA Platform Controllers and Framework (Dynamic Boost bridge to the ASUS controller)
Write-Host "`n--- step 2: disable $NPCF"; pnputil /disable-device "$NPCF"; Start-Sleep 5
$t2 = Test-Gpu 'NVPCF disabled'
$best = [Math]::Min($base.spw, $t1.spw)
if ($t2.spw -lt 0.8 * $best) {
    $keep += "NVPCF disabled (undo: pnputil /enable-device `"$NPCF`")"
} else {
    # Step 3: both together, only if step 1 was not already kept
    if ($keep.Count -eq 0) {
        nvidia-smi -lgc 1200,2100 | Out-Null; $t3 = Test-Gpu 'NVPCF disabled + clock lock'
        if ($t3.spw -lt 0.8 * $best) { $keep += "NVPCF disabled + clock lock (undo: pnputil /enable-device `"$NPCF`"; nvidia-smi -rgc)" }
        else { nvidia-smi -rgc | Out-Null; pnputil /enable-device "$NPCF" | Out-Null; Write-Host 'no gain -> NVPCF re-enabled, clock lock removed' }
    } else { pnputil /enable-device "$NPCF" | Out-Null; Write-Host 'no extra gain -> NVPCF re-enabled' }
}

Write-Host "`n=== SUMMARY"
Write-Host ("baseline {0:N3} s/window" -f $base.spw)
if ($keep.Count) { Write-Host "KEPT (helped):"; $keep | ForEach-Object { Write-Host "  - $_" } } else { Write-Host "Nothing helped; system left exactly as before." }
Write-Host "Final state:"; nvidia-smi --query-gpu=clocks.sm,power.draw,clocks_throttle_reasons.sw_power_cap --format=csv
Stop-Transcript | Out-Null
