"""Reproducible synthetic OCR comparison; no personal documents are used.

Run from repository root: python -m scripts.benchmark --output docs/benchmark-results.json
Geometry corrections below are known manual selections, NOT automatic detection.
"""
import argparse
import io
import json
from pathlib import Path
import time
import unicodedata
import platform
import pytesseract

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.ocr import extract

REFERENCE = "Bonjour le monde\nUne école à côté\nDocument de démonstration"


def character_error(reference, actual):
    reference = unicodedata.normalize("NFC", reference.replace("\r\n", "\n")).strip()
    actual = unicodedata.normalize("NFC", actual.replace("\r\n", "\n")).strip()
    row = list(range(len(actual) + 1))
    for i, left in enumerate(reference, 1):
        new = [i]
        for j, right in enumerate(actual, 1):
            new.append(min(new[-1] + 1, row[j] + 1, row[j - 1] + (left != right)))
        row = new
    return row[-1] / max(1, len(reference))


def samples():
    # Use a Windows font when DejaVu is not installed.
    fonts = [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("C:/Windows/Fonts/arial.ttf")]
    font_path = next((font for font in fonts if font.is_file()), None)
    if font_path is None:
        raise SystemExit("Installez DejaVu Sans ou Arial pour générer les exemples.")
    font = ImageFont.truetype(str(font_path), 38)
    page = Image.new("RGB", (1000, 380), "white")
    ImageDraw.Draw(page).multiline_text((50, 70), REFERENCE, font=font, fill="black", spacing=25)
    yield "texte_net", page, {"layout": "block"}
    yield "rotation_180", page.rotate(180), {"rotation": 180, "layout": "block"}
    yield "inclinaison_6", page.rotate(6, expand=True, fillcolor="white"), {"deskew": True, "layout": "block"}
    gray = page.convert("L").point(lambda value: 130 + round(value / 255 * 40)).convert("RGB")
    yield "faible_contraste", gray, {"mode": "contrast", "layout": "block"}
    corners = np.float32([[150, 120], [1120, 260], [1000, 780], [280, 680]])
    matrix = cv2.getPerspectiveTransform(np.float32([[0, 0], [999, 0], [999, 379], [0, 379]]), corners)
    warped = cv2.warpPerspective(np.array(page), matrix, (1300, 900), borderValue=(100, 100, 100))
    yield "perspective", Image.fromarray(warped), {"corners": (corners / [1299, 899]).tolist(), "mode": "contrast", "layout": "block"}
    background = Image.new("RGB", (1600, 1200), "white")
    ImageDraw.Draw(background).text((50, 40), "Texte du fond à ignorer", font=font, fill="black")
    background.paste(page, (300, 400))
    yield "zone_sur_fond", background, {"corners": [[300 / 1599, 400 / 1199], [1299 / 1599, 400 / 1199], [1299 / 1599, 779 / 1199], [300 / 1599, 779 / 1199]], "layout": "block"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".test-artifacts/benchmark.json"))
    args = parser.parse_args()
    results = []
    for name, image, options in samples():
        with image:
            stream = io.BytesIO(); image.save(stream, format="PNG")
        record = {"sample": name, "reference": REFERENCE, "options": options}
        for label, settings in (("baseline", {}), ("prepared", options)):
            start = time.perf_counter()
            actual = extract(stream.getvalue(), "fra", settings)
            record[label] = {"text": actual, "cer": round(character_error(REFERENCE, actual), 4), "seconds": round(time.perf_counter() - start, 3)}
        results.append(record)
        print(f"{name}: CER {record['baseline']['cer']:.1%} -> {record['prepared']['cer']:.1%}")
    summary = {"kind": "synthetic", "environment": {"python": platform.python_version(), "tesseract": str(pytesseract.get_tesseract_version()), "opencv": cv2.__version__, "numpy": np.__version__}, "note": "Known manual geometry corrections; results are not a claim about real identity cards. Font and Tesseract versions affect scores.",
        "samples": results, "mean_cer": {label: round(sum(item[label]["cer"] for item in results) / len(results), 4) for label in ("baseline", "prepared")}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
