"""Prepare optional PaddleOCR models via verified TLS, then run a real smoke test.

Execute with .venv-paddle Python after installing requirements-paddle.txt.
No documents are sent to a remote service. Only model archives are downloaded.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT / ".ocr-data" / "paddle"
MODELS = {"det": "PP-OCRv5_mobile_det", "rec": "latin_PP-OCRv5_mobile_rec"}
BASE = "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0"


def download_model(name, destination):
    archive = destination.parent / f"{name}.tar"
    url = f"{BASE}/{name}_infer.tar"
    size = 0
    # Keep default certificate verification and inherited proxy configuration.
    with urlopen(url, timeout=60) as response, archive.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > 64 * 1024 * 1024:
                raise ValueError("Archive de modèle trop volumineuse.")
            output.write(chunk)
    unpacked = destination.parent / f"{name}-unpacked"
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        if len(members) > 200 or sum(item.size for item in members) > 256 * 1024 * 1024:
            raise ValueError("Archive de modèle hors limites.")
        if any(not (item.isfile() or item.isdir()) for item in members):
            raise ValueError("Liens et fichiers spéciaux interdits dans les modèles.")
        tar.extractall(unpacked, filter="data")
    configs = list(unpacked.rglob("inference.yml"))
    if len(configs) != 1:
        raise ValueError("Structure du modèle officiel inattendue.")
    shutil.copytree(configs[0].parent, destination)
    for filename in ("inference.yml", "inference.json", "inference.pdiparams"):
        if not (destination / filename).is_file():
            raise ValueError(f"Fichier du modèle manquant : {filename}")
    return {"url": url, "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}


def smoke_test(models):
    from PIL import Image, ImageDraw, ImageFont
    font_path = next((path for path in [Path("C:/Windows/Fonts/arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")] if path.is_file()), None)
    font = ImageFont.truetype(str(font_path), 48) if font_path else ImageFont.load_default(size=48)
    with tempfile.TemporaryDirectory(prefix="paddle_setup_") as temp:
        directory = Path(temp)
        with Image.new("RGB", (900, 200), "white") as image:
            ImageDraw.Draw(image).text((40, 60), "LOCAL OCR 123", font=font, fill="black")
            image.save(directory / "smoke.png")
        result = subprocess.run([sys.executable, str(ROOT / "app/paddle_worker.py"),
            str(directory / "smoke.png"), str(directory / "result.json"), str(models)],
            timeout=90, check=False)
        if result.returncode != 0:
            raise RuntimeError("Le test PaddleOCR a échoué. Aucun modèle n’a été activé.")
        recognized = json.loads((directory / "result.json").read_text(encoding="utf-8"))["text"]
        if "LOCAL" not in recognized.upper() or "123" not in recognized:
            raise RuntimeError("Le moteur n’a pas reconnu le texte synthétique attendu.")


def main():
    os.chdir(ROOT)
    # Importing app.paddle_engine would import Flask, intentionally absent here.
    if DESTINATION.exists():
        spec = importlib.util.spec_from_file_location("paddle_integrity", ROOT / "app/paddle_engine.py")
        integrity = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(integrity)
        if not integrity.models_valid(DESTINATION):
            raise SystemExit("Les modèles existants ne correspondent pas au manifeste. Préservez ou renommez .ocr-data/paddle avant réinstallation.")
        smoke_test(DESTINATION)
        print("PaddleOCR : test réel réussi avec les modèles existants.")
        return
    DESTINATION.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="paddle_download_", dir=DESTINATION.parent) as temp:
        stage = Path(temp)
        prepared = stage / "prepared"; prepared.mkdir()
        sources = {}
        for kind, name in MODELS.items():
            print(f"Téléchargement du modèle officiel {name}…", flush=True)
            sources[kind] = download_model(name, stage / kind)
            shutil.move(str(stage / kind), prepared / kind)
        smoke_test(prepared)
        files = {str(path.relative_to(prepared)).replace(os.sep, "/"): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in prepared.rglob("*") if path.is_file()}
        manifest = {"models": MODELS, "files": files, "sources": sources, "smoke_test": "passed"}
        (prepared / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        shutil.move(str(prepared), DESTINATION)
    print("PaddleOCR prêt : modèles locaux et test réel réussis. Redémarrez l’application.")


if __name__ == "__main__":
    try:
        main()
    except (URLError, TimeoutError, subprocess.TimeoutExpired) as error:
        raise SystemExit("Préparation interrompue : téléchargement ou test expiré/refusé. Vérifiez Internet et l’accès à paddle-model-ecology.bj.bcebos.com, puis relancez. Aucun nouveau modèle n’a été activé.") from None
