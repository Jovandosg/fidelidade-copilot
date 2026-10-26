# Regenera frontend/openapi.json (a partir da API) e os tipos TypeScript. Requer Node 20+.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python scripts/export_openapi.py
npx --yes openapi-typescript@7 frontend/openapi.json -o frontend/src/api/schema.d.ts
