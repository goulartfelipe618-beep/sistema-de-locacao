# Cria .env na raiz do repo para o site/BFF (se ainda nao existir)
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$envPath = Join-Path $repoRoot ".env"
$example = Join-Path $repoRoot ".env.example"

if (Test-Path $envPath) {
    Write-Host ".env ja existe em $envPath"
    Write-Host "Confira: ERP_TENANT_SLUG=matriz e ERP_API_KEY (catalogo:read)"
    exit 0
}

if (-not (Test-Path $example)) {
    Write-Host "Arquivo .env.example nao encontrado." -ForegroundColor Red
    exit 1
}

Copy-Item $example $envPath
Write-Host "Criado $envPath"
Write-Host ""
Write-Host "Edite o arquivo e preencha:"
Write-Host "  ERP_API_KEY=<chave catalogo:read do ERP>"
Write-Host "  ERP_TENANT_SLUG=matriz"
Write-Host ""
Write-Host "Depois suba o BFF: site\scripts\start-dev.ps1"
