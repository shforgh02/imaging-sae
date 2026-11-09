# Upload what A3 --part sae needs to the Modal volume imgsae-p1b (about 3 GB; storage about $0.27/month, delete with
# `modal volume delete imgsae-p1b` when the project no longer needs it). rows.npz is cut to the arrays the job reads (byte copies, values unchanged).
# usage (from p1b_sanity/): powershell -File cloud\upload_p1.ps1      log: logs\cloud_upload.log
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path; $san = Split-Path -Parent $here; $p1 = Join-Path $san "..\..\data\p1" | Resolve-Path
$modal = "C:\Users\Arman\miniconda3\Scripts\modal.exe"; $py = "C:\Users\Arman\miniconda3\python.exe"; $env:PYTHONUTF8 = "1"
$stage = Join-Path $here "stage\p1"; New-Item -ItemType Directory -Force $stage | Out-Null; $log = Join-Path $san "logs\cloud_upload.log"
function L($m) { "$(Get-Date -Format s) $m" | Tee-Object -Append -FilePath $log }
L "stage rows.npz subset"
$code = @'
import shutil, sys, zipfile
keep = {k + ".npy" for k in ["X_ctfm", "lab", "scan", "gidx"] + [f"prep_{p}_{q}" for p in ("ctfm", "null", "ref") for q in ("mu", "sc")]}
with zipfile.ZipFile(sys.argv[1]) as zi, zipfile.ZipFile(sys.argv[2], "w", zipfile.ZIP_STORED, allowZip64=True) as zo:
    for n in zi.namelist():
        if n in keep:
            with zi.open(n) as fi, zo.open(n, "w", force_zip64=True) as fo: shutil.copyfileobj(fi, fo, 1 << 24)
    assert {i.filename for i in zo.infolist()} == keep, "missing arrays"
print("ok")
'@
& $py -c $code (Join-Path $p1 "rows.npz") (Join-Path $stage "rows.npz"); if ($LASTEXITCODE) { throw "staging failed" }
L ("staged {0:N2} GB" -f ((Get-Item (Join-Path $stage "rows.npz")).Length / 1GB))
& $modal volume create imgsae-p1b 2>&1 | Out-String | % { L $_.Trim() }
foreach ($f in @("concepts.json", "gates.json")) { & $modal volume put --force imgsae-p1b (Join-Path $p1 $f) "/p1/$f"; if ($LASTEXITCODE) { throw "put $f failed" } }
L "small files done; perturb (0.8 GB)"; $t0 = Get-Date
& $modal volume put --force imgsae-p1b (Join-Path $p1 "perturb") "/p1/perturb"; if ($LASTEXITCODE) { throw "put perturb failed" }
L ("perturb done {0:N1} min" -f ((Get-Date) - $t0).TotalMinutes); $t0 = Get-Date
& $modal volume put --force imgsae-p1b (Join-Path $stage "rows.npz") "/p1/rows.npz"; if ($LASTEXITCODE) { throw "put rows failed" }
L ("rows.npz done {0:N1} min" -f ((Get-Date) - $t0).TotalMinutes)
& $modal volume ls imgsae-p1b /p1 2>&1 | Out-String -Width 200 | % { L $_ }
L "UPLOAD DONE"
