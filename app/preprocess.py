"""Local, bounded image preparation. Coordinates refer to the rotated image."""
import math

import cv2
import numpy as np
from PIL import Image

MODES = {"original", "contrast", "threshold"}
LAYOUTS = {"auto": 3, "block": 6, "sparse": 11, "line": 7}
LIMIT = 8_000_000  # Bound intermediate OpenCV arrays, independently of upload size.
cv2.setNumThreads(1)


def validate_options(options):
    if not isinstance(options, dict) or set(options) - {"rotation", "corners", "mode", "layout", "deskew"}:
        raise ValueError("Réglages d’image invalides.")
    result = {"rotation": 0, "corners": None, "mode": "original", "layout": "auto", "deskew": False, **options}
    if type(result["rotation"]) is not int or result["rotation"] not in (0, 90, 180, 270):
        raise ValueError("Rotation invalide.")
    if result["mode"] not in MODES or result["layout"] not in LAYOUTS or type(result["deskew"]) is not bool:
        raise ValueError("Choisissez les réglages proposés.")
    corners = result["corners"]
    if corners is not None:
        if not isinstance(corners, list) or len(corners) != 4:
            raise ValueError("Sélectionnez les quatre coins dans l’ordre.")
        for point in corners:
            if not isinstance(point, list) or len(point) != 2 or any(type(v) not in (float, int) or not math.isfinite(v) or not 0 <= v <= 1 for v in point):
                raise ValueError("Les coins doivent rester dans l’image.")
        points = np.array(corners, dtype=np.float32)
        if not cv2.isContourConvex(points) or cv2.contourArea(points, oriented=True) < 0.0001:
            raise ValueError("Les coins doivent former une zone convexe, dans le sens horaire.")
    return result


def bounded_resize(image, target=None):
    height, width = image.shape[:2]
    scale = min(1.0, math.sqrt(LIMIT / (width * height)), 8000 / max(width, height))
    if target is not None:
        scale = min(target / max(width, height), 2.0, math.sqrt(LIMIT / (width * height)), 8000 / max(width, height))
    if abs(scale - 1) < 0.001:
        return image
    return cv2.resize(image, (max(1, round(width * scale)), max(1, round(height * scale))),
                      interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)


def prepare(image, options):
    """Return a new PIL image; original bypasses tonal filters, never replaces input."""
    options = validate_options(options)
    with image.rotate(-options["rotation"], expand=True) as rotated:
        array = bounded_resize(np.array(rotated))
    if options["corners"] is not None:
        height, width = array.shape[:2]
        points = np.array(options["corners"], np.float32) * [width - 1, height - 1]
        top_left, top_right, bottom_right, bottom_left = points
        out_width = round(max(np.linalg.norm(top_right - top_left), np.linalg.norm(bottom_right - bottom_left)))
        out_height = round(max(np.linalg.norm(bottom_left - top_left), np.linalg.norm(bottom_right - top_right)))
        if min(out_width, out_height) < 8:
            raise ValueError("La zone sélectionnée est trop petite.")
        scale = min(1, math.sqrt(LIMIT / (out_width * out_height)))
        out_width, out_height = max(8, round(out_width * scale)), max(8, round(out_height * scale))
        destination = np.float32([[0, 0], [out_width - 1, 0], [out_width - 1, out_height - 1], [0, out_height - 1]])
        matrix = cv2.getPerspectiveTransform(points.astype(np.float32), destination)
        array = cv2.warpPerspective(array, matrix, (out_width, out_height), borderValue=(255, 255, 255))
    if options["mode"] != "original":
        array = bounded_resize(array, target=2200)
        gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
        gray = cv2.fastNlMeansDenoising(gray, None, h=7, templateWindowSize=7, searchWindowSize=15)
        array = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        if options["mode"] == "threshold":
            array = cv2.adaptiveThreshold(array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
    if options["deskew"]:
        gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY) if array.ndim == 3 else array
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 80, minLineLength=max(30, gray.shape[1] // 10), maxLineGap=15)
        angles = []
        if lines is not None:
            for x1, y1, x2, y2 in lines[:, 0]:
                angle = math.degrees(math.atan2(float(y2 - y1), float(x2 - x1)))
                if abs(angle) <= 12:
                    angles.append(angle)
        if angles:
            angle = float(np.median(angles))
            height, width = array.shape[:2]
            matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
            # Expand the canvas so deskew does not cut off document edges.
            cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
            new_width, new_height = math.ceil(height * sin + width * cos), math.ceil(height * cos + width * sin)
            matrix[0, 2] += (new_width - width) / 2
            matrix[1, 2] += (new_height - height) / 2
            scale = min(1, math.sqrt(LIMIT / (new_width * new_height)), 8000 / max(new_width, new_height))
            matrix *= scale
            new_width, new_height = max(1, round(new_width * scale)), max(1, round(new_height * scale))
            array = cv2.warpAffine(array, matrix, (new_width, new_height), borderValue=255 if array.ndim == 2 else (255, 255, 255))
    return Image.fromarray(bounded_resize(array))
