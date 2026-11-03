"""Bounded local image decoding and OCR. No document is persisted."""

import io
import os
import shutil
from pathlib import Path
import subprocess
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
import pytesseract
from .preprocess import LAYOUTS, prepare, validate_options

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000
LANGUAGES = {"fra", "eng", "fra+eng"}
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

# setup.sh installs versioned language data here without requiring root.
LOCAL_DATA = Path(__file__).resolve().parent.parent / ".ocr-data"
if LOCAL_DATA.is_dir():
    os.environ.setdefault("TESSDATA_PREFIX", str(LOCAL_DATA))
if os.name == "nt" and not shutil.which("tesseract"):
    windows_engine = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Tesseract-OCR" / "tesseract.exe"
    if windows_engine.is_file():
        pytesseract.pytesseract.tesseract_cmd = str(windows_engine)


class OCRError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def readiness():
    try:
        result = subprocess.run(
            [pytesseract.pytesseract.tesseract_cmd, "--list-langs"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        installed = set(result.stdout.splitlines()[1:])
        return {"ready": {"fra", "eng"}.issubset(installed),
                "languages": sorted(installed & {"fra", "eng"})}
    except (OSError, subprocess.SubprocessError):
        return {"ready": False, "languages": []}


def extract(data, language, options=None):
    try:
        options = validate_options(options or {})
    except (ValueError, TypeError):
        raise OCRError("invalid_options", "Réglages invalides : vérifiez les coins et les modes proposés.") from None
    if language not in LANGUAGES:
        raise OCRError("invalid_language", "Choisissez une langue proposée.")
    if len(data) > MAX_BYTES:
        raise OCRError("image_too_large", "L’image dépasse 10 Mio. Réduisez sa taille.", 413)
    if not data:
        raise OCRError("invalid_image", "Le fichier est vide. Choisissez une image PNG ou JPEG.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in {"PNG", "JPEG"}:
                    raise OCRError("invalid_image", "Seules les images PNG et JPEG sont acceptées.")
                if source.width * source.height > MAX_PIXELS:
                    raise OCRError("too_many_pixels", "L’image dépasse 20 millions de pixels.", 413)
                source.verify()
            with Image.open(io.BytesIO(data)) as source:
                with ImageOps.exif_transpose(source) as oriented:
                    # Flatten transparency on white, not the black default of RGB conversion.
                    with oriented.convert("RGBA") as rgba:
                        with Image.new("RGB", rgba.size, "white") as prepared:
                            prepared.paste(rgba, mask=rgba.getchannel("A"))
                            try:
                                processed = prepare(prepared, options)
                            except ValueError as error:
                                raise OCRError("invalid_selection", str(error)) from None
                            with processed:
                                return pytesseract.image_to_string(
                                    processed, lang=language, timeout=30,
                                    config=f"--psm {LAYOUTS[options['layout']]}",
                                ).strip()
    except OCRError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise OCRError("too_many_pixels", "L’image dépasse les dimensions autorisées.", 413) from None
    except pytesseract.TesseractNotFoundError:
        raise OCRError("engine_unavailable", "Le moteur OCR n’est pas installé. Consultez le guide d’installation.", 503) from None
    except pytesseract.TesseractError:
        raise OCRError("ocr_unavailable", "Le moteur OCR ou les données de langue sont indisponibles. Vérifiez l’installation.", 503) from None
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise OCRError("invalid_image", "Impossible de lire cette image. Essayez un autre PNG ou JPEG.") from None
    except RuntimeError:
        raise OCRError("ocr_timeout", "L’extraction a dépassé 30 secondes. Essayez une image plus petite.", 504) from None
