"""Prepare optional PaddleOCR models via verified TLS, then run a real smoke test.

Execute with .venv-paddle Python after installing requirements-paddle.txt.
No documents are sent to a remote service. Only model archives are downloaded.
"""
import hashlib
import argparse
import importlib.util
from importlib.metadata import PackageNotFoundError, version
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


class SetupFailure(RuntimeError):
    """An explicitly local setup/test failure, not a download diagnosis."""


def run_smoke_worker(command, stage):
    print(f"Test local : {stage} (délai maximal : 90 secondes)…", flush=True)
    environment = os.environ.copy()
    environment["EXTRACTEUR_PADDLE_DIAGNOSTICS"] = "1"
    environment["PYTHONUNBUFFERED"] = "1"
    try:
        result = subprocess.run(command, timeout=90, check=False, env=environment)
    except subprocess.TimeoutExpired:
        raise SetupFailure(f"Le test LOCAL « {stage} » a dépassé 90 secondes. Ce dépassement ne prouve pas un problème Internet. La dernière ligne [Paddle] indique l’étape bloquée. Les modèles existants sont conservés ; la lecture CNI n’est pas activée.") from None
    if result.returncode != 0:
        raise SetupFailure(f"Le test LOCAL « {stage} » a échoué (code {result.returncode}). Consultez les lignes [Paddle] et l’erreur juste au-dessus ; aucun téléchargement supplémentaire n’est demandé pendant ce test.")


def write_manifest(path, manifest):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix="manifest_", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


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


def smoke_test(models, check_legacy=False):
    from PIL import Image, ImageDraw, ImageFont
    font_path = next((path for path in [Path("C:/Windows/Fonts/arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")] if path.is_file()), None)
    font = ImageFont.truetype(str(font_path), 48) if font_path else ImageFont.load_default(size=48)
    with tempfile.TemporaryDirectory(prefix="paddle_setup_") as temp:
        directory = Path(temp)
        with Image.new("RGB", (900, 200), "white") as image:
            draw = ImageDraw.Draw(image)
            draw.text((40, 60), "LOCAL OCR 123", font=font, fill="black")
            image.save(directory / "smoke.png")
            left, top, right, bottom = draw.textbbox((40, 60), "LOCAL OCR 123", font=font)
            with image.crop((left - 8, top - 8, right + 8, bottom + 8)) as line:
                line.save(directory / "zone-smoke.png")
        fields = ("nom", "prenoms", "date_naissance", "lieu_naissance", "sexe", "taille", "profession")
        jobs = [{"field": field, "path": str(directory / "zone-smoke.png")} for field in fields]
        (directory / "zones.json").write_text(json.dumps(jobs), encoding="utf-8")
        run_smoke_worker([sys.executable, "-u", str(ROOT / "app/paddle_worker.py"),
            str(directory / "smoke.png"), str(directory / "zones-result.json"), str(models), str(directory / "zones.json")], "reconnaissance directe des sept zones CNI")
        zones = json.loads((directory / "zones-result.json").read_text(encoding="utf-8"))["zones"]
        if set(zones) != set(fields) or any("LOCAL" not in zone["text"].upper() or "123" not in zone["text"] for zone in zones.values()):
            raise SetupFailure("Le test local a terminé, mais le texte synthétique attendu n’a pas été reconnu dans chaque zone.")
        print("Test des zones CNI réussi.", flush=True)
        if check_legacy:
            run_smoke_worker([sys.executable, "-u", str(ROOT / "app/paddle_worker.py"),
                str(directory / "smoke.png"), str(directory / "result.json"), str(models)], "ancien pipeline généraliste (optionnel)")
            recognized = json.loads((directory / "result.json").read_text(encoding="utf-8"))["text"]
            if "LOCAL" not in recognized.upper() or "123" not in recognized:
                raise SetupFailure("L’ancien pipeline n’a pas reconnu le texte synthétique attendu.")


def main(check_legacy=False):
    os.chdir(ROOT)
    print("Préparation du moteur CNI par zones — aucun test généraliste requis.", flush=True)
    print(f"Python {sys.version.split()[0]} · {64 if sys.maxsize > 2**32 else 32} bits", flush=True)
    for package in ("paddleocr", "paddlepaddle", "paddlex"):
        try:
            print(f"{package} : {version(package)}", flush=True)
        except PackageNotFoundError:
            print(f"{package} : non installé dans ce Python", flush=True)
    # Importing app.paddle_engine would import Flask, intentionally absent here.
    if DESTINATION.exists():
        print("Vérification des empreintes des modèles existants…", flush=True)
        spec = importlib.util.spec_from_file_location("paddle_integrity", ROOT / "app/paddle_engine.py")
        integrity = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(integrity)
        if not integrity.models_valid(DESTINATION):
            raise SystemExit("Les modèles existants ne correspondent pas au manifeste. Préservez ou renommez .ocr-data/paddle avant réinstallation.")
        manifest_path = DESTINATION / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["zone_smoke_test"] = "pending"
        if check_legacy:
            manifest["smoke_test"] = "pending"
        write_manifest(manifest_path, manifest)
        if check_legacy:
            smoke_test(DESTINATION, check_legacy=True)
            manifest["smoke_test"] = "passed"
        else:
            smoke_test(DESTINATION)
        manifest["zone_smoke_test"] = "passed"
        write_manifest(manifest_path, manifest)
        print("PaddleOCR CNI : test réel des zones réussi avec les modèles existants.", flush=True)
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
        if check_legacy:
            smoke_test(prepared, check_legacy=True)
        else:
            smoke_test(prepared)
        files = {str(path.relative_to(prepared)).replace(os.sep, "/"): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in prepared.rglob("*") if path.is_file()}
        manifest = {"models": MODELS, "files": files, "sources": sources, "smoke_test": "passed" if check_legacy else "not_run", "zone_smoke_test": "passed"}
        write_manifest(prepared / "manifest.json", manifest)
        shutil.move(str(prepared), DESTINATION)
    print("PaddleOCR prêt : modèles locaux et test réel réussis. Redémarrez l’application.")


def cli():
    parser = argparse.ArgumentParser(description="Préparer PaddleOCR CNI et diagnostiquer chaque étape locale.")
    parser.add_argument("--check-legacy", action="store_true", help="Tester aussi l’ancien détecteur généraliste, non utilisé par le parcours CNI.")
    args = parser.parse_args()
    try:
        main(check_legacy=args.check_legacy)
    except (URLError, TimeoutError):
        raise SystemExit("Échec du TÉLÉCHARGEMENT des modèles : vérifiez Internet et l’accès HTTPS à paddle-model-ecology.bj.bcebos.com. Aucun nouveau modèle n’a été activé.") from None
    except SetupFailure as error:
        raise SystemExit(str(error)) from None
    except KeyboardInterrupt:
        raise SystemExit("Préparation arrêtée par l’utilisateur. Les modèles existants sont conservés ; relancez quand vous serez prêt.") from None


if __name__ == "__main__":
    cli()
