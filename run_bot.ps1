<#
PowerShell launcher for Line-Homeroom-Bot

Usage: Create a scheduled task that runs the bundled `run_bot.bat` (recommended) or call this PowerShell script directly.

What it does:
- sets the working directory to the script location
- loads environment variables from a `.env` file in the same folder (simple KEY=VALUE parser)
- optionally activates a virtualenv if `venv\Scripts\Activate.ps1` exists
- runs `python main.py` with the same environment

Security note: This script reads secrets from `.env` inside the repository. Protect that file and the scheduled task credentials.
#>

Param(
    [string]$Python = $null
)

# Ensure script runs from its containing directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# Load .env if present (simple parser: KEY=VALUE, ignores comments)
if (Test-Path -Path (Join-Path $scriptDir '.env')) {
    Get-Content -Path (Join-Path $scriptDir '.env') | ForEach-Object {
        $line = $_.Trim()
        if (-not [string]::IsNullOrWhiteSpace($line) -and -not $line.StartsWith('#')) {
            $parts = $line -split '=', 2
            if ($parts.Count -eq 2) {
                $k = $parts[0].Trim()
                $v = $parts[1].Trim().Trim('"')
                # Set environment variable for this process
                $env:$k = $v
            }
        }
    }
}

# Attempt to activate virtualenv if present (optional)
$venvActivate = Join-Path $scriptDir 'venv\Scripts\Activate.ps1'
if (Test-Path -Path $venvActivate) {
    try {
        & $venvActivate
    } catch {
        Write-Verbose "Could not activate venv: $_"
    }
}

# Determine python executable
if (-not $Python) {
    if ($env:PYTHON_PATH) { $Python = $env:PYTHON_PATH } else { $Python = 'python' }
}

# Run the bot script and forward stdout/stderr
Write-Output "Running main.py using: $Python"
& $Python (Join-Path $scriptDir 'main.py')

if ($LASTEXITCODE -ne 0) {
    Write-Error "main.py exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}
