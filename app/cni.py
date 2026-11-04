"""CNI template pipeline: align -> fixed value crops -> recognition -> validation.

This is not an old/new-card classifier and does not train an OCR model.
The only profile is provisional, based on the front layout supplied by the user.
"""
import io
import json
import hashlib
from pathlib import Path
import warnings

import cv2
import numpy as np
from PIL import Image, ImageOps

from .fields import FIELDS, _typed_value, selected_text
from .ocr import MAX_BYTES, MAX_PIXELS, OCRError
from .paddle_engine import PaddleFailure, recognize_zones

PROFILE_ID = "cni_puce_recto_v1"
PROFILES = json.loads(Path(__file__).with_name("cni_templates.json").read_text(encoding="utf-8"))
PROFILE = PROFILES[PROFILE_ID]
WIDTH, HEIGHT = PROFILE["reference_size"]


def decode_image(data):
    if not data or len(data) > MAX_BYTES:
        raise OCRError("invalid_size", "Chaque photo doit être non vide et ne pas dépasser 10 Mio.", 413 if data else 400)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in {"PNG", "JPEG"}:
                    raise OCRError("invalid_image", "Choisissez une photo PNG ou JPEG.")
                if source.width * source.height > MAX_PIXELS:
                    raise OCRError("too_many_pixels", "La photo dépasse 20 millions de pixels.", 413)
                source.verify()
            with Image.open(io.BytesIO(data)) as source:
                with ImageOps.exif_transpose(source) as oriented:
                    with oriented.convert("RGBA") as rgba:
                        result = Image.new("RGB", rgba.size, "white")
                        result.paste(rgba, mask=rgba.getchannel("A"))
                        return result
    except OCRError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise OCRError("too_many_pixels", "La photo est trop grande.", 413) from None
    except (OSError, ValueError, SyntaxError):
        raise OCRError("invalid_image", "Impossible de lire cette photo. Essayez un autre fichier.") from None


def _ordered_quad(points):
    points = np.array(points, np.float32).reshape(4, 2)
    center = points.mean(axis=0)
    points = points[np.argsort(np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0]))]
    points = np.roll(points, -int(np.argmin(points.sum(axis=1))), axis=0)
    # Make the longest edge horizontal. The remaining 180° orientation is
    # explicitly confirmed using the preview, never guessed from identity data.
    if np.linalg.norm(points[1] - points[0]) < np.linalg.norm(points[2] - points[1]):
        points = np.roll(points, -1, axis=0)
    return points


def align_card(image):
    if min(image.size) < 180:
        raise OCRError("image_too_small", "La photo est trop petite. Reprenez la carte de plus près.")
    scale = min(1, 1400 / max(image.size))
    with image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale)))) as reduced:
        array = np.array(reduced)
    gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 40, 120)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    hsv = cv2.cvtColor(array, cv2.COLOR_RGB2HSV)
    colored = cv2.inRange(hsv, np.array([0, 25, 25]), np.array([179, 255, 255]))
    colored = cv2.morphologyEx(colored, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    candidates = []
    total = array.shape[0] * array.shape[1]
    for mask in (edges, colored):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:12]:
            hull = cv2.convexHull(contour)
            for precision in (.015, .025, .04):
                quad = cv2.approxPolyDP(hull, precision * cv2.arcLength(hull, True), True)
                if len(quad) != 4 or not cv2.isContourConvex(quad):
                    continue
                area = cv2.contourArea(quad)
                if area < total * .20:
                    continue
                points = _ordered_quad(quad)
                top = max(np.linalg.norm(points[1] - points[0]), np.linalg.norm(points[2] - points[3]))
                side = max(np.linalg.norm(points[3] - points[0]), np.linalg.norm(points[2] - points[1]))
                if 1.30 <= top / max(1, side) <= 1.95:
                    candidates.append((area, points))
                    break
    if candidates:
        points = max(candidates, key=lambda item: item[0])[1] / scale
        method = "contour"
    elif abs(max(image.size) / min(image.size) - WIDTH / HEIGHT) < .065:
        points = _ordered_quad([[0, 0], [image.width - 1, 0], [image.width - 1, image.height - 1], [0, image.height - 1]])
        method = "image_cadree"
    else:
        raise OCRError("alignment_failed", "Les contours de la carte ne sont pas assez nets. Reprenez la photo sur un fond uni, avec les quatre coins visibles.")
    destination = np.float32([[0, 0], [WIDTH - 1, 0], [WIDTH - 1, HEIGHT - 1], [0, HEIGHT - 1]])
    transform = cv2.getPerspectiveTransform(points.astype(np.float32), destination)
    aligned = cv2.warpPerspective(np.array(image), transform, (WIDTH, HEIGHT), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    return Image.fromarray(aligned), {"method": method, "orientation_confirmed": False, "size": [WIDTH, HEIGHT]}


def crop_zones(image):
    crops = {}
    for key, (left, top, right, bottom) in PROFILE["zones"].items():
        crop = image.crop((round(left * image.width), round(top * image.height), round(right * image.width), round(bottom * image.height)))
        # Value crops only: no label searching and no whole-card detection.
        # Preserve colors/accents; add a white margin without aggressive binarization.
        padded = ImageOps.expand(crop, border=8, fill="white")
        crop.close()
        crops[key] = padded
    return crops


def validate_zone_values(values):
    fields = {}
    for key, (label, _) in FIELDS.items():
        item = values.get(key, {})
        value = item.get("text", "").strip()
        confidence = item.get("score")
        field = {"label": label, "value": value, "normalized": None,
                 "status": "non_trouve", "message": "Aucune valeur lisible dans cette zone.",
                 "zone": PROFILE["zones"][key], "side": "recto", "evidence": []}
        if value:
            normalized, warning = _typed_value(key, value)
            # Strings with digits in names or an implausible multiline reading
            # remain visible but never become silently accepted identity data.
            if key in {"nom", "prenoms"} and any(c.isdigit() for c in value):
                warning = "Des chiffres ont été lus dans ce champ : vérifiez sur la carte."
            if confidence is None or confidence < .70:
                warning = warning or "Lecture incertaine : vérifiez cette zone sur la carte."
            field.update(normalized=normalized, status="a_verifier" if warning else "propose",
                         message=warning or "Valeur proposée dans la zone prédéfinie, à relire.")
        fields[key] = field
    return fields


def read_cni(front_data, back_data):
    # Both images were aligned and orientation-confirmed in the wizard. Require
    # the canonical dimensions rather than silently stretching an arbitrary photo.
    if front_data and back_data and hashlib.sha256(front_data).digest() == hashlib.sha256(back_data).digest():
        raise OCRError("duplicate_sides", "La même photo a été ajoutée deux fois. Ajoutez l’autre face de la carte au verso.")
    with decode_image(front_data) as front, decode_image(back_data) as back:
        if front.size != (WIDTH, HEIGHT) or back.size != (WIDTH, HEIGHT):
            raise OCRError("alignment_required", "Reprenez les étapes recto et verso pour aligner les photos.")
        crops = crop_zones(front)
        try:
            values = recognize_zones(crops)
        except PaddleFailure as error:
            raise OCRError("paddle_unavailable" if error.status == 503 else "paddle_timeout", str(error), error.status) from None
        finally:
            for crop in crops.values():
                crop.close()
    fields = validate_zone_values(values)
    return {"engine": "paddleocr", "profile": PROFILE_ID, "profile_status": PROFILE["status"],
            "fields": fields, "text": selected_text(fields),
            "notices": ["Gabarit provisoire du recto illustré : vérifiez chaque champ.",
                        "Classification ancien/nouveau différée.",
                        "Verso reçu, sans lecture automatique : ses zones ne sont pas encore définies."]}
