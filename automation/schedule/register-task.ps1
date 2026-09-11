<#
.SYNOPSIS
    Windows — register the daily harvest as a Scheduled Task.

.DESCRIPTION
    Runs the harvest natively through the Python launcher. WSL is not required: the runner is
    Python and standard library only. If your knowledge base and CLI live inside WSL, pass
    -UseWsl and give -ScriptPath as a WSL path.

    Starts in DRY RUN. Once you trust what the digests contain, pass -Write.

    The task runs under Interactive logon, which means it does not start while nobody is
    logged in; -StartWhenAvailable catches the missed run up at the next logon.

.EXAMPLE
    .\register-task.ps1 -ScriptPath "C:\stack\automation\run.py"

.EXAMPLE
    .\register-task.ps1 -ScriptPath "/home/you/stack/automation/run.sh" -UseWsl -Write
#>
param(
    [Parameter(Mandatory = $true)][string]$ScriptPath,
    [string]$TaskName = "KnowledgeMiner",
    [string]$Time = "07:20",
    [switch]$UseWsl,
    [switch]$Write
)

# --write is deliberately opt-in: an unattended agent should not get write access by default.
$harvestArgs = if ($Write) { " --write" } else { "" }

if ($UseWsl) {
    $execute   = "wsl.exe"
    $arguments = "-e bash -lc `"$ScriptPath$harvestArgs`""
} else {
    # py.exe is the launcher shipped with python.org installs and resolves the right
    # interpreter without a hard-coded version path. Fall back to python.exe on PATH.
    $launcher = if (Get-Command py.exe -ErrorAction SilentlyContinue) { "py.exe" } else { "python.exe" }
    $execute   = $launcher
    $arguments = if ($launcher -eq "py.exe") { "-3 `"$ScriptPath`"$harvestArgs" } else { "`"$ScriptPath`"$harvestArgs" }
}

$action    = New-ScheduledTaskAction -Execute $execute -Argument $arguments
$trigger   = New-ScheduledTaskTrigger -Daily -At $Time
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable `
                -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Daily knowledge harvest from past agent sessions" `
    -Force

$mode = if ($Write) { "write mode" } else { "dry run" }
Write-Host "Registered '$TaskName' for $Time daily ($mode)." -ForegroundColor Green
Write-Host "Command: $execute $arguments"
Write-Host "Inspect it with: Get-ScheduledTask -TaskName $TaskName"
Write-Host "Remove it with:  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
Write-Host ""
Write-Host "A registered task that starts on time still proves nothing about the harvest:" -ForegroundColor Yellow
Write-Host "  py -3 `"$ScriptPath`" --status"
