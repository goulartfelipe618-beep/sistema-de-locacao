# Dev sem Docker: BFF :8090 + site estático :8080 (CORS via rodavia-config)
$siteDir = Split-Path $PSScriptRoot -Parent
$public = Join-Path $siteDir "public"
$bff = Join-Path $siteDir "bff"

if (-not (Test-Path (Join-Path $siteDir ".env"))) {
    Copy-Item (Join-Path $siteDir ".env.example") (Join-Path $siteDir ".env")
    Write-Host "Criado .env — configure ERP_API_KEY antes de testar ping/empresa."
}

Get-Content (Join-Path $siteDir ".env") | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim().Trim('"'), "Process")
    }
}

Write-Host "Site: http://127.0.0.1:8080  (outro terminal: cd public; python -m http.server 8080)"
Write-Host "BFF:  http://127.0.0.1:8090  (esta janela — obrigatorio)"
Write-Host "rodavia-config.js ja aponta para :8090 em localhost (sem Docker)."
Set-Location $bff
pip install -q -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8090 --reload
