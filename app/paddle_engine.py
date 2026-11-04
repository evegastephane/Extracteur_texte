"""Isolated optional PaddleOCR worker, with local models and bounded lifetime."""
import hashlib
import json
import math
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


def models_valid(root=None):
    root = MODEL_ROOT if root is None else Path(root)
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("models") != MODEL_NAMES or not manifest.get("files"):
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
    try:
        ready = ready and json.loads((MODEL_ROOT / "manifest.json").read_text(encoding="utf-8")).get("smoke_test") == "passed"
    except (OSError, ValueError, AttributeError):
        ready = False
    return {"ready": ready, "timeout_seconds": TIMEOUT,
            "message": "Modèles locaux prêts." if ready else "Installation optionnelle requise : consultez le guide PaddleOCR."}


def zone_status():
    ready = worker_python().is_file() and models_valid()
    try:
        manifest = json.loads((MODEL_ROOT / "manifest.json").read_text(encoding="utf-8"))
        ready = ready and manifest.get("zone_smoke_test") == "passed"
    except (OSError, ValueError, AttributeError):
        ready = False
    return {"ready": ready, "message": "Reconnaissance par zones prête." if ready else "Relancez scripts/setup_paddle.py avec Python de .venv-paddle pour préparer et tester la lecture par zones."}


def recognize(image, structured=False):
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
            if structured:
                tokens = payload.get("tokens")
                if not isinstance(tokens, list):
                    raise ValueError()
                for token in tokens:
                    if not isinstance(token.get("text"), str) or len(token.get("box", [])) != 4:
                        raise ValueError()
                    if any(type(value) not in (float, int) or not math.isfinite(value) for value in token["box"]):
                        raise ValueError()
                return payload
            return payload["text"].strip()
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            raise PaddleFailure("PaddleOCR a renvoyé un résultat illisible. Réessayez ou choisissez Tesseract.") from None


def recognize_zones(crops):
    """Recognize all value crops in ONE worker/model load; never detect full-page text."""
    expected = {"nom", "prenoms", "date_naissance", "lieu_naissance", "sexe", "taille", "profession"}
    if set(crops) != expected:
        raise PaddleFailure("Le gabarit des zones est invalide.")
    if not zone_status()["ready"]:
        raise PaddleFailure("Le moteur par zones n’est pas prêt. Relancez scripts/setup_paddle.py avec Python de .venv-paddle (guide docs/PADDLEOCR.md), puis réessayez.")
    with tempfile.TemporaryDirectory(prefix="extracteur_cni_") as directory:
        folder = Path(directory)
        jobs = []
        for key, image in crops.items():
            path = folder / f"{key}.png"
            image.save(path, format="PNG")
            jobs.append({"field": key, "path": str(path)})
        (folder / "zones.json").write_text(json.dumps(jobs), encoding="utf-8")
        command = [str(worker_python()), str(ROOT / "app/paddle_worker.py"),
                   str(folder / "nom.png"), str(folder / "result.json"), str(MODEL_ROOT), str(folder / "zones.json")]
        try:
            completed = subprocess.run(command, timeout=TIMEOUT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except subprocess.TimeoutExpired:
            raise PaddleFailure("La lecture des zones a dépassé 90 secondes. Reprenez des photos plus nettes et réessayez.", 504) from None
        except OSError:
            raise PaddleFailure("Impossible de lancer PaddleOCR. Vérifiez son installation.") from None
        try:
            if completed.returncode != 0:
                raise ValueError()
            payload = json.loads((folder / "result.json").read_text(encoding="utf-8"))
            if set(payload.get("zones", {})) != expected:
                raise ValueError()
            for value in payload["zones"].values():
                if not isinstance(value.get("text"), str) or len(value["text"]) > 200:
                    raise ValueError()
                score = value.get("score")
                if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
                    raise ValueError()
            return payload["zones"]
        except (OSError, ValueError, TypeError, AttributeError):
            raise PaddleFailure("La lecture par zones a échoué. Vérifiez PaddleOCR et ses modèles ; aucune valeur n’a été inventée.") from None
