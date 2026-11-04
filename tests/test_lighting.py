import base64
import io

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance
import pytesseract

from app import create_app
from app import cni
from app.lighting import auto_lighten
from test_cni import synthetic_front, synthetic_back, png, VALUES


def test_well_lit_photo_is_pixel_identical_and_source_unchanged():
    with synthetic_front() as image:
        original = np.array(image)
        output, status = auto_lighten(image)
        with output:
            assert status["applied"] is False
            assert np.array_equal(np.array(output), original)
            assert np.array_equal(np.array(image), original)


def test_dark_photo_lifts_paper_preserves_text_and_highlights():
    with Image.new("RGB", (800, 500), (65, 65, 65)) as image:
        draw = ImageDraw.Draw(image)
        draw.rectangle((250, 180, 300, 210), fill="black")
        draw.rectangle((350, 180, 370, 210), fill="white")
        original = np.array(image)
        output, status = auto_lighten(image)
        with output:
            result = np.array(output)
            assert status["applied"] and status["global"]
            assert result[100, 250].mean() > original[100, 250].mean() + 30
            assert np.all(result[190, 260] == 0)
            assert np.all(result[190, 360] == 255)
            assert result[100, 250].mean() < 240
            assert np.array_equal(np.array(image), original)


def test_local_shadow_lift_does_not_burn_bright_half():
    array = np.full((500, 800, 3), 230, np.uint8)
    array[:, :355] = 80
    with Image.fromarray(array) as image:
        output, status = auto_lighten(image)
        with output:
            result = np.array(output)
            assert status["shadows"] and not status["global"]
            assert result[250, 250].mean() > 110
            assert abs(result[250, 500].mean() - 230) <= 1
            assert result[250, 500].max() < 255


def test_nearly_black_photo_warns_without_inventing_details():
    with Image.new("RGB", (800, 500), "black") as image:
        output, status = auto_lighten(image)
        with output:
            assert status["warning"]
            assert not status["applied"]
            assert not np.any(np.array(output))


def test_dark_card_upload_returns_visible_corrected_preview():
    with synthetic_front() as image:
        with ImageEnhance.Brightness(image).enhance(.25) as dark:
            raw = png(dark)
            before = np.array(dark)[180:780, 400:1000].mean()
    response = create_app().test_client().post("/api/cni/align", data={"image": (io.BytesIO(raw), "dark.png")})
    assert response.status_code == 200
    assert response.json["alignment"]["lighting"]["applied"]
    with Image.open(io.BytesIO(base64.b64decode(response.json["image"]))) as preview:
        assert preview.size == (1600, 1000)
        assert np.array(preview)[180:780, 400:1000].mean() > before + 30


def test_ocr_receives_the_same_lightened_preview_without_second_correction(monkeypatch):
    with synthetic_front() as image:
        with ImageEnhance.Brightness(image).enhance(.25) as dark:
            response = create_app().test_client().post("/api/cni/align", data={"image": (io.BytesIO(png(dark)), "dark.png")})
    preview_bytes = base64.b64decode(response.json["image"])
    with Image.open(io.BytesIO(preview_bytes)) as preview:
        expected = cni.crop_zones(preview)
    def recognize(crops):
        # Real Tesseract checks the corrected synthetic strokes; Paddle itself
        # is substituted here and is not claimed as a measured accuracy gain.
        for key in crops:
            assert np.array_equal(np.array(crops[key]), np.array(expected[key]))
        assert "MARTIN" in pytesseract.image_to_string(crops["nom"], lang="fra+eng", config="--psm 7")
        assert "TECHNICIENNE" in pytesseract.image_to_string(crops["profession"], lang="fra+eng", config="--psm 7")
        return {key: {"text": text, "score": .99} for key, text in VALUES.items()}
    monkeypatch.setattr(cni, "recognize_zones", recognize)
    try:
        with synthetic_back() as back:
            result = cni.read_cni(preview_bytes, png(back))
        assert result["fields"]["nom"]["value"] == "MARTIN"
    finally:
        for crop in expected.values(): crop.close()
