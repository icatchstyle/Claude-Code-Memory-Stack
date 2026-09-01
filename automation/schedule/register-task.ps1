<#
.SYNOPSIS
    Windows — register the daily harvest as a Scheduled Task that runs inside WSL.

.DESCRIPTION
    Claude Code and the knowledge base live in WSL, so the task calls `wsl.exe` rather than
    running the script directly. Run this script from an elevated PowerShell prompt.

    Starts in DRY RUN. Once you trust what the digests contain, add --write to $Arguments.

.EXAMPLE
    .\register-task.ps1 -ScriptPath "/home/you/stack/automation/run.sh"
#>
param(
    [Parameter(Mandatory = $true)][string]$ScriptPath,
    [string]$TaskName = "KnowledgeMiner",
    [string]$Time = "07:20"
)

# --write is deliberately absent: an unattended agent should not get write access by default.
$Arguments = "-e bash -lc `"$ScriptPath`""

$action    = New-ScheduledTaskAction -Execute "wsl.exe" -Argument $Arguments
$trigger   = New-ScheduledTaskTrigger -Daily -At $Time
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable `
                -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Daily knowledge harvest from past Claude Code sessions" `
    -Force

Write-Host "Registered '$TaskName' for $Time daily (dry run)." -ForegroundColor Green
Write-Host "Inspect it with: Get-ScheduledTask -TaskName $TaskName"
Write-Host "Remove it with:  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
