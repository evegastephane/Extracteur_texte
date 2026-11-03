import io
import json

import pytest
from PIL import Image, ImageDraw, ImageFont

from app import create_app
from app.fields import FIELDS, extract_fields, selected_text
from app.ocr import extract
from app.paddle_worker import collect_results
from test_app import FONT_PATH, image_bytes


def token(text, x, y, width=None, height=16):
    return {"text": text, "box": [x, y, width or len(text) * 9, height]}


@pytest.mark.parametrize("label,key,value", [
    ("NOM/SURNAME", "nom", "MARTIN"), ("Prénoms/GIVEN NAMES", "prenoms", "ALICE MARIE"),
    ("DATE DE NAISSANCE/DATE OF BIRTH", "date_naissance", "17.12.2000"),
    ("LIEU DE NAISSANCE/PLACE OF BIRTH", "lieu_naissance", "VILLE DEMO"),
    ("SEXE/SEX", "sexe", "F"), ("TAILLE/HEIGHT", "taille", "1,77"),
    ("PROFFESION/OCCUPATION", "profession", "TECHNICIENNE"),
    ("SURNAME", "nom", "DOE"), ("GIVEN NAMES", "prenoms", "JANE"),
    ("DATE OF BIRTH", "date_naissance", "01/02/1999"),
])
@pytest.mark.parametrize("relation", ["droite", "dessous"])
def test_bilingual_labels_and_positions(label, key, value, relation):
    tokens = [token(label, 50, 20)]
    tokens.append(token(value, 60 + len(label) * 9, 20) if relation == "droite" else token(value, 50, 45))
    fields = extract_fields(tokens, 1200, 800)
    assert fields[key]["value"] == value
    assert fields[key]["status"] == "propose"
    assert fields[key]["evidence"][0]["relation"] == relation
    assert set(fields) == set(FIELDS)


def test_adjacent_columns_are_not_mixed():
    fields = extract_fields([token("SEXE/SEX", 50, 20), token("TAILLE/HEIGHT", 250, 20), token("F", 50, 45), token("177 cm", 250, 45)], 1000, 400)
    assert fields["sexe"]["value"] == "F"
    assert fields["taille"]["value"] == "177 cm"
    assert fields["taille"]["normalized"] == "1.77 m"


@pytest.mark.parametrize("same_line", [True, False])
def test_height_unit_without_space_is_not_an_identifier(same_line):
    fields = extract_fields([token("HEIGHT", 50, 20), token("177cm", 120 if same_line else 50, 20 if same_line else 45)], 1000, 500)
    assert fields["taille"]["normalized"] == "1.77 m"


def test_unknown_unrelated_information_is_not_returned():
    fields = extract_fields([token("NOM/SURNAME MARTIN NATIONALITÉ AUTRE", 50, 20, width=800),
        token("CARD NUMBER SECRET-123", 50, 100), token("DATE OF ISSUE 01/01/2020", 50, 150)], 1000, 500)
    assert fields["nom"]["value"] == "MARTIN"
    serialized = json.dumps(fields)
    assert "SECRET" not in serialized and "2020" not in serialized and "AUTRE" not in serialized
    assert selected_text(fields) == "Nom : MARTIN"


def test_missing_labels_never_infer_fields_from_values():
    fields = extract_fields([token("MARTIN ALICE 17/12/2000 F 1,77 TECHNICIENNE", 50, 30)], 1000, 500)
    assert all(field["status"] == "non_trouve" and field["value"] == "" for field in fields.values())
    assert selected_text(fields) == ""


def test_same_row_unrelated_distant_identifier_discarded():
    fields = extract_fields([token("NOM", 50, 20, 27), token("MARTIN", 110, 20, 54), token("SECRET-123", 700, 20, 90)], 1000, 500)
    assert fields["nom"]["value"] == "MARTIN"
    assert "SECRET" not in json.dumps(fields)


def test_unlabelled_identifier_not_appended_to_profession():
    fields = extract_fields([token("PROFESSION", 50, 20, 90), token("TECHNICIENNE", 50, 45, 99), token("SECRET-123", 50, 65, 90)], 1000, 500)
    assert fields["profession"]["value"] == "TECHNICIENNE"
    assert "SECRET" not in json.dumps(fields)


def test_inline_nearby_identifier_not_copied_as_name():
    fields = extract_fields([token("NOM", 50, 20, 27), token("MARTIN", 110, 20, 54), token("SECRET-123", 180, 20, 90)], 1000, 500)
    assert fields["nom"]["value"] == "MARTIN"
    assert "SECRET" not in json.dumps(fields)


def test_stop_before_next_label_not_use_its_value():
    fields = extract_fields([token("NOM/SURNAME", 50, 20), token("PRENOMS/GIVEN NAMES", 50, 45), token("ALICE", 50, 70)], 1000, 400)
    assert fields["nom"]["value"] == ""
    assert fields["prenoms"]["value"] == "ALICE"


def test_conflicting_labels_are_ambiguous():
    fields = extract_fields([token("NOM : MARTIN", 50, 20), token("SURNAME : DOE", 50, 120)], 1000, 500)
    assert fields["nom"]["status"] == "a_verifier"
    assert fields["nom"]["value"] == ""
    assert len(fields["nom"]["evidence"]) == 2


@pytest.mark.parametrize("label,value", [("DATE OF BIRTH", "31/02/2000"), ("SEX", "X??"), ("HEIGHT", "9,99 m")])
def test_invalid_typed_values_retained_with_warning(label, value):
    fields = extract_fields([token(f"{label} : {value}", 50, 20)], 1000, 500)
    found = next(field for field in fields.values() if field["value"])
    assert found["status"] == "a_verifier"
    assert found["normalized"] is None


def test_wrapped_value():
    fields = extract_fields([token("PLACE OF BIRTH", 50, 20), token("VILLE", 50, 45), token("DEMO", 50, 65), token("PROFESSION", 50, 100)], 1000, 500)
    assert fields["lieu_naissance"]["value"] == "VILLE DEMO"


def synthetic_card():
    image = Image.new("RGB", (1600, 1100), "white")
    draw = ImageDraw.Draw(image)
    label_font = ImageFont.truetype(FONT_PATH, 26)
    value_font = ImageFont.truetype(FONT_PATH, 34)
    entries = [("NOM / SURNAME", "MARTIN"), ("PRENOMS / GIVEN NAMES", "ALICE MARIE"),
        ("DATE DE NAISSANCE / DATE OF BIRTH", "17.12.2000"),
        ("LIEU DE NAISSANCE / PLACE OF BIRTH", "VILLE DEMO"),
        ("SEXE / SEX", "F"), ("TAILLE / HEIGHT", "1,77"), ("PROFESSION / OCCUPATION", "TECHNICIENNE")]
    for index, (label, value) in enumerate(entries):
        y = 30 + index * 130
        draw.text((60, y), label, font=label_font, fill="black")
        draw.text((60, y + 42), value, font=value_font, fill="black")
    draw.text((1050, 30), "CARD NUMBER", font=label_font, fill="black")
    draw.text((1050, 72), "SECRET-123", font=value_font, fill="black")
    stream = io.BytesIO(); image.save(stream, format="PNG"); image.close()
    return stream.getvalue()


def test_real_tesseract_fields_only():
    result = extract(synthetic_card(), "fra+eng", {"layout": "sparse"}, structured=True)
    assert result["fields"]["nom"]["value"] == "MARTIN"
    assert result["fields"]["prenoms"]["value"] == "ALICE MARIE"
    assert result["fields"]["date_naissance"]["normalized"] == "2000-12-17"
    assert result["fields"]["lieu_naissance"]["value"] == "VILLE DEMO"
    assert result["fields"]["sexe"]["value"] == "F"
    assert result["fields"]["taille"]["normalized"] == "1.77 m"
    assert result["fields"]["profession"]["value"] == "TECHNICIENNE"
    assert "SECRET" not in json.dumps(result)


def test_structured_api_and_input_validation():
    client = create_app().test_client()
    response = client.post("/api/ocr", data={"image": (io.BytesIO(synthetic_card()), "card.png"),
        "language": "fra+eng", "engine": "tesseract", "options": json.dumps({"layout": "sparse"}), "structured": "true"})
    assert response.status_code == 200
    assert set(response.json["fields"]) == set(FIELDS)
    assert "SECRET" not in response.get_data(as_text=True)
    assert "tokens" not in response.json
    assert client.post("/api/ocr", data={"image": (io.BytesIO(image_bytes()), "photo.png"), "structured": "invalid"}).status_code == 400


def test_default_api_does_not_return_unlabelled_text():
    response = create_app().test_client().post("/api/ocr", data={"image": (io.BytesIO(image_bytes("Autre information")), "photo.png")})
    assert response.status_code == 200
    assert response.json["text"] == ""
    assert "Autre information" not in response.get_data(as_text=True)
    assert set(response.json["fields"]) == set(FIELDS)


def test_paddle_line_box_parser_without_real_model(monkeypatch):
    # Explicitly simulated PaddleOCR geometry; actual model inference remains unverified.
    payload = collect_results([{"rec_texts": ["NOM / SURNAME : MARTIN"], "rec_polys": [[[50, 20], [600, 20], [600, 50], [50, 50]]]}])
    monkeypatch.setattr("app.ocr.recognize_paddle", lambda image, structured: payload)
    result = extract(image_bytes(), "fra", engine="paddleocr", structured=True)
    assert result["fields"]["nom"]["value"] == "MARTIN"
