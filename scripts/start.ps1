# Sobe tudo: Postgres (docker) -> pipeline -> migracoes + carga -> API (8000) -> frontend (5173).
# Uso:  .\scripts\start.ps1            (Ctrl+C encerra API e frontend; o Postgres continua no Docker)
#       .\scripts\start.ps1 -SetupOnly (prepara banco e dados e sai, sem subir API/frontend)
param([switch]$SetupOnly)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "ERRO: $msg" -ForegroundColor Red; exit 1 }
function Run($label, [scriptblock]$cmd) {
    # docker/pip/npm escrevem progresso em stderr; so o codigo de saida importa
    $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & $cmd 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($code -ne 0) { Fail "$label falhou (codigo $code)" }
}

foreach ($tool in "docker", "python", "node", "npm") {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { Fail "'$tool' nao encontrado no PATH" }
}

Step "Configuracao (.env)"
if (-not (Test-Path .env)) {
    $rand = { -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ }) }
    $owner = & $rand
    $api = & $rand
    $etl = & $rand
    $audit = & $rand
    $db, $user, $port = "fidelidade", "fidelidade_owner", 5432
    @(
        "POSTGRES_DB=$db", "POSTGRES_USER=$user", "POSTGRES_PORT=$port",
        "POSTGRES_PASSWORD=$owner", "POSTGRES_API_PASSWORD=$api",
        "POSTGRES_ETL_PASSWORD=$etl", "POSTGRES_AUDIT_PASSWORD=$audit",
        "DATABASE_URL=postgresql://${user}:${owner}@127.0.0.1:${port}/${db}",
        "DATABASE_URL_RO=postgresql://fidelidade_ro:${api}@127.0.0.1:${port}/${db}",
        "DATABASE_URL_ETL=postgresql://fidelidade_etl:${etl}@127.0.0.1:${port}/${db}",
        "DATABASE_URL_AUDIT=postgresql://fidelidade_api_audit:${audit}@127.0.0.1:${port}/${db}",
        "CORS_ORIGINS=http://localhost:5173"
    ) | Set-Content .env -Encoding ascii
    Write-Host ".env criado com senhas aleatorias (nao versionado)."
}
Get-Content .env | ForEach-Object { if ($_ -match '^(\w+)=(.*)$') { Set-Item "env:$($Matches[1])" $Matches[2] } }
if (-not $env:JWT_SECRET) {
    $env:JWT_SECRET = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
    Add-Content .env "JWT_SECRET=$($env:JWT_SECRET)" -Encoding ascii
    Write-Host "JWT_SECRET gerado e salvo no .env (nao versionado)."
}

Step "PostgreSQL (docker compose)"
Run "docker compose up" { docker compose up -d }
$status = ""
for ($i = 0; $i -lt 40 -and $status -ne "healthy"; $i++) {
    $status = docker inspect -f "{{.State.Health.Status}}" fidelidade-postgres 2>$null
    if ($status -ne "healthy") { Start-Sleep 2 }
}
if ($status -ne "healthy") { Fail "Postgres nao ficou saudavel (veja: docker logs fidelidade-postgres)" }

Step "Dependencias Python"
Run "pip install" { python -m pip install -q -r requirements.txt }

Step "Pipeline de dados sinteticos + testes de qualidade"
Run "pipeline" { python -m src.pipeline }

Step "Migracoes e carga idempotente no Postgres"
Run "carga" { python -m src.db all }

if ($SetupOnly) { Write-Host "`nPreparo concluido (-SetupOnly)." -ForegroundColor Green; exit 0 }

Step "Dependencias do frontend"
if (-not (Test-Path frontend\node_modules)) { Push-Location frontend; Run "npm install" { npm install --no-audit --no-fund }; Pop-Location }

Step "Subindo API e frontend"
$env:DEMO_LOGIN = "1"   # botoes de perfil na tela de login (so neste processo local; nao e gravado no .env)
$procs = @()
try {
    $procs += Start-Process python -ArgumentList "-m", "uvicorn", "src.api.main:app", "--port", "8000" -PassThru -NoNewWindow
    $procs += Start-Process cmd -ArgumentList "/c", "cd frontend && npm run dev" -PassThru -NoNewWindow
    Write-Host "`nAPI:      http://localhost:8000/docs`nFrontend: http://localhost:5173`nCtrl+C para encerrar." -ForegroundColor Green
    Write-Host "Token de teste (8h, perfil gestor): python -m src.api.tokens --sub seu.apelido --role gestor" -ForegroundColor Yellow
    Wait-Process -Id $procs[0].Id
}
finally {
    foreach ($p in $procs) { & taskkill /PID $p.Id /T /F 2>$null | Out-Null }
}
