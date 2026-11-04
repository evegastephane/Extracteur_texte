$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$tesseractAvailable = $true
if (-not (Get-Command tesseract -ErrorAction SilentlyContinue)) {
    $engine = Join-Path $env:ProgramFiles "Tesseract-OCR\tesseract.exe"
    if (-not (Test-Path $engine)) {
        $tesseractAvailable = $false
    } else {
        $env:Path += ";$(Split-Path $engine -Parent)"
    }
}

py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.12 est requis (commande py -3.12)." }
$python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
& $python -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "Installation des dependances echouee." }
if (-not $tesseractAvailable) {
    Write-Host 'Base installee. Tesseract est optionnel. Preparez PaddleOCR selon docs/PADDLEOCR.md puis lancez .\.venv\Scripts\python.exe -m app'
    return
}

New-Item -ItemType Directory -Force .ocr-data | Out-Null
$base = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/87416418657359cb625c412a48b6e1d6d41c29bd"
$hashes = @{
    eng = "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2"
    fra = "ced037562e8c80c13122dece28dd477d399af80911a28791a66a63ac1e3445ca"
}
foreach ($lang in @("eng", "fra")) {
    $destination = Join-Path (Get-Location) ".ocr-data\$lang.traineddata"
    if ((Test-Path $destination) -and ((Get-FileHash $destination -Algorithm SHA256).Hash.ToLowerInvariant() -eq $hashes[$lang])) { continue }
    $temporary = "$destination.$([guid]::NewGuid().ToString('N')).tmp"
    try {
        Invoke-WebRequest "$base/$lang.traineddata" -OutFile $temporary -UseBasicParsing
        if ((Get-FileHash $temporary -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hashes[$lang]) {
            throw "Verification SHA-256 echouee pour $lang."
        }
        Move-Item -Force $temporary $destination
    } finally {
        if (Test-Path $temporary) { Remove-Item $temporary }
    }
}
$env:TESSDATA_PREFIX = (Resolve-Path .ocr-data).Path
@'
from app.ocr import readiness
state = readiness()
print(state)
assert state["ready"], "Moteur ou langues manquants"
'@ | & $python -
if ($LASTEXITCODE -ne 0) { throw "Tesseract ou ses langues sont indisponibles." }
Write-Host 'Base installee. Preparez PaddleOCR selon docs/PADDLEOCR.md. Demarrage : .\.venv\Scripts\python.exe -m app'
