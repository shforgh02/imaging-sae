# Upload what the Stage 1a SAE jobs need beyond the Stage A upload: X_null (untrained CT-FM tokens, for the T9 null SAE) as
# /p1/rows_extra.npz on the volume imgsae-p1b (2.1 GB; byte copy of the array in data/p1/rows.npz, values unchanged).
# The physics R3 input is rebuilt in the job from p1b_sanity/results/cache_refpos.npz (baked into the image). usage: pwsh -File cloud\upload_s1a.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path; $v2 = Split-Path -Parent $here; $p1 = Join-Path $v2 "..\..\data\p1" | Resolve-Path
$stageDir = Join-Path $v2 "..\p1b_sanity\cloud\stage\p1" | Resolve-Path   # git-ignored staging folder of the Stage A upload
$modal = "C:\Users\Arman\miniconda3\Scripts\modal.exe"; $py = "C:\Users\Arman\miniconda3\python.exe"; $env:PYTHONUTF8 = "1"
$log = Join-Path $v2 "logs\s1a_upload.log"; function L($m) { "$(Get-Date -Format s) $m" | Tee-Object -Append -FilePath $log }
$out = Join-Path $stageDir "rows_extra.npz"
$code = @'
import shutil, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as zi, zipfile.ZipFile(sys.argv[2], "w", zipfile.ZIP_STORED, allowZip64=True) as zo:
    with zi.open("X_null.npy") as fi, zo.open("X_null.npy", "w", force_zip64=True) as fo: shutil.copyfileobj(fi, fo, 1 << 24)
    assert [i.filename for i in zo.infolist()] == ["X_null.npy"]
print("ok")
'@
L "stage rows_extra.npz (X_null)"; & $py -c $code (Join-Path $p1 "rows.npz") $out; if ($LASTEXITCODE) { throw "staging failed" }
L ("staged {0:N2} GB" -f ((Get-Item $out).Length / 1GB)); $t0 = Get-Date
& $modal volume put --force imgsae-p1b $out "/p1/rows_extra.npz"; if ($LASTEXITCODE) { throw "put failed" }
L ("put done {0:N1} min" -f ((Get-Date) - $t0).TotalMinutes)
& $modal volume ls imgsae-p1b /p1 2>&1 | Out-String -Width 200 | % { L $_ }
L "UPLOAD DONE"
