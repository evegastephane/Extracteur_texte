"""Isolated optional PaddleOCR worker, with local models and bounded lifetime."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
MODEL_ROOT = ROOT / ".ocr-data" / "paddle"
TIMEOUT = 90  # Includes import/model loading; CPU inference is heavier than Tesseract.
MODEL_NAMES = {"det": "PP-OCRv5_mobile_det", "rec": "latin_PP-OCRv5_mobile_rec"}


class PaddleFailure(Exception):
    def __init__(self, message, status=503):
        super().__init__(message)
        self.status = status


def worker_python():
    return Path(os.environ.get("EXTRACTEUR_PADDLE_PYTHON") or (
        ROOT / ".venv-paddle" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")))


def models_valid(root=MODEL_ROOT):
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("models") != MODEL_NAMES or manifest.get("smoke_test") != "passed" or not manifest.get("files"):
            return False
        # Reject unknown/escaping names even if the local manifest was edited.
        required = {f"{kind}/{name}" for kind in MODEL_NAMES for name in ("inference.json", "inference.pdiparams", "inference.yml")}
        if not required.issubset(manifest["files"]):
            return False
        for name, digest in manifest["files"].items():
            path = root / name
            if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
                return False
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                return False
        return True
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


def status():
    installed = worker_python().is_file()
    ready = installed and models_valid()
    return {"ready": ready, "timeout_seconds": TIMEOUT,
            "message": "Modèles locaux prêts." if ready else "Installation optionnelle requise : consultez le guide PaddleOCR."}


def recognize(image):
    if not status()["ready"]:
        raise PaddleFailure("PaddleOCR n’est pas préparé. Suivez le guide PaddleOCR, puis réessayez.")
    with tempfile.TemporaryDirectory(prefix="extracteur_paddle_") as directory:
        folder = Path(directory)
        image.save(folder / "image.png", format="PNG")
        command = [str(worker_python()), str(ROOT / "app" / "paddle_worker.py"), str(folder / "image.png"), str(folder / "result.json"), str(MODEL_ROOT)]
        try:
            result = subprocess.run(command, timeout=TIMEOUT, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, check=False)
        except subprocess.TimeoutExpired:
            raise PaddleFailure("PaddleOCR a dépassé 90 secondes. Essayez une zone plus petite ou Tesseract.", 504) from None
        except OSError:
            raise PaddleFailure("Impossible de démarrer PaddleOCR. Vérifiez son installation optionnelle.") from None
        if result.returncode != 0:
            # Library logs can contain recognized text: never return or log them.
            raise PaddleFailure("PaddleOCR a échoué. Vérifiez les modèles et les dépendances avec le guide d’installation.")
        try:
            payload = json.loads((folder / "result.json").read_text(encoding="utf-8"))
            if not isinstance(payload.get("text"), str):
                raise ValueError()
            return payload["text"].strip()
        except (OSError, ValueError, AttributeError):
            raise PaddleFailure("PaddleOCR a renvoyé un résultat illisible. Réessayez ou choisissez Tesseract.") from None
