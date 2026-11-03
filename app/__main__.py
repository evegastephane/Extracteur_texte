from waitress import serve

from . import create_app
from .ocr import readiness

if __name__ == "__main__":
    state = readiness()
    if not state["ready"]:
        raise SystemExit("OCR indisponible : exécutez bash scripts/setup.sh et vérifiez Tesseract.")
    print("Extracteur de texte — http://127.0.0.1:8000", flush=True)
    serve(create_app(), host="127.0.0.1", port=8000, threads=4,
          max_request_body_size=10 * 1024 * 1024 + 64 * 1024)
