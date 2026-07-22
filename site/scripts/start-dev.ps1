# Carrega .env da raiz do monorepo e sobe BFF :8090 (obrigatório para slides/API)
$siteDir = Split-Path $PSScriptRoot -Parent
$repoRoot = Split-Path $siteDir -Parent
$bff = Join-Path $siteDir "bff"

function Import-DotEnv($path) {
    if (-not (Test-Path $path)) { return }
    Get-Content $path | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $val = $matches[2].Trim().Trim('"')
            [Environment]::SetEnvironmentVariable($name, $val, "Process")
        }
    }
}

Import-DotEnv (Join-Path $repoRoot ".env")
Import-DotEnv (Join-Path $siteDir ".env")

if (-not $env:ERP_API_KEY -and $env:SITE_ERP_API_KEY) {
    $env:ERP_API_KEY = $env:SITE_ERP_API_KEY
}
if (-not $env:ERP_TENANT_SLUG) {
    $env:ERP_TENANT_SLUG = "matriz"
}
if (-not $env:ERP_BASE_URL -and -not $env:ERP_INTERNAL_URL) {
    $env:ERP_BASE_URL = "https://loca-erp-locadora.eal7ix.easypanel.host"
}

if ($env:ERP_TENANT_SLUG -eq "rodavia") {
    Write-Host "AVISO: ERP_TENANT_SLUG=rodavia nao existe. Use matriz." -ForegroundColor Yellow
}
if ($env:ERP_API_KEY -match "COLE_SUA_CHAVE") {
    Write-Host "Configure ERP_API_KEY em .env (Integracoes > API Publica > catalogo:read)." -ForegroundColor Yellow
}

$erpUrl = if ($env:ERP_INTERNAL_URL) { $env:ERP_INTERNAL_URL } else { $env:ERP_BASE_URL }
Write-Host "Repo .env: $(Join-Path $repoRoot '.env')"
Write-Host "ERP: $erpUrl  tenant=$($env:ERP_TENANT_SLUG)"
Write-Host ""
Write-Host "Terminal 2 — site estatico:"
Write-Host "  cd `"$(Join-Path $siteDir 'public')`""
Write-Host "  python -m http.server 8080"
Write-Host ""
Write-Host "BFF nesta janela: http://127.0.0.1:8090/bff/health"
Set-Location $bff
pip install -q -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8090 --reload
