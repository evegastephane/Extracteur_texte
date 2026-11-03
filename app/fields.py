"""Deterministic label-and-position extraction. No training, no identity inference.

Input boxes are in prepared-image pixels. Only seven allowlisted fields leave
this module; unrelated OCR content is never included in the response.
"""
from datetime import date
import re
import unicodedata

FIELDS = {
    "nom": ("Nom", ["NOM DE FAMILLE", "SURNAME", "LAST NAME", "NOM", "N0M"]),
    "prenoms": ("Prénoms", ["PRENOMS", "PRENOM", "GIVEN NAMES", "GIVEN NAME", "FIRST NAMES", "FIRST NAME"]),
    "date_naissance": ("Date de naissance", ["DATE DE NAISSANCE", "DATE OF BIRTH", "BIRTH DATE"]),
    "lieu_naissance": ("Lieu de naissance", ["LIEU DE NAISSANCE", "PLACE OF BIRTH", "BIRTHPLACE"]),
    "sexe": ("Sexe", ["SEXE", "SEX"]),
    "taille": ("Taille", ["TAILLE", "HEIGHT"]),
    "profession": ("Profession", ["PROFESSION", "PROFFESION", "PROFESION", "OCCUPATION"]),
}


def normalized(text):
    return "".join(char for char in unicodedata.normalize("NFKD", text.upper()) if not unicodedata.combining(char))


PATTERNS = sorted([
    (key, re.compile(r"(?<![A-Z0-9])" + r"\s*".join(alias.split()) + r"(?![A-Z0-9])"))
    for key, (_, aliases) in FIELDS.items() for alias in aliases
], key=lambda item: -len(item[1].pattern))
# These labels delimit a value but are never returned as fields.
EXCLUDED = ["NATIONALITE", "NATIONALITY", "NUMERO DE CARTE", "CARD NUMBER", "DOCUMENT NUMBER",
    "DATE DE DELIVRANCE", "DATE OF ISSUE", "DATE D EXPIRATION", "DATE OF EXPIRY", "EXPIRY DATE",
    "SIGNATURE", "AUTORITE", "AUTHORITY", "ADRESSE", "ADDRESS", "IDENTITY NUMBER"]
PATTERNS.extend((None, re.compile(r"(?<![A-Z0-9])" + r"\s+".join(alias.split()) + r"(?![A-Z0-9])")) for alias in EXCLUDED)
PATTERNS.sort(key=lambda item: -len(item[1].pattern))


def _row_text(tokens):
    text, spans = "", []
    for token in sorted(tokens, key=lambda item: item["box"][0]):
        if text:
            text += " "
        start = len(text)
        text += token["text"]
        spans.append((start, len(text), token))
    return text, spans


def _box_for_span(row, start, end):
    boxes = []
    for left, right, token in row["spans"]:
        if right <= start or left >= end:
            continue
        x, y, w, h = token["box"]
        length = max(1, right - left)
        # Paddle may supply a whole text line in one box. Character interpolation
        # is an approximation for geometry, never a modification of the text.
        offset = max(start, left) - left
        fraction = (min(end, right) - max(start, left)) / length
        boxes.append([x + w * offset / length, y, w * fraction, h])
    if not boxes:
        return [0, 0, 0, 0]
    x, y = min(box[0] for box in boxes), min(box[1] for box in boxes)
    return [x, y, max(box[0] + box[2] for box in boxes) - x, max(box[1] + box[3] for box in boxes) - y]


def rows_from_tokens(tokens):
    rows = []
    for token in sorted(tokens, key=lambda item: (item["box"][1], item["box"][0])):
        x, y, w, h = token["box"]
        if not token["text"].strip() or min(w, h) <= 0:
            continue
        center = y + h / 2
        target = next((row for row in reversed(rows[-6:]) if abs(row["center"] - center) <= .45 * max(row["height"], h)), None)
        if target is None:
            target = {"tokens": [], "center": center, "height": h}
            rows.append(target)
        target["tokens"].append(token)
        target["center"] = sum(t["box"][1] + t["box"][3] / 2 for t in target["tokens"]) / len(target["tokens"])
        target["height"] = max(target["height"], h)
    for row in rows:
        row["text"], row["spans"] = _row_text(row["tokens"])
        row["top"] = min(t["box"][1] for t in row["tokens"])
        # Build a normalized string while keeping offsets into original Unicode.
        norm, mapping = "", []
        for index, char in enumerate(row["text"]):
            for part in normalized(char):
                norm += part if part.isalnum() else " "
                mapping.append(index)
        found = []
        for key, pattern in PATTERNS:
            for match in pattern.finditer(norm):
                start, end = mapping[match.start()], mapping[match.end() - 1] + 1
                if any(start < hit["end"] and end > hit["start"] for hit in found):
                    continue
                found.append({"key": key, "start": start, "end": end})
        merged = []
        for hit in sorted(found, key=lambda item: item["start"]):
            if merged and merged[-1]["key"] == hit["key"] and not re.search(r"\w", row["text"][merged[-1]["end"]:hit["start"]]):
                merged[-1]["end"] = hit["end"]
            else:
                merged.append(hit)
        for hit in merged:
            hit["box"] = _box_for_span(row, hit["start"], hit["end"])
            hit["label"] = row["text"][hit["start"]:hit["end"]]
        row["labels"] = merged
    return sorted(rows, key=lambda row: row["top"])


def _clean(value):
    return value.strip(" \t\r\n:;/|—–=-")


def _identifier_like(value):
    return any(len(word) >= 5 and re.fullmatch(r"[A-Z0-9./-]+", word) and any(c.isalpha() for c in word) and any(c.isdigit() for c in word)
               for word in normalized(value).split())


def _inline_candidate(row, hit, end, width):
    pieces = []
    for start, stop, token in row["spans"]:
        left, right = max(start, hit["end"]), min(stop, end)
        if left >= right:
            continue
        for word in re.finditer(r"\S+", row["text"][left:right]):
            first, last = left + word.start(), left + word.end()
            value = _clean(row["text"][first:last])
            if value:
                pieces.append((value, _box_for_span(row, first, last)))
    chosen = []
    previous_right = hit["box"][0] + hit["box"][2]
    previous_height = hit["box"][3]
    for value, box in pieces:
        gap_limit = max(4 * previous_height, width * .04) if not chosen else 3 * max(previous_height, box[3])
        if box[0] - previous_right > gap_limit or (hit["key"] in {"nom", "prenoms", "lieu_naissance", "profession"} and _identifier_like(value)):
            break
        chosen.append(value)
        previous_right, previous_height = box[0] + box[2], box[3]
    return " ".join(chosen)


def _typed_value(key, value):
    """Return normalized display value + warning. Never repair uncertain OCR digits."""
    if key == "date_naissance":
        match = re.fullmatch(r"(\d{1,2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{4})", value)
        iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value)
        try:
            if match:
                day, month, year = map(int, match.groups())
            elif iso:
                year, month, day = map(int, iso.groups())
            else:
                raise ValueError()
            result = date(year, month, day)
            if year < 1850 or result > date.today():
                raise ValueError()
            return result.isoformat(), None
        except ValueError:
            return None, "Date non reconnue ou invalide : vérifiez les chiffres."
    if key == "sexe":
        value_norm = normalized(value)
        if value_norm in {"M", "MALE", "MASCULIN"}:
            return "M", None
        if value_norm in {"F", "FEMALE", "FEMININ"}:
            return "F", None
        return None, "Valeur du sexe à vérifier."
    if key == "taille":
        match = re.fullmatch(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*(CM|M)?", normalized(value))
        if match:
            number = float(match[1].replace(",", "."))
            if match[2] == "CM" or (match[2] is None and number >= 30):
                number /= 100
            if .3 <= number <= 2.7:
                return f"{number:.2f} m", None
        return None, "Taille non reconnue : vérifiez la valeur et l’unité."
    if len(value) > 200 or not any(char.isalpha() for char in value):
        return None, "Valeur à vérifier."
    return value, None


def _below_candidate(rows, index, hit, boundary, width):
    x, y, w, h = hit["box"]
    candidates = []
    for row in rows[index + 1:]:
        if row["top"] > y + h + max(5 * h, 25):
            break
        # A subsequent label in this column is a hard stop, not a value.
        if any(abs(label["box"][0] - x) <= max(2 * h, width * .035) for label in row["labels"]):
            break
        eligible = []
        for start, end, token in row["spans"]:
            if any(start < label["end"] and end > label["start"] for label in row["labels"]):
                continue
            tx, ty, tw, th = token["box"]
            if tx >= x - h and tx < boundary and ty >= y + h * .5:
                eligible.append(token)
        if not eligible:
            continue
        eligible.sort(key=lambda token: token["box"][0])
        first_x = eligible[0]["box"][0]
        if abs(first_x - x) > max(2 * h, width * .035):
            continue
        chunk = [eligible[0]]
        for token in eligible[1:]:
            previous = chunk[-1]["box"]
            if token["box"][0] - (previous[0] + previous[2]) > 3 * max(previous[3], token["box"][3]):
                break
            chunk.append(token)
        value = _clean(" ".join(token["text"] for token in chunk))
        if (hit["key"] in {"nom", "prenoms", "lieu_naissance", "profession"} and _identifier_like(value)) or (candidates and any(char.isdigit() for char in value)):
            # A second unlabeled line containing digits is not safe to merge.
            # Do not expose discarded identifiers even as candidate evidence.
            break
        if value:
            candidates.append(value)
            # Names/places/occupations may wrap across two close aligned lines.
            if hit["key"] in {"date_naissance", "sexe", "taille"} or len(candidates) == 2:
                break
            # Never concatenate past a new field or large vertical gap.
            next_index = rows.index(row) + 1
            if next_index >= len(rows) or rows[next_index]["labels"] or rows[next_index]["top"] > row["top"] + 1.8 * row["height"]:
                break
    return " ".join(candidates)


def extract_fields(tokens, width, height):
    rows = rows_from_tokens(tokens)
    proposals = {key: [] for key in FIELDS}
    labels_seen = set()
    for index, row in enumerate(rows):
        for order, hit in enumerate(row["labels"]):
            key = hit["key"]
            if key is None:
                continue
            labels_seen.add(key)
            next_label = row["labels"][order + 1] if order + 1 < len(row["labels"]) else None
            end = next_label["start"] if next_label else len(row["text"])
            value = _inline_candidate(row, hit, end, width)
            relation = "droite"
            if not value:
                boundary = next_label["box"][0] if next_label else width
                value = _below_candidate(rows, index, hit, boundary, width)
                relation = "dessous"
            if not value:
                continue
            normalized_value, warning = _typed_value(key, value)
            proposals[key].append({"value": value, "normalized": normalized_value,
                "label": hit["label"], "relation": relation, "warning": warning,
                "label_box": [round(hit["box"][0] / width, 4), round(hit["box"][1] / height, 4), round(hit["box"][2] / width, 4), round(hit["box"][3] / height, 4)]})
    result = {}
    for key, (title, _) in FIELDS.items():
        options = []
        for proposal in proposals[key]:
            if not any(normalized(proposal["value"]) == normalized(item["value"]) for item in options):
                options.append(proposal)
        field = {"label": title, "value": "", "normalized": None, "status": "non_trouve", "message": "Valeur absente." if key in labels_seen else "Libellé absent.", "evidence": []}
        if len(options) == 1:
            proposal = options[0]
            field.update(value=proposal["value"], normalized=proposal["normalized"], status="a_verifier" if proposal["warning"] else "propose", message=proposal["warning"] or "Valeur proposée, à relire.", evidence=options)
        elif len(options) > 1:
            field.update(status="a_verifier", message="Plusieurs valeurs possibles : choisissez après vérification.", evidence=options)
        result[key] = field
    return result


def selected_text(fields):
    return "\n".join(f"{field['label']} : {field['value']}" for field in fields.values() if field["value"])
