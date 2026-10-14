$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
& "$projectRoot\.venv\Scripts\pythonw.exe" "$PSScriptRoot\launcher.py"
