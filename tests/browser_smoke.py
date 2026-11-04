"""Wizard browser regression. Alignment/errors are real HTTP; successful Paddle
zone output is explicitly simulated because local model weights are unavailable.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import expect, sync_playwright

root = Path(__file__).resolve().parent.parent
out = root / '.test-artifacts'; out.mkdir(exist_ok=True)
profile = json.loads((root / 'app/cni_templates.json').read_text())['cni_puce_recto_v1']
names = {'nom':'Nom', 'prenoms':'Prénoms', 'date_naissance':'Date de naissance', 'lieu_naissance':'Lieu de naissance', 'sexe':'Sexe', 'taille':'Taille', 'profession':'Profession'}
values = {'nom':'MARTIN', 'prenoms':'ALICE MARIE', 'date_naissance':'17.12.2000', 'lieu_naissance':'VILLE DEMO', 'sexe':'F', 'taille':'1,77', 'profession':'TECHNICIENNE'}
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 36)
with Image.new('RGB', (1600, 1000), '#f7f8ef') as image:
    draw = ImageDraw.Draw(image)
    draw.rectangle((4, 4, 1595, 995), outline='#386849', width=8)
    draw.text((400, 70), 'DOCUMENT SYNTHETIQUE', font=font, fill='black')
    draw.rectangle((1070, 290, 1520, 900), fill='#b9c7b9')
    draw.text((1100, 520), 'FICTIF', font=font, fill='black')
    for key, (left, top, right, bottom) in profile['zones'].items():
        draw.text((round(left * 1600) + 8, round(top * 1000) + 1), values[key], font=font, fill='black')
    image.save(out / 'cni-front.png')
with Image.new('RGB', (1600, 1000), '#e5e9dc') as image:
    ImageDraw.Draw(image).text((200, 450), 'VERSO SYNTHETIQUE', font=font, fill='black')
    image.save(out / 'cni-back.png')
fields = {key: {'label':name, 'value':values[key], 'normalized':None, 'status':'propose', 'message':'Valeur proposée dans la zone prédéfinie, à relire.'} for key,name in names.items()}
fields['taille'].update(status='a_verifier', message='Lecture incertaine : vérifiez cette zone sur la carte.')
fixture = {'fields':fields, 'profile':'cni_puce_recto_v1', 'engine':'paddleocr', 'profile_status':'provisional'}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path='/usr/bin/chromium')
    context = browser.new_context(viewport={'width':1440,'height':1000}, permissions=['clipboard-read','clipboard-write'])
    page = context.new_page(); errors, external = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: external.append(request.url) if not request.url.startswith(('http://127.0.0.1:8000/', 'blob:http://127.0.0.1:8000/')) else None)
    page.goto('http://127.0.0.1:8000')
    assert page.locator('select').count() == 0
    assert page.locator('#next').is_disabled()
    page.screenshot(path=str(out/'desktop-wizard-recto.png'), full_page=True)
    page.locator('#image').set_input_files(str(out/'cni-front.png'))
    expect(page.locator('#next')).to_be_enabled(timeout=15000)
    page.locator('#flip-photo').click()
    expect(page.locator('#next')).to_be_enabled()
    page.locator('#flip-photo').click()
    expect(page.locator('#next')).to_be_enabled()
    page.locator('#next').click()
    expect(page.locator('#upload-title')).to_have_text('Ajoutez le verso')
    assert page.locator('#next').is_disabled()
    page.locator('#image').set_input_files(str(out/'cni-back.png'))
    expect(page.locator('#next')).to_be_enabled(timeout=15000)
    page.screenshot(path=str(out/'desktop-wizard-verso.png'), full_page=True)
    # Actual missing-engine response: no fake claim of a successful Paddle read.
    page.locator('#next').click()
    expect(page.locator('#status')).to_have_class('status error', timeout=15000)
    assert page.locator('#upload-step').is_visible()
    assert page.locator('#next').is_enabled()
    # Simulate only the OCR response to exercise result UI independently.
    page.route('**/api/cni/read', lambda route: route.fulfill(json=fixture))
    page.locator('#next').click()
    expect(page.locator('#field-nom')).to_have_value('MARTIN')
    expect(page.locator('#count')).to_have_text('7/7 champs renseignés')
    expect(page.locator('#note-taille')).to_contain_text('Lecture incertaine')
    page.locator('#field-nom').fill('MARTIN CORRIGÉ')
    page.locator('#copy').click()
    copied = page.evaluate('navigator.clipboard.readText()')
    assert 'Nom : MARTIN CORRIGÉ' in copied and 'FICTIF' not in copied
    with page.expect_download() as download: page.locator('#download-json').click()
    exported = json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
    assert len(exported['champs']) == 7
    assert exported['champs']['nom']['statut'] == 'modifie_manuellement'
    with page.expect_download() as download: page.locator('#download').click()
    assert Path(download.value.path()).read_text(encoding='utf-8') == copied
    page.screenshot(path=str(out/'desktop-wizard-results.png'), full_page=True)
    page.locator('#review-photos').click(); page.locator('#next').click()
    page.unroute('**/api/cni/read')
    page.route('**/api/cni/read', lambda route: route.fulfill(status=504,json={'error':{'message':'Délai dépassé.'}}))
    page.locator('#next').click()
    expect(page.locator('#result-step')).to_be_visible()  # No reread for unchanged photos.
    expect(page.locator('#status')).to_contain_text('corrections sont conservées')
    assert page.locator('#field-nom').input_value() == 'MARTIN CORRIGÉ'
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(out/'mobile-wizard-results.png'), full_page=True)
    page.locator('#review-photos').click()
    page.screenshot(path=str(out/'mobile-wizard-recto.png'), full_page=True)
    page.locator('#image').set_input_files(str(out/'cni-front.png'))
    expect(page.locator('#next')).to_be_enabled(timeout=15000)
    page.locator('#next').click()
    assert page.locator('#next').is_disabled()  # New recto invalidates old verso.
    assert page.locator('#return-results').is_hidden()
    assert page.locator('#result-front').get_attribute('src') is None
    assert page.locator('#result-back').get_attribute('src') is None
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    assert not external, external
    print('Browser OK: recto/verso wizard, real alignment/missing-model error; simulated Paddle result UI, seven editable fields, exports, recovery, mobile, no technical selectors.')
    browser.close()
