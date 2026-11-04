from waitress import serve

from . import create_app
from .paddle_engine import zone_status

if __name__ == "__main__":
    state = zone_status()
    if not state["ready"]:
        print("PaddleOCR à préparer : l’interface reste disponible. Voir docs/PADDLEOCR.md.", flush=True)
    print("Extracteur de texte — http://127.0.0.1:8000", flush=True)
    serve(create_app(), host="127.0.0.1", port=8000, threads=4,
          max_request_body_size=20 * 1024 * 1024 + 128 * 1024)
