# Step R (rescue scouting, dev only): the full-dev runs. usage: run_r_dev.ps1 cpu | gpu | shared
# Each config writes its own result file at once; a finished config is skipped on restart.
param([string]$part = "cpu")
$env:OMP_NUM_THREADS = 4; $env:MKL_NUM_THREADS = 4; $env:OPENBLAS_NUM_THREADS = 4; $env:PYTHONUNBUFFERED = 1
$py = "D:\Shayan\imgsae\.venv\Scripts\python.exe"; $L2 = $PSScriptRoot
$A = "D:\Shayan\imgsae_data\lung_l2\dev"; $H = "D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info\heads.npz"; $R = "$L2\results\r"
$cpuArms = "raw,pca,ica,nmf,kmeans"
if ($part -eq "shared") { & $py "$L2\r2_shared.py" $A $H $R; & $py "$L2\r2_shared.py" $A $H $R --npc 50 }
if ($part -eq "cpu") {
    & $py "$L2\r1_arms.py" $A $H $R --layer h --K 64 --arms raw,pca          # check: must reproduce S4
    & $py "$L2\r1_arms.py" $A $H $R --layer h --K 8,16 --arms $cpuArms       # R3
    & $py "$L2\r1_arms.py" $A $H $R --layer pooled --K 64,16 --arms $cpuArms # R4
}
if ($part -eq "gpu") {   # SAE fits; V2 on member 0 only (about 1 minute per fit on this GPU)
    & $py "$L2\r1_arms.py" $A $H $R --layer h --K 64 --arms sae --sae-k 16,8,32 --v2-members 0 --device cuda       # R2
    & $py "$L2\r1_arms.py" $A $H $R --layer h --K 16 --arms sae --sae-k 4,8 --v2-members 0 --device cuda           # R3
    & $py "$L2\r1_arms.py" $A $H $R --layer pooled --K 64 --arms sae --sae-k 16,4 --v2-members 0 --device cuda     # R4
    & $py "$L2\r1_arms.py" $A $H $R --layer pooled --K 16 --arms sae --sae-k 4,1 --v2-members 0 --device cuda      # R4
    & $py "$L2\r1_arms.py" $A $H $R --layer h --K 8 --arms sae --sae-k 2,4 --v2-members 0 --device cuda            # R3
}
