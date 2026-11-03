"""Optional Chromium check for the seven-field workflow, no personal data.
Run with the local server started, Playwright, Pillow and /usr/bin/chromium.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import expect, sync_playwright

root = Path(__file__).resolve().parent.parent / '.test-artifacts'
root.mkdir(exist_ok=True)
with Image.new('RGB', (1600, 1100), 'white') as image:
    draw = ImageDraw.Draw(image)
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    label_font, value_font = ImageFont.truetype(font_path, 26), ImageFont.truetype(font_path, 34)
    for i, (label, value) in enumerate([
        ('NOM / SURNAME', 'MARTIN'), ('PRENOMS / GIVEN NAMES', 'ALICE MARIE'),
        ('DATE DE NAISSANCE / DATE OF BIRTH', '17.12.2000'),
        ('LIEU DE NAISSANCE / PLACE OF BIRTH', 'VILLE DEMO'),
        ('SEXE / SEX', 'F'), ('TAILLE / HEIGHT', '1,77'), ('PROFESSION / OCCUPATION', 'TECHNICIENNE')]):
        draw.text((60, 30 + i * 130), label, font=label_font, fill='black')
        draw.text((60, 72 + i * 130), value, font=value_font, fill='black')
    draw.text((1050, 30), 'CARD NUMBER', font=label_font, fill='black')
    draw.text((1050, 72), 'SECRET-123', font=value_font, fill='black')
    image.save(root / 'synthetic-fields.png')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path='/usr/bin/chromium')
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, permissions=['clipboard-read', 'clipboard-write'])
    page = context.new_page()
    errors, external = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: external.append(request.url) if not request.url.startswith(('http://127.0.0.1:8000/', 'blob:http://127.0.0.1:8000/')) else None)
    page.goto('http://127.0.0.1:8000')
    assert page.locator('#extract').is_disabled()
    page.screenshot(path=str(root / 'desktop-fields-empty.png'), full_page=True)
    page.locator('#image').set_input_files(str(root / 'synthetic-fields.png'))
    page.locator('#layout').select_option('sparse')
    page.locator('#language').select_option('fra+eng')
    page.locator('#extract').click()
    expect(page.locator('#field-nom')).to_have_value('MARTIN', timeout=20000)
    expect(page.locator('#count')).to_have_text('7/7 champs renseignés')
    assert 'SECRET' not in page.locator('#text').input_value()
    page.locator('#field-nom').fill('MARTIN CORRIGÉ')
    page.locator('#copy').click()
    copied = page.evaluate('navigator.clipboard.readText()')
    assert 'Nom : MARTIN CORRIGÉ' in copied and 'SECRET' not in copied
    with page.expect_download() as download:
        page.locator('#download').click()
    assert Path(download.value.path()).read_text(encoding='utf-8') == copied
    with page.expect_download() as download:
        page.locator('#download-json').click()
    payload = json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
    assert len(payload['champs']) == 7
    assert payload['champs']['nom']['valeur'] == 'MARTIN CORRIGÉ'
    assert payload['champs']['nom']['statut'] == 'modifie_manuellement'
    assert 'SECRET' not in json.dumps(payload)
    page.screenshot(path=str(root / 'desktop-fields-result.png'), full_page=True)
    page.route('**/api/ocr', lambda route: route.fulfill(status=504, json={'error': {'message': 'Délai dépassé.'}}))
    page.locator('#extract').click()
    expect(page.locator('#status')).to_have_class('status error')
    assert page.locator('#field-nom').input_value() == 'MARTIN CORRIGÉ'
    assert page.locator('#download-json').is_enabled()
    page.unroute('**/api/ocr')
    page.locator('#engine').select_option('paddleocr')
    assert page.locator('#language').is_disabled() and page.locator('#layout').is_disabled()
    page.locator('#extract').click()
    expect(page.locator('#status')).to_have_class('status error', timeout=15000)
    assert page.locator('#field-nom').input_value() == 'MARTIN CORRIGÉ'
    page.locator('#engine').select_option('tesseract')
    # Exercise pointer selection and rotation before returning to full image.
    for _ in range(4):
        page.locator('#rotate').click()
    page.locator('#crop-enabled').check()
    page.locator('#place-corners').click()
    box = page.locator('#selection-canvas').bounding_box()
    for x, y in ((.01, .01), (.99, .01), (.99, .99), (.01, .99)):
        page.mouse.click(box['x'] + x * box['width'], box['y'] + y * box['height'])
    page.locator('#reset-selection').click()
    page.locator('#image').set_input_files(str(root / 'synthetic-fields.png'))
    assert page.locator('#fields').is_hidden()
    assert page.locator('#text').input_value() == ''
    assert page.locator('#download-json').is_disabled()
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('#extract').click()
    expect(page.locator('#field-nom')).to_have_value('MARTIN', timeout=20000)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(root / 'mobile-fields-result.png'), full_page=True)
    assert not errors, errors
    assert not external, external
    print('Browser OK: sept champs, correction, TXT/JSON/copie sans autres données, erreur sans perte, réinitialisation, moteurs, rotation/coins et mobile.')
    browser.close()
