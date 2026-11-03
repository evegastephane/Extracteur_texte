import io
import json

import cv2
import numpy as np
import pytest
from PIL import Image

from app import create_app
from app.ocr import extract
from app.preprocess import LIMIT, bounded_resize, prepare
from test_app import FONT_PATH, image_bytes


def request_options(options):
    return create_app({"TESTING": True}).test_client().post("/api/ocr", data={
        "image": (io.BytesIO(image_bytes()), "photo.png"),
        "language": "fra", "options": json.dumps(options),
    })


@pytest.mark.parametrize("options", [[], None, {"rotation": 45}, {"rotation": True}, {"mode": "invented"},
    {"mode": []}, {"layout": "--anything"}, {"deskew": "yes"}, {"unknown": 1},
    {"corners": [[0, 0], [1, 1], [1, 0], [0, 1]]},
    {"corners": [[0, 0], [1, 0], [1, 2], [0, 1]]},
    {"corners": [[0, 0]] * 4}, {"corners": [[0, 0], [1, 0], [1, float("nan")], [0, 1]]},
])
def test_invalid_options(options):
    assert request_options(options).status_code == 400


def test_malformed_options():
    response = create_app().test_client().post("/api/ocr", data={
        "image": (io.BytesIO(image_bytes()), "photo.png"), "options": "{oops",
    })
    assert response.status_code == 400


@pytest.mark.parametrize("mode", ["original", "contrast", "threshold"])
def test_modes_real_ocr(mode):
    assert "Bonjour le monde" in extract(image_bytes(), "fra", {"mode": mode, "layout": "block"})


def test_rotation_real_ocr():
    with Image.open(io.BytesIO(image_bytes())) as source:
        with source.rotate(90, expand=True) as rotated:
            output = io.BytesIO(); rotated.save(output, format="PNG")
    assert "Bonjour le monde" in extract(output.getvalue(), "fra", {"rotation": 90, "layout": "block"})


def test_crop_excludes_other_text():
    # Put a second unrelated line below the desired region.
    from PIL import ImageDraw, ImageFont
    with Image.open(io.BytesIO(image_bytes(size=(1000, 500)))) as source:
        ImageDraw.Draw(source).text((40, 330), "Ne pas extraire", fill="black",
            font=ImageFont.truetype(FONT_PATH, 40))
        output = io.BytesIO(); source.save(output, format="PNG")
    result = extract(output.getvalue(), "fra", {"corners": [[0, 0], [1, 0], [1, .45], [0, .45]], "layout": "block"})
    assert "Bonjour le monde" in result
    assert "extraire" not in result


def test_perspective_geometry():
    # Four distinct corner colors must remain in their respective quadrants.
    array = np.full((200, 300, 3), 255, np.uint8)
    array[:100, :150] = (255, 0, 0); array[:100, 150:] = (0, 255, 0)
    array[100:, 150:] = (0, 0, 255); array[100:, :150] = (255, 255, 0)
    corners = np.float32([[80, 50], [430, 80], [400, 340], [40, 310]])
    matrix = cv2.getPerspectiveTransform(np.float32([[0, 0], [299, 0], [299, 199], [0, 199]]), corners)
    warped = cv2.warpPerspective(array, matrix, (500, 400))
    with Image.fromarray(warped) as source:
        with prepare(source, {"corners": (corners / [499, 399]).tolist()}) as corrected:
            recovered = np.array(corrected)
    height, width = recovered.shape[:2]
    assert tuple(recovered[height // 4, width // 4]) == (255, 0, 0)
    assert tuple(recovered[height // 4, 3 * width // 4]) == (0, 255, 0)
    assert tuple(recovered[3 * height // 4, 3 * width // 4]) == (0, 0, 255)
    assert tuple(recovered[3 * height // 4, width // 4]) == (255, 255, 0)


def test_small_selection_rejected():
    response = request_options({"corners": [[0, 0], [.01, 0], [.01, .02], [0, .02]]})
    assert response.status_code == 400


def test_deskew_reduces_line_angle():
    array = np.full((300, 700, 3), 255, np.uint8)
    for y in range(60, 250, 40):
        cv2.line(array, (40, y), (650, y + 42), (0, 0, 0), 2)
    with Image.fromarray(array) as source:
        with prepare(source, {"deskew": True}) as corrected:
            gray = cv2.cvtColor(np.array(corrected), cv2.COLOR_RGB2GRAY)
    lines = cv2.HoughLinesP(cv2.Canny(gray, 50, 150), 1, np.pi / 180, 80, minLineLength=400, maxLineGap=15)
    assert lines is not None
    slopes = [abs(float(y2 - y1) / max(1, x2 - x1)) for x1, y1, x2, y2 in lines[:, 0]]
    assert np.median(slopes) < .02


def test_original_does_not_change_pixels():
    with Image.open(io.BytesIO(image_bytes())) as source:
        with prepare(source, {}) as result:
            assert np.array_equal(np.array(source), np.array(result))


def test_extreme_aspect_ratio_is_bounded():
    array = np.zeros((1, 100_000, 3), np.uint8)
    resized = bounded_resize(array)
    assert max(resized.shape[:2]) <= 8000
    assert resized.shape[0] * resized.shape[1] <= LIMIT
