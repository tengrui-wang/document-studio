param([string]$Python = '', [switch]$SkipTests)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not $Python) { $Python = Join-Path $projectRoot '.venv\Scripts\python.exe' }
function Assert-Success([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE" }
}
if (-not $SkipTests) {
    & $Python -m pytest -q
    Assert-Success 'Tests'
}
& $Python "$PSScriptRoot\collect_licenses.py"
Assert-Success 'Collect licenses'
& $Python -m PyInstaller --noconfirm packaging/DocumentStudio.spec
Assert-Success 'PyInstaller'
$testProcess = Start-Process -FilePath "$projectRoot\dist\DocumentStudio\DocumentStudio.exe" -ArgumentList '--smoke-test' -PassThru -WindowStyle Hidden
if (-not $testProcess.WaitForExit(30000)) { $testProcess.Kill(); throw 'Packaged app startup timed out' }
if ($testProcess.ExitCode -ne 0) { throw 'Packaged app startup failed' }
$reportPath = Join-Path $projectRoot 'build\packaged-selftest.json'
$workerTest = Start-Process -FilePath "$projectRoot\dist\DocumentStudio\DocumentStudio.exe" -ArgumentList '--self-test', ('--self-test-report="' + $reportPath + '"') -PassThru -WindowStyle Hidden
if (-not $workerTest.WaitForExit(120000)) { $workerTest.Kill(); throw 'Packaged worker test timed out' }
if ($workerTest.ExitCode -ne 0) { throw "Packaged worker test failed; see $reportPath" }
New-Item -ItemType Directory -Force release | Out-Null
$appVersion = (& $Python -c 'from document_studio import __version__; print(__version__)').Trim()
$appNumericVersion = (& $Python -c 'from document_studio import __version__; from packaging.version import Version; print(".".join(map(str, (list(Version(__version__).release)+[0,0,0,0])[:4])))').Trim()
Compress-Archive -LiteralPath "$projectRoot\dist\DocumentStudio" -DestinationPath "$projectRoot\release\DocumentStudio-$appVersion-Windows-x64.zip" -Force
$compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$innoPath = if ($compiler) { $compiler.Source } else { 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' }
if (Test-Path -LiteralPath $innoPath) {
    & $innoPath "/DAppVersion=$appVersion" "/DAppNumericVersion=$appNumericVersion" packaging/installer.iss
    Assert-Success 'Inno Setup'
} else {
    Write-Host 'Portable ZIP built. Installer will be built by GitHub Actions using Inno Setup.'
}
Copy-Item -LiteralPath "$projectRoot\CHANGELOG.md" -Destination "$projectRoot\release\RELEASE-NOTES.md" -Force
Get-ChildItem -LiteralPath "$projectRoot\release" -File | Where-Object { $_.Extension -in '.zip', '.exe' } | ForEach-Object {
    $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower()
    "$hash  $($_.Name)" | Set-Content -LiteralPath "$($_.FullName).sha256" -Encoding ascii
}
