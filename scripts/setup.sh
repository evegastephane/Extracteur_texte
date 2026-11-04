#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
if ! command -v tesseract >/dev/null; then
  echo 'Base installée. Tesseract est optionnel (anciens outils/tests). Préparez PaddleOCR selon docs/PADDLEOCR.md puis lancez .venv/bin/python -m app.'
  exit 0
fi
mkdir -p .ocr-data
data_base='https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/87416418657359cb625c412a48b6e1d6d41c29bd'
for lang in eng fra; do
  case "$lang" in
    eng) expected='7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2' ;;
    fra) expected='ced037562e8c80c13122dece28dd477d399af80911a28791a66a63ac1e3445ca' ;;
  esac
  destination=".ocr-data/$lang.traineddata"
  if ! printf '%s  %s\n' "$expected" "$destination" | sha256sum --check --status 2>/dev/null; then
    temporary=$(mktemp .ocr-data/download.XXXXXX)
    trap 'rm -f "$temporary"' EXIT
    curl --fail --location --silent --show-error "$data_base/$lang.traineddata" -o "$temporary"
    printf '%s  %s\n' "$expected" "$temporary" | sha256sum --check --status
    mv "$temporary" "$destination"
    trap - EXIT
  fi
done
.venv/bin/python -c 'from app.ocr import readiness; state = readiness(); print(state); assert state["ready"], "Moteur ou langues manquants"'
echo 'Base installée. Préparez PaddleOCR selon docs/PADDLEOCR.md. Démarrage : .venv/bin/python -m app'
