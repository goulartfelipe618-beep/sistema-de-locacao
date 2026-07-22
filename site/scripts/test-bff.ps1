# Testa BFF (local :8090 ou Docker :80) + rotas do ERP incluindo slides
# Uso: .\scripts\test-bff.ps1
# Requer .env na raiz do repo OU site/.env com ERP_API_KEY e ERP_TENANT_SLUG=matriz

$ErrorActionPreference = "Stop"
$siteDir = Split-Path $PSScriptRoot -Parent
$repoRoot = Split-Path $siteDir -Parent

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

$bases = @("http://127.0.0.1:8090/bff", "http://127.0.0.1:8080/bff")
$base = $null
foreach ($candidate in $bases) {
    try {
        Invoke-WebRequest -Uri "$candidate/health" -UseBasicParsing -TimeoutSec 5 | Out-Null
        $base = $candidate
        break
    } catch {}
}
if (-not $base) {
    Write-Host "BFF offline. Suba com: site\scripts\start-dev.ps1  ou  docker compose up site" -ForegroundColor Red
    exit 1
}

$erpUrl = if ($env:ERP_INTERNAL_URL) { $env:ERP_INTERNAL_URL } elseif ($env:ERP_BASE_URL) { $env:ERP_BASE_URL } else { '(nao definido)' }
$tenant = if ($env:ERP_TENANT_SLUG) { $env:ERP_TENANT_SLUG } else { 'matriz' }
Write-Host "BFF: $base" -ForegroundColor Cyan
Write-Host "ERP alvo: $erpUrl" -ForegroundColor Cyan
Write-Host "Tenant: $tenant" -ForegroundColor Cyan

if ($env:ERP_TENANT_SLUG -eq "rodavia") {
    Write-Host "ERRO: tenant rodavia nao existe no ERP. Altere para matriz no .env" -ForegroundColor Red
}

function Test-Route($path) {
    try {
        $r = Invoke-WebRequest -Uri "$base$path" -UseBasicParsing -TimeoutSec 25
        Write-Host "OK  $path -> $($r.StatusCode)" -ForegroundColor Green
        if ($r.Content.Length -lt 600) { Write-Host $r.Content }
        return $r
    }
    catch {
        $code = $_.Exception.Response.StatusCode.value__
        Write-Host "FAIL $path -> $code" -ForegroundColor Red
        try {
            $sr = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
            Write-Host $sr.ReadToEnd()
        } catch {}
        return $null
    }
}

Test-Route "/health" | Out-Null
Test-Route "/ping" | Out-Null
Test-Route "/empresa" | Out-Null
Test-Route "/filiais" | Out-Null

$slidesResp = Test-Route "/slides"
if ($slidesResp) {
    try {
        $slides = $slidesResp.Content | ConvertFrom-Json
        $count = @($slides).Count
        Write-Host "Slides retornados: $count" -ForegroundColor Cyan
        if ($count -gt 0 -and $slides[0].id) {
            $sid = $slides[0].id
            $img = Test-Route "/slides/$sid/imagem"
            if ($img -and $img.RawContentLength -gt 1000) {
                Write-Host "Imagem OK ($($img.RawContentLength) bytes)" -ForegroundColor Green
            }
        }
    } catch {
        Write-Host "Resposta /slides nao e JSON valido" -ForegroundColor Red
    }
}

Write-Host "`nSe /health mostra issues ou erp_status != ok, revise ERP_API_KEY e ERP_TENANT_SLUG=matriz." -ForegroundColor Yellow
