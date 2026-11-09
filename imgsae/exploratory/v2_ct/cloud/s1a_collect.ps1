# Fetch Stage 1a SAE results that the cloud jobs saved on the volume (/s1a_out) and merge the ones missing from results/s1a_sae.json
# (used when the local Modal client died before collecting). usage (from v2_ct/): pwsh -File cloud\s1a_collect.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path; $v2 = Split-Path -Parent $here; $env:PYTHONUTF8 = "1"
$modal = "C:\Users\Arman\miniconda3\Scripts\modal.exe"; $dst = Join-Path $v2 "..\p1b_sanity\cloud\stage\s1a_out"   # git-ignored folder
New-Item -ItemType Directory -Force $dst | Out-Null
& $modal volume get --force imgsae-p1b /s1a_out $dst; if ($LASTEXITCODE) { throw "volume get failed" }
& (Join-Path $v2 "..\..\.venv\Scripts\python.exe") (Join-Path $here "s1a_merge.py") $dst
