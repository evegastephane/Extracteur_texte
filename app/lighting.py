"""Conservative automatic lighting for the aligned card, without text synthesis."""
import math

import cv2
import numpy as np
from PIL import Image


def auto_lighten(image, measurement_box=(.25, .18, .64, .78)):
    """Return a new RGB image and a non-content status for the upload preview.

    Measure the card's value area rather than the dark desk/portrait. Gamma
    lifts a globally dark exposure; a smooth bounded gain lifts local shadows.
    Already bright images take the exact, unmodified-pixel path.
    """
    rgb = np.array(image.convert("RGB"))
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    luminance = lab[:, :, 0]
    height, width = luminance.shape
    left, top, right, bottom = measurement_box
    roi = (slice(round(top * height), max(round(top * height) + 1, round(bottom * height))),
           slice(round(left * width), max(round(left * width) + 1, round(right * width))))
    background = cv2.GaussianBlur(cv2.morphologyEx(luminance, cv2.MORPH_CLOSE, np.ones((17, 17), np.uint8)), (0, 0), 25)
    sample = background[roi]
    paper = float(np.percentile(sample, 85))
    status = {"applied": False, "global": False, "shadows": False, "warning": ""}
    if paper < 8:
        status["warning"] = "La photo est presque noire : reprenez-la avec davantage de lumière."
        return Image.fromarray(rgb), status
    if paper < 35:
        status["warning"] = "La photo est très sombre : vérifiez que les lettres sont réellement lisibles."
    corrected = luminance.copy()
    if paper < 175:
        gamma = max(.50, min(1.0, math.log(210 / 255) / math.log(paper / 255)))
        table = np.round(255 * (np.arange(256, dtype=np.float32) / 255) ** gamma).astype(np.uint8)
        corrected = cv2.LUT(corrected, table)
        background = cv2.LUT(background, table)
        status["global"] = True
    sample = background[roi]
    # A uniform dark image is handled above. Only a substantial mix of dark
    # and bright paper triggers spatial gain, to avoid lifting ordinary ink.
    if np.mean(sample < 155) >= .12 and np.mean(sample > 195) >= .12:
        gain = np.clip(195 / np.maximum(background.astype(np.float32), 1), 1, 1.8)
        values = corrected.astype(np.float32)
        lifted = np.minimum(255, values * gain)
        # Fade the change near white so glare/highlights are not amplified.
        protection = 1 - (values / 255) ** 4
        corrected = np.round(values + (lifted - values) * protection).clip(0, 255).astype(np.uint8)
        status["shadows"] = True
    status["applied"] = status["global"] or status["shadows"]
    if not status["applied"]:
        return Image.fromarray(rgb), status
    lab[:, :, 0] = corrected
    return Image.fromarray(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)), status
