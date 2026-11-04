import base64
import io
import json
from pathlib import Path
import sys
import subprocess
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont
import pytesseract

from app import create_app
from app import cni
from app import paddle_engine, paddle_worker
from test_app import FONT_PATH

VALUES = {"nom": "MARTIN", "prenoms": "ALICE MARIE", "date_naissance": "17.12.2000",
          "lieu_naissance": "VILLE DEMO", "sexe": "F", "taille": "1,77", "profession": "TECHNICIENNE"}


def synthetic_front():
    image = Image.new("RGB", (cni.WIDTH, cni.HEIGHT), "#f7f8ef")
    draw = ImageDraw.Draw(image)
    draw.rectangle((4, 4, cni.WIDTH - 5, cni.HEIGHT - 5), outline="#386849", width=8)
    font = ImageFont.truetype(FONT_PATH, 36)
    small = ImageFont.truetype(FONT_PATH, 20)
    draw.text((400, 70), "DOCUMENT SYNTHETIQUE", font=font, fill="black")
    draw.rectangle((1070, 290, 1520, 900), fill="#b9c7b9")
    draw.text((1100, 550), "PHOTO FICTIVE", font=small, fill="black")
    for key, zone in cni.PROFILE["zones"].items():
        x, y = round(zone[0] * image.width), round(zone[1] * image.height)
        draw.text((x + 8, y - 25), key.upper(), font=small, fill="#386849")
        draw.text((x + 8, y + 1), VALUES[key], font=font, fill="black")
    return image


def synthetic_back():
    image = Image.new("RGB", (cni.WIDTH, cni.HEIGHT), "#e5e9dc")
    ImageDraw.Draw(image).text((100, 100), "VERSO SYNTHETIQUE — aucune zone configuree", fill="black", font=ImageFont.truetype(FONT_PATH, 30))
    return image


def png(image):
    stream = io.BytesIO(); image.save(stream, format="PNG"); return stream.getvalue()


def test_template_has_seven_value_only_regions():
    assert set(cni.PROFILE["zones"]) == set(VALUES)
    for key, (left, top, right, bottom) in cni.PROFILE["zones"].items():
        assert 0 <= left < right < .66  # Portrait never sent to OCR.
        assert 0 < top < bottom < .8  # Signature excluded.
        assert bottom - top < .08


def test_back_regions_reference_only_no_extra_output(monkeypatch):
    back_profile = cni.PROFILE["back"]
    assert back_profile["status"] == "provisional"
    assert back_profile["ocr_enabled"] is False
    assert {"pere", "mere", "adresse", "date_delivrance", "date_expiration", "numero_carte"}.issubset(back_profile["regions"])
    for left, top, right, bottom in back_profile["regions"].values():
        assert 0 <= left < right <= 1 and 0 <= top < bottom <= 1
    def recognize_only_front(crops):
        assert set(crops) == set(VALUES)
        return {key: {"text": value, "score": .99} for key, value in VALUES.items()}
    monkeypatch.setattr(cni, "recognize_zones", recognize_only_front)
    with synthetic_front() as front, synthetic_back() as back:
        ImageDraw.Draw(back).text((100, 200), "PRIVATE_BACK_MARKER", fill="black")
        result = cni.read_cni(png(front), png(back))
    assert set(result["fields"]) == set(VALUES)
    assert "PRIVATE_BACK_MARKER" not in json.dumps(result)
    assert result["verso"] == {"zones_referenced": True, "ocr": False}


def test_align_perspective_and_crop_values():
    with synthetic_front() as front:
        quad = np.float32([[170, 240], [1850, 120], [1730, 1240], [220, 1320]])
        matrix = cv2.getPerspectiveTransform(np.float32([[0, 0], [1599, 0], [1599, 999], [0, 999]]), quad)
        photo = cv2.warpPerspective(np.array(front), matrix, (2000, 1500), borderValue=(80, 80, 80))
    with Image.fromarray(photo) as image:
        aligned, meta = cni.align_card(image)
    with aligned:
        assert aligned.size == (1600, 1000)
        assert meta["method"] == "contour"
        crops = cni.crop_zones(aligned)
        try:
            # Actual OCR proves the alignment + fixed crop positions on a known
            # synthetic layout. It does NOT validate Paddle model accuracy.
            assert "MARTIN" in pytesseract.image_to_string(crops["nom"], lang="fra+eng", config="--psm 7")
            assert "TECHNICIENNE" in pytesseract.image_to_string(crops["profession"], lang="fra+eng", config="--psm 7")
        finally:
            for crop in crops.values(): crop.close()


def test_alignment_handles_portrait_and_rejects_unusable():
    with synthetic_front() as source:
        with source.rotate(90, expand=True) as portrait:
            aligned, _ = cni.align_card(portrait)
            assert aligned.size == (1600, 1000)
            aligned.close()
    with Image.new("RGB", (1000, 1000), "white") as blank:
        with pytest.raises(cni.OCRError, match="contours"):
            cni.align_card(blank)
    with Image.new("RGB", (100, 60), "white") as tiny:
        with pytest.raises(cni.OCRError, match="petite"):
            cni.align_card(tiny)


def test_cni_pipeline_actual_crops_with_explicit_tesseract_substitute(monkeypatch):
    def recognize_crops(crops):
        assert set(crops) == set(VALUES)
        return {key: {"text": pytesseract.image_to_string(image, lang="fra+eng", config="--psm 7").strip(), "score": .99} for key, image in crops.items()}
    monkeypatch.setattr(cni, "recognize_zones", recognize_crops)
    with synthetic_front() as front, synthetic_back() as back:
        result = cni.read_cni(png(front), png(back))
    assert result["engine"] == "paddleocr"  # Production route remains Paddle; test callback above is explicit.
    assert {key: field["value"] for key, field in result["fields"].items()} == VALUES
    assert result["fields"]["date_naissance"]["normalized"] == "2000-12-17"
    assert result["profile_status"] == "provisional"
    assert any("Verso" in notice for notice in result["notices"])
    assert "PHOTO FICTIVE" not in json.dumps(result)


def test_validation_warns_and_never_fabricates():
    fields = cni.validate_zone_values({"nom": {"text": "MART1N", "score": .95},
        "date_naissance": {"text": "31.02.2000", "score": .95}, "profession": {"text": "TECHNICIENNE", "score": .3}})
    assert fields["nom"]["status"] == "a_verifier"
    assert fields["date_naissance"]["normalized"] is None
    assert fields["profession"]["status"] == "a_verifier"
    assert fields["taille"]["value"] == "" and fields["taille"]["status"] == "non_trouve"


def test_cni_api_alignment_and_missing_sides():
    client = create_app().test_client()
    with synthetic_front() as image:
        response = client.post("/api/cni/align", data={"image": (io.BytesIO(png(image)), "photo.png")})
    assert response.status_code == 200
    with Image.open(io.BytesIO(base64.b64decode(response.json["image"]))) as aligned:
        assert aligned.size == (1600, 1000)
    assert response.headers["Cache-Control"] == "no-store"
    assert client.post("/api/cni/read").status_code == 400
    assert client.post("/api/cni/align", data={"image": (io.BytesIO(b"bad"), "photo.png")}).status_code == 400
    assert client.get("/api/cni/status").json["classification"] == "deferred"


def test_duplicate_and_unaligned_sides_rejected():
    with synthetic_front() as front:
        data = png(front)
    with pytest.raises(cni.OCRError, match="même photo"):
        cni.read_cni(data, data)
    with Image.new("RGB", (800, 500), "white") as front, synthetic_back() as back:
        with pytest.raises(cni.OCRError, match="aligner"):
            cni.read_cni(png(front), png(back))


def test_zone_worker_loads_recognition_once(monkeypatch, tmp_path):
    jobs = [{"field": key, "path": str(tmp_path / f"{key}.png")} for key in VALUES]
    job_file = tmp_path / "jobs.json"; job_file.write_text(json.dumps(jobs))
    calls = []
    class FakeRecognition:
        def __init__(self, **kwargs): calls.append(("init", kwargs))
        def predict(self, input, batch_size):
            calls.append(("predict", input))
            return [{"rec_text": VALUES[Path(input).stem], "rec_score": .98}]
        def close(self): calls.append(("close",))
    monkeypatch.setitem(sys.modules, "paddleocr", SimpleNamespace(TextRecognition=FakeRecognition))
    monkeypatch.setattr(sys, "argv", ["worker.py", "unused.png", str(tmp_path / "out.json"), str(tmp_path / "models"), str(job_file)])
    paddle_worker.main()
    payload = json.loads((tmp_path / "out.json").read_text())
    assert {key: value["text"] for key, value in payload["zones"].items()} == VALUES
    assert [call[0] for call in calls].count("init") == 1
    assert [call[0] for call in calls].count("predict") == 7
    assert calls[0][1]["model_name"] == "latin_PP-OCRv5_mobile_rec"


def test_zone_api_missing_paddle_is_explicit(monkeypatch):
    monkeypatch.setattr(paddle_engine, "zone_status", lambda: {"ready": False})
    client = create_app().test_client()
    with synthetic_front() as front, synthetic_back() as back:
        response = client.post("/api/cni/read", data={"recto": (io.BytesIO(png(front)), "recto.png"), "verso": (io.BytesIO(png(back)), "verso.png")})
    assert response.status_code == 503
    assert response.json["error"]["code"] == "paddle_unavailable"
    monkeypatch.setattr(cni, "recognize_zones", lambda crops: {key: {"text": text, "score": .95} for key, text in VALUES.items()})
    with synthetic_front() as front, synthetic_back() as back:
        recovered = client.post("/api/cni/read", data={"recto": (io.BytesIO(png(front)), "recto.png"), "verso": (io.BytesIO(png(back)), "verso.png")})
    assert recovered.status_code == 200  # Lock released after the earlier failure.


@pytest.mark.parametrize("behavior", ["success", "timeout", "bad_score", "missing"])
def test_zone_process_protocol_and_cleanup(tmp_path, monkeypatch, behavior):
    worker = tmp_path / "synthetic_worker.py"
    payload = {key: {"text": text, "score": .95} for key, text in VALUES.items()}
    if behavior == "bad_score": payload["nom"]["score"] = 1.5
    if behavior == "missing": payload.pop("sexe")
    code = "import sys,json,time\nfrom pathlib import Path\n"
    code += "time.sleep(10)\n" if behavior == "timeout" else f"Path(sys.argv[2]).write_text({json.dumps(json.dumps({'zones': payload}))},encoding='utf-8')\n"
    worker.write_text(code, encoding="utf-8")
    monkeypatch.setattr(paddle_engine, "zone_status", lambda: {"ready": True})
    monkeypatch.setattr(paddle_engine, "worker_python", lambda: Path(sys.executable))
    if behavior == "timeout": monkeypatch.setattr(paddle_engine, "TIMEOUT", .05)
    original_run, directories = subprocess.run, []
    def run(command, **kwargs):
        directories.append(Path(command[2]).parent)
        jobs = json.loads(Path(command[5]).read_text())
        assert {job["field"] for job in jobs} == set(VALUES)
        assert all(Path(job["path"]).is_file() for job in jobs)
        command[1] = str(worker)
        return original_run(command, **kwargs)
    monkeypatch.setattr(paddle_engine.subprocess, "run", run)
    with synthetic_front() as front:
        crops = cni.crop_zones(front)
        try:
            if behavior == "success": assert paddle_engine.recognize_zones(crops) == payload
            else:
                with pytest.raises(paddle_engine.PaddleFailure) as error:
                    paddle_engine.recognize_zones(crops)
                assert error.value.status == (504 if behavior == "timeout" else 503)
        finally:
            for crop in crops.values(): crop.close()
    assert directories and not directories[0].exists()


@pytest.mark.skipif(not paddle_engine.zone_status()["ready"], reason="PaddleOCR par zones non préparé : reconnaissance réelle non exécutée")
def test_real_paddle_cni_when_prepared():
    with synthetic_front() as front, synthetic_back() as back:
        result = cni.read_cni(png(front), png(back))
    assert "MARTIN" in result["fields"]["nom"]["value"]
