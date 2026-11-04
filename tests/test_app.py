import io
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest
from PIL import Image, ImageDraw, ImageFont
import pytesseract

from app import create_app
from app.ocr import MAX_BYTES

FONT_PATH = next((str(path) for path in (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("C:/Windows/Fonts/arial.ttf")) if path.is_file()), None)


@pytest.fixture
def app():
    return create_app({"TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


def image_bytes(content="Bonjour le monde", fmt="PNG", size=(1000, 240)):
    with Image.new("RGB", size, "white") as image:
        if content:
            assert FONT_PATH, "Installez DejaVu Sans ou Arial pour les tests OCR."
            font = ImageFont.truetype(FONT_PATH, 48)
            ImageDraw.Draw(image).text((40, 70), content, font=font, fill="black")
        stream = io.BytesIO()
        image.save(stream, format=fmt)
        return stream.getvalue()


def post(client, data, language="fra"):
    return client.post("/api/ocr", data={"image": (io.BytesIO(data), "image.png"), "language": language, "structured": "false"})


def test_page_and_health(client, monkeypatch):
    page = client.get("/")
    assert page.status_code == 200
    assert b'lang="fr"' in page.data
    assert page.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in page.headers["Content-Security-Policy"]
    monkeypatch.setattr("app.zone_status", lambda: {"ready": True})
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json["ready"] is True
    assert health.json["engine"] == "paddleocr"
    assert health.json["classification"] == "deferred"


@pytest.mark.parametrize("fmt,language,content", [
    ("PNG", "fra", "Bonjour le monde"),
    ("JPEG", "eng", "Read this document"),
    ("PNG", "fra+eng", "Bonjour Hello"),
    ("PNG", "fra", "Une école à côté"),
])
def test_real_ocr(client, fmt, language, content, tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    before = set(Path(tempfile.gettempdir()).glob("tess_*"))
    response = post(client, image_bytes(content, fmt), language)
    assert response.status_code == 200, response.json
    assert content in response.json["text"]
    assert response.json["language"] == language
    assert set(Path(tempfile.gettempdir()).glob("tess_*")) == before


def test_real_timeout_cleans_temporary_files(client, monkeypatch, tmp_path):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    original = pytesseract.image_to_string
    def short_timeout(*args, **kwargs):
        kwargs["timeout"] = 0.000001
        return original(*args, **kwargs)
    monkeypatch.setattr("app.ocr.pytesseract.image_to_string", short_timeout)
    response = post(client, image_bytes())
    assert response.status_code == 504
    assert not list(tmp_path.glob("tess_*"))


def test_blank_image(client):
    response = post(client, image_bytes(""))
    assert response.status_code == 200
    assert response.json["text"] == ""


@pytest.mark.parametrize("data", [b"", b"not an image", b"\x89PNG\r\n\x1a\ninvalid", image_bytes("", "GIF")])
def test_invalid_images(client, data):
    assert post(client, data).status_code == 400


def test_normal_photo_upload_over_parser_buffer(client, monkeypatch):
    stream = io.BytesIO()
    with Image.effect_noise((640, 480), 100).convert("RGB") as photo:
        photo.save(stream, format="JPEG", quality=95)
    data = stream.getvalue()
    assert 100_000 < len(data) < MAX_BYTES
    def recognize(received, language):
        assert received == data
        assert language == "fra"
        return "Texte de la photo"
    monkeypatch.setattr("app.extract", recognize)
    response = post(client, data)
    assert response.status_code == 200
    assert response.json["text"] == "Texte de la photo"


def test_limits_and_language(client):
    assert client.post("/api/ocr").status_code == 400
    assert post(client, image_bytes(), "../../eng").status_code == 400
    assert post(client, b"x" * (MAX_BYTES + 1)).status_code == 413
    assert post(client, b"x" * (MAX_BYTES + 100_000)).status_code == 413
    assert post(client, image_bytes("", size=(5000, 4001))).status_code == 413


def test_same_origin(client):
    image = image_bytes()
    for origin in ["https://evil.example", "http://localhost:9999", "null", "http://[invalid"]:
        response = client.post("/api/ocr", headers={"Origin": origin})
        assert response.status_code == 403
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400
    assert client.get("/", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.get("/", headers={"Origin": "http://localhost"}).status_code == 200


@pytest.mark.parametrize("error,status,code", [
    (RuntimeError("Tesseract process timeout"), 504, "ocr_timeout"),
    (pytesseract.TesseractNotFoundError(), 503, "engine_unavailable"),
    (pytesseract.TesseractError(1, "private document"), 503, "ocr_unavailable"),
    (Exception("private document"), 500, "internal_error"),
])
def test_engine_errors(client, monkeypatch, error, status, code):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr("app.ocr.pytesseract.image_to_string", fail)
    response = post(client, image_bytes())
    assert response.status_code == status
    assert response.json["error"]["code"] == code
    assert b"private document" not in response.data


def test_missing_primary_engine_health(client, monkeypatch):
    monkeypatch.setattr("app.zone_status", lambda: {"ready": False})
    assert client.get("/health").status_code == 503


def test_single_extraction_and_lock_release(app, monkeypatch):
    entered, release = Event(), Event()
    def slow(*args):
        entered.set()
        assert release.wait(5)
        return "done"
    monkeypatch.setattr("app.extract", slow)
    with ThreadPoolExecutor(max_workers=1) as pool:
        job = pool.submit(lambda: post(app.test_client(), b"image"))
        assert entered.wait(5)
        try:
            assert post(app.test_client(), b"image").status_code == 429
        finally:
            release.set()
        assert job.result().status_code == 200
    assert post(app.test_client(), b"image").status_code == 200
