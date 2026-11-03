"""Optional browser check: python tests/browser_smoke.py with Playwright installed.

Requires the server on port 8000, Pillow, Playwright and /usr/bin/chromium.
Screenshots and synthetic image stay in the ignored .test-artifacts directory.
"""
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import expect, sync_playwright

root = Path(__file__).resolve().parent.parent / ".test-artifacts"
root.mkdir(exist_ok=True)
with Image.new("RGB", (1100, 300), "white") as image:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 56)
    ImageDraw.Draw(image).text((50, 90), "Bonjour le monde", font=font, fill="black")
    image.save(root / "sample.png")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
    context = browser.new_context(
        viewport={"width": 1440, "height": 1000},
        permissions=["clipboard-read", "clipboard-write"],
    )
    page = context.new_page()
    errors, external = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: external.append(request.url)
            if not request.url.startswith(("http://127.0.0.1:8000/", "blob:http://127.0.0.1:8000/")) else None)
    page.goto("http://127.0.0.1:8000")
    page.screenshot(path=str(root / "desktop-empty.png"), full_page=True)
    assert page.locator("#extract").is_disabled()
    page.locator("#image").set_input_files(str(root / "sample.png"))
    page.locator("#extract").click()
    expect(page.locator("#text")).to_have_value(re.compile("Bonjour le monde"), timeout=15000)
    corrected = "Texte corrigé : école à côté.\nDeuxième ligne."
    page.locator("#text").fill(corrected)
    page.locator("#copy").click()
    assert page.evaluate("navigator.clipboard.readText()") == corrected
    with page.expect_download() as download:
        page.locator("#download").click()
    assert Path(download.value.path()).read_text() == corrected
    page.screenshot(path=str(root / "desktop-result.png"), full_page=True)
    page.locator("#image").set_input_files(str(root / "sample.png"))
    assert page.locator("#text").input_value() == ""
    assert page.locator("#copy").is_disabled()
    page.locator("#text").evaluate("element => element.disabled = false")
    page.locator("#text").fill("Correction à conserver en cas d’échec")
    page.route("**/api/ocr", lambda route: route.fulfill(
        status=504, json={"error": {"message": "L’extraction a dépassé 30 secondes."}}))
    page.locator("#extract").click()
    expect(page.locator("#status")).to_have_class("status error")
    assert page.locator("#text").input_value() == "Correction à conserver en cas d’échec"
    assert page.locator("#copy").is_enabled()
    assert page.locator("#extract").is_enabled()
    page.unroute("**/api/ocr")
    # Rotate four times, define a zone via keyboard, and exercise new OCR settings.
    for _ in range(4):
        page.locator("#rotate").click()
    page.locator("#crop-enabled").check()
    page.locator("#place-corners").click()
    box = page.locator("#selection-canvas").bounding_box()
    for x, y in ((.01, .01), (.99, .01), (.99, .99), (.01, .99)):
        page.mouse.click(box["x"] + x * box["width"], box["y"] + y * box["height"])
    page.locator("#crop-tools details").evaluate("element => element.open = true")
    page.locator("#corner-0-0").fill("1")
    page.locator("#processing").select_option("contrast")
    page.locator("#layout").select_option("sparse")
    page.locator("#deskew").check()
    page.locator(".zones").evaluate("element => element.open = true")
    page.locator("#zone-name").fill("Nom")
    page.locator("#extract").click()
    expect(page.locator("#text")).to_have_value(re.compile("Nom :.*Bonjour le monde", re.S), timeout=20000)
    page.locator("#append-result").check()
    page.locator("#zone-name").fill("Autre zone")
    page.locator("#processing").select_option("threshold")
    page.locator("#extract").click()
    expect(page.locator("#text")).to_have_value(re.compile("Nom :.*Autre zone :", re.S), timeout=20000)
    page.screenshot(path=str(root / "desktop-preparation.png"), full_page=True)
    saved = page.locator("#text").input_value()
    page.locator("#engine").select_option("paddleocr")
    assert page.locator("#language").is_disabled()
    assert page.locator("#layout").is_disabled()
    page.locator("#extract").click()
    expect(page.locator("#status")).to_have_class("status error", timeout=15000)
    assert page.locator("#text").input_value() == saved
    page.screenshot(path=str(root / "desktop-paddle-unavailable.png"), full_page=True)
    page.locator("#engine").select_option("tesseract")
    assert page.locator("#language").is_enabled()
    assert page.locator("#layout").is_enabled()
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto("http://127.0.0.1:8000")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(path=str(root / "mobile-empty.png"), full_page=True)
    page.locator("#image").set_input_files(str(root / "sample.png"))
    page.locator("#extract").click()
    expect(page.locator("#text")).to_have_value(re.compile("Bonjour le monde"), timeout=15000)
    page.screenshot(path=str(root / "mobile-result.png"), full_page=True)
    page.locator("#crop-enabled").check()
    page.locator("#crop-tools details").evaluate("element => element.open = true")
    page.screenshot(path=str(root / "mobile-preparation.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert not errors, errors
    assert not external, external
    print("Browser OK: OCR desktop/mobile, édition, copie, export, réinitialisation, erreur et nouvelle tentative ; aucun appel externe ni erreur JS.")
    browser.close()
