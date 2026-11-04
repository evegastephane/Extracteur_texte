import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest
from PIL import Image

from app import create_app
from app import paddle_engine as engine
from scripts import setup_paddle
from test_app import image_bytes


@pytest.mark.skipif(not engine.status()["ready"], reason="Modèles PaddleOCR locaux non préparés : test de reconnaissance réelle non exécuté")
def test_real_paddle_ocr_when_prepared():
    from app.ocr import extract
    result = extract(image_bytes(), "fra", engine="paddleocr")
    assert "Bonjour" in result and "monde" in result


def test_optional_api_unavailable_and_invalid_engine(monkeypatch):
    monkeypatch.setattr(engine, "worker_python", lambda: Path("/nonexistent/worker"))
    client = create_app().test_client()
    response = client.get("/api/engines")
    assert response.json["tesseract"]["ready"]
    assert not response.json["paddleocr"]["ready"]
    for name, status in (("paddleocr", 503), ("unknown", 400)):
        response = client.post("/api/ocr", data={"image": (io.BytesIO(image_bytes()), "image.png"), "engine": name})
        assert response.status_code == status
    assert "path" not in str(client.get("/api/engines").json)


def test_paddle_dispatch_applies_geometry(monkeypatch):
    received = []
    monkeypatch.setattr("app.ocr.recognize_paddle", lambda image: received.append(image.size) or "Texte Paddle")
    client = create_app().test_client()
    response = client.post("/api/ocr", data={"image": (io.BytesIO(image_bytes()), "photo.png"), "engine": "paddleocr", "structured": "false", "options": json.dumps({"rotation": 90})})
    assert response.status_code == 200
    assert response.json["text"] == "Texte Paddle"
    assert received == [(240, 1000)]


def create_manifest(root):
    files = {}
    for kind in engine.MODEL_NAMES:
        (root / kind).mkdir()
        for name in ("inference.json", "inference.pdiparams", "inference.yml"):
            relative = f"{kind}/{name}"
            (root / relative).write_bytes(b"synthetic file for integrity test")
            files[relative] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    manifest = {"models": engine.MODEL_NAMES, "files": files, "smoke_test": "passed"}
    (root / "manifest.json").write_text(json.dumps(manifest))
    return manifest


def test_model_integrity_and_tampering(tmp_path):
    assert not engine.models_valid(tmp_path)
    manifest = create_manifest(tmp_path)
    assert engine.models_valid(tmp_path)
    (tmp_path / "det/inference.json").write_bytes(b"tampered")
    assert not engine.models_valid(tmp_path)
    manifest["files"]["../../escape"] = "anything"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    assert not engine.models_valid(tmp_path)


@pytest.mark.parametrize("behavior,expected", [("success", "résultat local"), ("failure", 503), ("invalid", 503), ("timeout", 504)])
def test_subprocess_contract_and_cleanup(tmp_path, monkeypatch, behavior, expected):
    # Test process protocol/cleanup with a deliberately synthetic worker, not OCR accuracy.
    worker = tmp_path / "fake_worker.py"
    worker.write_text("import json, sys, time\nfrom pathlib import Path\n" + {
        "success": "Path(sys.argv[2]).write_text(json.dumps({'text':'résultat local'}), encoding='utf-8')\n",
        "failure": "raise SystemExit(1)\n",
        "invalid": "Path(sys.argv[2]).write_text('invalid')\n",
        "timeout": "time.sleep(10)\n",
    }[behavior], encoding="utf-8")
    monkeypatch.setattr(engine, "status", lambda: {"ready": True})
    monkeypatch.setattr(engine, "worker_python", lambda: Path(sys.executable))
    if behavior == "timeout":
        monkeypatch.setattr(engine, "TIMEOUT", .05)
    original_run = subprocess.run
    seen = []
    def redirected(command, **kwargs):
        seen.append(Path(command[2]).parent)
        command[1] = str(worker)
        return original_run(command, **kwargs)
    monkeypatch.setattr(engine.subprocess, "run", redirected)
    with Image.new("RGB", (30, 30), "white") as image:
        if behavior == "success":
            assert engine.recognize(image) == expected
        else:
            with pytest.raises(engine.PaddleFailure) as error:
                engine.recognize(image)
            assert error.value.status == expected
    assert seen and not seen[0].exists()


def test_archive_extraction_rejects_links(tmp_path, monkeypatch):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as archive:
        entry = tarfile.TarInfo("link"); entry.type = tarfile.SYMTYPE; entry.linkname = "/tmp/escape"
        archive.addfile(entry)
    payload = data.getvalue()
    monkeypatch.setattr(setup_paddle, "urlopen", lambda *args, **kwargs: io.BytesIO(payload))
    with pytest.raises(ValueError, match="Liens"):
        setup_paddle.download_model("synthetic", tmp_path / "model")


def test_archive_layout_and_recorded_digest(tmp_path, monkeypatch):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as archive:
        for name in ("inference.yml", "inference.json", "inference.pdiparams"):
            content = b"synthetic test only"
            entry = tarfile.TarInfo(f"synthetic_infer/{name}"); entry.size = len(content)
            archive.addfile(entry, io.BytesIO(content))
    payload = data.getvalue()
    monkeypatch.setattr(setup_paddle, "urlopen", lambda *args, **kwargs: io.BytesIO(payload))
    record = setup_paddle.download_model("synthetic", tmp_path / "model")
    assert record["archive_sha256"] == hashlib.sha256(payload).hexdigest()
    assert (tmp_path / "model/inference.yml").read_bytes() == b"synthetic test only"


def test_setup_activates_only_after_smoke(tmp_path, monkeypatch):
    monkeypatch.chdir(Path.cwd())  # Restore cwd after main's explicit chdir.
    destination = tmp_path / "paddle"
    monkeypatch.setattr(setup_paddle, "DESTINATION", destination)
    def fake_download(name, path):
        path.mkdir()
        for filename in ("inference.yml", "inference.json", "inference.pdiparams"):
            (path / filename).write_bytes(b"synthetic")
        return {"url": "synthetic fixture", "archive_sha256": "fixture"}
    monkeypatch.setattr(setup_paddle, "download_model", fake_download)
    def fail_smoke(models):
        raise RuntimeError("synthetic smoke failure")
    monkeypatch.setattr(setup_paddle, "smoke_test", fail_smoke)
    with pytest.raises(RuntimeError, match="synthetic"):
        setup_paddle.main()
    assert not destination.exists()
    monkeypatch.setattr(setup_paddle, "smoke_test", lambda models: None)
    setup_paddle.main()
    assert engine.models_valid(destination)
    assert json.loads((destination / "manifest.json").read_text())["zone_smoke_test"] == "passed"
    monkeypatch.setattr(setup_paddle, "smoke_test", fail_smoke)
    with pytest.raises(RuntimeError, match="synthetic"):
        setup_paddle.main()
    assert json.loads((destination / "manifest.json").read_text())["zone_smoke_test"] == "pending"
