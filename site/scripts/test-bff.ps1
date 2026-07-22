# Testa BFF local ou Docker (health + ping + empresa)
# Uso: .\scripts\test-bff.ps1
# Requer ERP_API_KEY válida em site\.env e ERP em v0.2.0+ (rotas /public/empresa, /public/ping)

$ErrorActionPreference = "Stop"
$siteDir = Split-Path $PSScriptRoot -Parent

$envFile = Join-Path $siteDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "Crie site\.env a partir de .env.example (ERP_API_KEY obrigatória)." -ForegroundColor Yellow
    exit 1
}

Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $val = $matches[2].Trim().Trim('"')
        [Environment]::SetEnvironmentVariable($name, $val, "Process")
    }
}

$base = "http://127.0.0.1:8090/bff"
Write-Host "BFF: $base" -ForegroundColor Cyan
Write-Host "ERP: $env:ERP_BASE_URL" -ForegroundColor Cyan

function Test-Route($path) {
    try {
        $r = Invoke-WebRequest -Uri "$base$path" -UseBasicParsing -TimeoutSec 25
        Write-Host "OK  $path -> $($r.StatusCode)" -ForegroundColor Green
        if ($r.Content.Length -lt 500) { Write-Host $r.Content }
        return $true
    }
    catch {
        $code = $_.Exception.Response.StatusCode.value__
        Write-Host "FAIL $path -> $code" -ForegroundColor Red
        try {
            $sr = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
            Write-Host $sr.ReadToEnd()
        } catch {}
        return $false
    }
}

if ($env:ERP_API_KEY -match "COLE_SUA_CHAVE") {
    Write-Host "Edite site\.env e coloque ERP_API_KEY real (Integrações > API pública no ERP)." -ForegroundColor Yellow
}

Test-Route "/health" | Out-Null
Test-Route "/ping" | Out-Null
Test-Route "/empresa" | Out-Null
Test-Route "/filiais" | Out-Null
Test-Route "/slides" | Out-Null

try {
    $filiais = Invoke-RestMethod -Uri "$base/filiais" -TimeoutSec 25
    $first = @($filiais)[0]
    if ($first.id) {
        $fid = $first.id
        $ret = (Get-Date).AddDays(1).ToString("yyyy-MM-ddT10:00:00")
        $dev = (Get-Date).AddDays(4).ToString("yyyy-MM-ddT10:00:00")
        $gpath = "/grupos?filial_id=$fid&retirada_em=$ret&devolucao_em=$dev"
        Test-Route $gpath | Out-Null
    }
} catch {
    Write-Host "FAIL /grupos (precisa de filiais)" -ForegroundColor Red
}

Write-Host "`nSe /ping ou /empresa retornam 404, faça deploy do ERP (git pull + rebuild) até v0.2.1." -ForegroundColor Yellow
