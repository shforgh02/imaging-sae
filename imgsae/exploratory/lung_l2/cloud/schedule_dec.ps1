# Creates the one-time Windows scheduled task "imgsae_l2_dec": on 2026-12-01 01:00 local time (or as soon as the PC is on after that)
# it runs run_dec.cmd = the unattended driver for tiers D2, D3, D4 (every launch through the budget guard; stops on any problem).
# Run by the lead:  powershell -NoProfile -ExecutionPolicy Bypass -File D:\Shayan\imgsae\exploratory\lung_l2\cloud\schedule_dec.ps1
# Remove it again:  Unregister-ScheduledTask -TaskName imgsae_l2_dec -Confirm:$false
$at  = [datetime]::ParseExact('2026-12-01 01:00', 'yyyy-MM-dd HH:mm', [System.Globalization.CultureInfo]::InvariantCulture)
$act = New-ScheduledTaskAction -Execute 'D:\Shayan\imgsae\exploratory\lung_l2\cloud\run_dec.cmd'
$trg = New-ScheduledTaskTrigger -Once -At $at
$set = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 12) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'imgsae_l2_dec' -Action $act -Trigger $trg -Settings $set -Description 'Lung L2 S3 December tiers D2, D3, D4 (unattended, guard-checked)' -Force | Out-Null
$t = Get-ScheduledTask -TaskName 'imgsae_l2_dec'
"created: imgsae_l2_dec, starts " + $t.Triggers[0].StartBoundary
