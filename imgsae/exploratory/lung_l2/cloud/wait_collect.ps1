# Wait for a spawned L2 job and collect it (see launch.py / collect.py). Bounded loop; exits 0 when collected, 4 if a call failed,
# 6 if it is still not done after -MaxMinutes. Usage: powershell -File imgsae\exploratory\lung_l2\cloud\wait_collect.ps1 -Rid lung_l2_audit-031 -MaxMinutes 70
param([Parameter(Mandatory = $true)][string]$Rid, [int]$MaxMinutes = 70, [int]$EverySeconds = 120)
$env:PYTHONUTF8 = "1"; $t0 = Get-Date
while (((Get-Date) - $t0).TotalMinutes -lt $MaxMinutes) {
    & C:\Users\Arman\miniconda3\python.exe D:\Shayan\imgsae\exploratory\lung_l2\cloud\collect.py $Rid --wait 30
    $code = $LASTEXITCODE; "{0:HH:mm:ss} collect exit {1}" -f (Get-Date), $code
    if ($code -eq 0 -or $code -eq 4) { exit $code }
    Start-Sleep -Seconds $EverySeconds
}
"not finished after $MaxMinutes min"; exit 6
