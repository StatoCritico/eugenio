# Costruzione di EuGEnioVisure.exe sul PC Windows (PowerShell), dalla cartella fase11-visure:
#
#   powershell -ExecutionPolicy Bypass -File avviatore\costruisci_windows.ps1
#   powershell -ExecutionPolicy Bypass -File avviatore\costruisci_windows.ps1 -Firma     # firma con signtool
#
# Passi: ambiente Python separato (.venv-build), test, pacchetto riproducibile del lettore con la sua impronta,
# controllo che l'impronta sia quella dell'elenco delle versioni approvate, PyInstaller, prova dell'.exe (lettore e,
# dal 04/11/2026, conversione dei modelli DXF/IFC con ezdxf e IfcOpenShell), impronta dell'.exe. Serve il repository
# completo: il pacchetto prende edifici3d/importa.py dalla cartella fase10-edifici3d.
# La firma (facoltativa) usa signtool di Windows SDK con un certificato che NON sta mai nel repository: o nel
# magazzino dei certificati di Windows (chiavetta o cloud Certum SimplySign), indicato con l'impronta in
# $env:EUGENIO_FIRMA_SHA1, o nel servizio SignPath dal workflow di GitHub Actions (vedi README, «Firma»).
param([switch]$Firma)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path .venv-build)) { py -3.13 -m venv .venv-build }
.\.venv-build\Scripts\python -m pip install --upgrade pip
.\.venv-build\Scripts\python -m pip install -r avviatore\requirements-build.txt -r requirements-dev.txt

Write-Host "1. Test" -ForegroundColor Cyan
.\.venv-build\Scripts\python -m pytest -q tests
if ($LASTEXITCODE -ne 0) { throw "test non superati" }

Write-Host "2. Pacchetto del lettore e impronta" -ForegroundColor Cyan
.\.venv-build\Scripts\python avviatore\costruisci_pacchetto.py
$versione = (Select-String -Path visure\__init__.py -Pattern 'VERSIONE = "(.+)"').Matches[0].Groups[1].Value
$zip = "dist\visure-$versione.zip"
$sha = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
$elenco = Get-Content avviatore\versioni_approvate.json -Raw | ConvertFrom-Json
$voce = $elenco.versioni | Where-Object { $_.versione -eq $versione }
if (-not $voce -or $voce.sha256 -ne $sha) {
  throw "L'impronta di $zip ($sha) non e' quella dell'elenco: esegui costruisci_pacchetto.py --aggiorna-elenco e fai il commit"
}

Write-Host "3. PyInstaller" -ForegroundColor Cyan
.\.venv-build\Scripts\pyinstaller --clean --noconfirm avviatore\eugenio_visure.spec
$exe = "dist\EuGEnioVisure.exe"

if ($Firma) {
  Write-Host "4. Firma" -ForegroundColor Cyan
  if (-not $env:EUGENIO_FIRMA_SHA1) { throw "imposta `$env:EUGENIO_FIRMA_SHA1 con l'impronta del certificato (non la password)" }
  # certificato nel magazzino di Windows (chiavetta o Certum SimplySign): nessuna password in questo file
  signtool sign /sha1 $env:EUGENIO_FIRMA_SHA1 /fd SHA256 /tr http://time.certum.pl /td SHA256 /d "EuGEnio Visure" $exe
  signtool verify /pa /v $exe
}

Write-Host "5. Prova dell'.exe" -ForegroundColor Cyan
& $exe --non-aggiornare prova --modelli
if ($LASTEXITCODE -ne 0) { throw "l'.exe non supera il controllo di avvio (lettore o conversione dei modelli)" }
# conversione di un DXF e di un IFC sintetici (gli stessi dei test di parità della fase 10)
.\.venv-build\Scripts\python ..\fase10-edifici3d\tests\modelli_sintetici.py dist\modelli_prova | Out-Null
& $exe --non-aggiornare modello dist\modelli_prova\casa_sito.ifc --uscita dist\modelli_prova\casa_sito.geojson
if ($LASTEXITCODE -ne 0) { throw "l'.exe non converte l'IFC di prova" }
& $exe --non-aggiornare modello dist\modelli_prova\casa_utm.dxf --crs EPSG:7791 --uscita dist\modelli_prova\casa_utm.geojson
if ($LASTEXITCODE -ne 0) { throw "l'.exe non converte il DXF di prova" }
$shaExe = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
"$shaExe  EuGEnioVisure.exe" | Out-File -Encoding ascii dist\EuGEnioVisure.exe.sha256
"$sha  visure-$versione.zip" | Out-File -Encoding ascii "dist\visure-$versione.zip.sha256"
Write-Host "Fatto: $exe (SHA-256 $shaExe)" -ForegroundColor Green
