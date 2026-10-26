# Roda toda a suite: pytest (com Postgres se DATABASE_URL/DATABASE_URL_RO estiverem no .env), tsc e vitest.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
if (Test-Path .env) { Get-Content .env | ForEach-Object { if ($_ -match '^(\w+)=(.*)$') { Set-Item "env:$($Matches[1])" $Matches[2] } } }

python -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Push-Location frontend
npx tsc --noEmit
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm test
exit $LASTEXITCODE
