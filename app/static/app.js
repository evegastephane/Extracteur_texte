"use strict";
const $ = (id) => document.getElementById(id);
const input = $("image"), preview = $("preview"), text = $("text"), status = $("status");
let paddleAvailable = null;
function updateEngine() {
  const paddle = $("engine").value === "paddleocr";
  $("language").disabled = busy || paddle;
  $("layout").disabled = paddle;
  $("engine-help").textContent = !paddle ? "Tesseract utilise la langue et la disposition choisies ci-dessous." : paddleAvailable === false ? "PaddleOCR n’est pas installé ou ses modèles ne sont pas prêts. Voir le guide PaddleOCR dans la documentation du projet. Tesseract reste disponible." : "PaddleOCR lit le français et l’anglais avec le même modèle latin. La disposition est détectée automatiquement. Le démarrage peut prendre jusqu’à 90 secondes.";
}
let selected = null, previewURL = null, busy = false;
let retainedFields = null, retainedEngine = null;
const fieldNames = {nom: "Nom", prenoms: "Prénoms", date_naissance: "Date de naissance", lieu_naissance: "Lieu de naissance", sexe: "Sexe", taille: "Taille", profession: "Profession"};
const fieldInputs = {};
for (const [key, labelText] of Object.entries(fieldNames)) {
  const group = document.createElement("div"); group.className = "retained-field";
  const label = document.createElement("label"); label.htmlFor = `field-${key}`; label.textContent = labelText;
  const field = document.createElement("input"); field.type = "text"; field.id = `field-${key}`; field.maxLength = 200;
  field.autocomplete = "off"; field.spellcheck = false; field.setAttribute("aria-describedby", `field-note-${key}`);
  const note = document.createElement("small"); note.id = `field-note-${key}`;
  field.addEventListener("input", () => { note.textContent = "Modifié manuellement — à vérifier."; updateRetainedText(); });
  group.append(label, field, note); $("field-list").append(group); fieldInputs[key] = field;
}
function updateRetainedText() {
  text.value = Object.entries(fieldNames).filter(([key]) => fieldInputs[key].value.trim()).map(([key, label]) => `${label} : ${fieldInputs[key].value.trim()}`).join("\n");
  updateActions();
}
function showFields(fields, engine = null) {
  retainedFields = fields; retainedEngine = engine;
  $("fields").hidden = !fields; $("fields").disabled = busy || !fields;
  for (const key of Object.keys(fieldNames)) {
    const field = fields?.[key]; fieldInputs[key].value = field?.value || "";
    const note = $(`field-note-${key}`);
    note.textContent = field?.message || "";
    if (field?.evidence?.length > 1) note.textContent += " Propositions : " + field.evidence.map(item => item.value).join(" / ");
    else if (field?.evidence?.length === 1) note.textContent += ` Libellé « ${field.evidence[0].label} », valeur à ${field.evidence[0].relation === "droite" ? "droite" : "la ligne suivante"}.`;
  }
  updateRetainedText();
}
const canvas = $("selection-canvas"), ctx = canvas.getContext("2d");
let sourceImage = null, rotation = 0, corners = fullCorners(), placing = -1, dragging = -1;
function fullCorners() { return [[0, 0], [1, 0], [1, 1], [0, 1]]; }
const cornerNames = ["Haut gauche", "Haut droit", "Bas droit", "Bas gauche"];
cornerNames.forEach((name, index) => {
  const group = document.createElement("div");
  const title = document.createElement("span"); title.textContent = `${index + 1}. ${name}`; group.append(title);
  const pair = document.createElement("div"); pair.className = "coordinate-pair";
  ["X (%)", "Y (%)"].forEach((axis, coordinate) => {
    const label = document.createElement("label"); label.textContent = axis;
    const field = document.createElement("input"); field.type = "number"; field.min = "0"; field.max = "100"; field.step = "0.1";
    field.setAttribute("aria-label", `${name}, ${axis}`); field.id = `corner-${index}-${coordinate}`;
    field.addEventListener("input", () => {
      if (!Number.isFinite(field.valueAsNumber)) return;
      corners[index][coordinate] = Math.min(100, Math.max(0, field.valueAsNumber)) / 100;
      drawSelection(false);
    });
    label.append(field); pair.append(label);
  });
  group.append(pair); $("corner-inputs").append(group);
});
function drawSelection(sync = true) {
  if (!sourceImage) return;
  const swapped = rotation % 180 !== 0;
  const width = swapped ? sourceImage.naturalHeight : sourceImage.naturalWidth;
  const height = swapped ? sourceImage.naturalWidth : sourceImage.naturalHeight;
  const scale = Math.min(1, 1200 / Math.max(width, height));
  canvas.width = Math.round(width * scale); canvas.height = Math.round(height * scale);
  ctx.save(); ctx.translate(canvas.width / 2, canvas.height / 2); ctx.rotate(rotation * Math.PI / 180);
  ctx.drawImage(sourceImage, -sourceImage.naturalWidth * scale / 2, -sourceImage.naturalHeight * scale / 2, sourceImage.naturalWidth * scale, sourceImage.naturalHeight * scale); ctx.restore();
  if ($("crop-enabled").checked) {
    ctx.lineWidth = Math.max(2, canvas.width / 300); ctx.strokeStyle = "#255e48"; ctx.fillStyle = "#255e4820";
    ctx.beginPath(); corners.forEach(([x, y], index) => index ? ctx.lineTo(x * canvas.width, y * canvas.height) : ctx.moveTo(x * canvas.width, y * canvas.height)); ctx.closePath(); ctx.fill(); ctx.stroke();
    const radius = Math.max(12, canvas.width / 45);
    corners.forEach(([x, y], index) => {
      ctx.beginPath(); ctx.arc(x * canvas.width, y * canvas.height, radius, 0, Math.PI * 2); ctx.fillStyle = "#255e48"; ctx.fill();
      ctx.fillStyle = "#fff"; ctx.font = `bold ${radius}px sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(String(index + 1), x * canvas.width, y * canvas.height);
    });
  }
  $("rotation-label").textContent = `${rotation}°`;
  if (sync) corners.forEach((point, index) => point.forEach((value, coordinate) => { $(`corner-${index}-${coordinate}`).value = String(Math.round(value * 1000) / 10); }));
}
function pointerPoint(event) {
  const box = canvas.getBoundingClientRect();
  return [Math.min(1, Math.max(0, (event.clientX - box.left) / box.width)), Math.min(1, Math.max(0, (event.clientY - box.top) / box.height))];
}
canvas.addEventListener("click", event => event.preventDefault());
canvas.addEventListener("pointerdown", event => {
  event.preventDefault();
  if (busy || !$("crop-enabled").checked) return;
  const point = pointerPoint(event);
  if (placing >= 0) {
    corners[placing++] = point;
    if (placing === 4) { placing = -1; announce("Quatre coins placés. Ajustez les poignées si nécessaire."); }
    else announce(`Placez le coin ${placing + 1} : ${cornerNames[placing].toLowerCase()}.`);
    drawSelection(); return;
  }
  const distances = corners.map(([x, y]) => Math.hypot(x - point[0], y - point[1]));
  dragging = distances.indexOf(Math.min(...distances));
  canvas.setPointerCapture(event.pointerId); corners[dragging] = point; drawSelection();
});
canvas.addEventListener("pointermove", event => { if (dragging >= 0 && !busy) { corners[dragging] = pointerPoint(event); drawSelection(); } });
for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) canvas.addEventListener(name, () => { dragging = -1; });
$("rotate").addEventListener("click", () => { rotation = (rotation + 90) % 360; corners = fullCorners(); placing = -1; drawSelection(); announce("Image tournée. La sélection a été réinitialisée."); });
$("reset-selection").addEventListener("click", () => { corners = fullCorners(); placing = -1; $("crop-enabled").checked = false; $("crop-tools").hidden = true; drawSelection(); });
$("crop-enabled").addEventListener("change", () => { placing = -1; $("crop-tools").hidden = !$("crop-enabled").checked; drawSelection(); });
$("place-corners").addEventListener("click", () => { placing = 0; announce("Sur l’image, placez le coin 1 : haut gauche."); });

function announce(message, kind = "") {
  status.textContent = message;
  status.className = `status ${kind}`;
}
function updateActions() {
  const available = !busy && text.value.length > 0;
  $("copy").disabled = !available;
  $("download").disabled = !available;
  $("download-json").disabled = busy || !retainedFields;
  const count = Object.values(fieldInputs).filter(field => field.value.trim()).length;
  $("count").textContent = retainedFields ? `${count}/7 champs renseignés` : "En attente d’une image";
}
function clearImage() {
  if (previewURL) URL.revokeObjectURL(previewURL);
  previewURL = null;
  selected = null;
  sourceImage = null; rotation = 0; corners = fullCorners(); placing = -1;
  canvas.hidden = true; $("adjustments").disabled = true;
  $("crop-enabled").checked = false; $("crop-tools").hidden = true;
  showFields(null);
  preview.removeAttribute("src");
  preview.hidden = true;
  $("upload-content").hidden = false;
  $("change-image").hidden = true;
  text.value = "";
  text.disabled = true;
  $("extract").disabled = true;
  $("image-help").textContent = "Une image à la fois, jusqu’à 20 millions de pixels.";
  updateActions();
}
async function selectFile(file) {
  if (busy || !file) return;
  clearImage();
  if (!["image/png", "image/jpeg"].includes(file.type)) {
    announce("Choisissez une image PNG ou JPEG.", "error"); return;
  }
  if (file.size > 10 * 1024 * 1024 || file.size === 0) {
    announce("L’image doit être non vide et ne pas dépasser 10 Mio.", "error"); return;
  }
  const url = URL.createObjectURL(file);
  previewURL = url;
  const probe = new Image();
  probe.src = url;
  try {
    await probe.decode();
    if (previewURL !== url) return;
    if (probe.naturalWidth * probe.naturalHeight > 20_000_000) throw new Error("L’image dépasse 20 millions de pixels. Réduisez ses dimensions.");
    selected = file;
    preview.src = url;
    sourceImage = probe; canvas.hidden = false; $("adjustments").disabled = false; drawSelection(); updateEngine();
    $("upload-content").hidden = true;
    $("change-image").hidden = false;
    $("image-help").textContent = `${file.name} · ${(file.size / 1024 / 1024).toLocaleString("fr-FR", {maximumFractionDigits: 2})} Mio`;
    $("extract").disabled = false;
    announce("Image prête. Vérifiez la langue, puis lancez l’extraction.");
  } catch (error) {
    if (previewURL !== url) return;
    clearImage();
    announce(error.message.startsWith("L’image dépasse") ? error.message : "Impossible de lire cette image. Essayez un autre fichier.", "error");
  }
}
input.addEventListener("change", () => { const file = input.files[0]; input.value = ""; selectFile(file); });
const dropzone = $("dropzone");
for (const name of ["dragenter", "dragover"]) dropzone.addEventListener(name, (event) => {
  event.preventDefault(); if (!busy) dropzone.classList.add("dragging");
});
for (const name of ["dragleave", "drop"]) dropzone.addEventListener(name, (event) => {
  event.preventDefault(); dropzone.classList.remove("dragging");
});
dropzone.addEventListener("drop", (event) => {
  if (busy) return;
  if (event.dataTransfer.files.length !== 1) {
    announce("Déposez une seule image à la fois.", "error"); return;
  }
  selectFile(event.dataTransfer.files[0]);
});
$("ocr-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selected || busy) return;
  const originalText = text.value, wasDisabled = text.disabled;
  const engine = $("engine").value;
  busy = true;
  $("engine").disabled = true;
  text.disabled = true; $("adjustments").disabled = true;
  $("fields").disabled = true;
  input.disabled = true; $("language").disabled = true; $("extract").disabled = true;
  $("extract").textContent = "Extraction en cours…";
  document.querySelector(".result").setAttribute("aria-busy", "true");
  updateActions();
  announce("Lecture de l’image en cours. Cela peut prendre quelques secondes.", "busy");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), engine === "paddleocr" ? 105000 : 40000);
  try {
    const form = new FormData();
    form.append("image", selected); form.append("language", $("language").value);
    form.append("engine", engine);
    form.append("structured", "true");
    form.append("options", JSON.stringify({rotation, corners: $("crop-enabled").checked ? corners : null, mode: $("processing").value, layout: $("layout").value, deskew: $("deskew").checked}));
    const response = await fetch("/api/ocr", {method: "POST", body: form, signal: controller.signal});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message || "L’extraction a échoué. Réessayez.");
    if (!data.fields) throw new Error("La version du serveur ne fournit pas les champs. Mettez à jour puis redémarrez l’application.");
    showFields(data.fields, data.engine);
    text.disabled = false;
    announce(data.text ? "Champs repérés. Vérifiez les propositions ; les autres informations sont écartées." : "Aucun des sept champs n’a été repéré avec une valeur. Vérifiez l’image ou renseignez les champs manuellement.");
    fieldInputs.nom.focus();
  } catch (error) {
    text.value = originalText; text.disabled = wasDisabled;
    announce(error.name === "AbortError" ? "Le délai d’attente est dépassé. Réessayez avec une image plus petite." : error.message === "Failed to fetch" ? "Le service local ne répond pas. Vérifiez qu’il est démarré, puis réessayez." : error.message, "error");
  } finally {
    clearTimeout(timer);
    busy = false; input.disabled = false; $("language").disabled = false;
    $("engine").disabled = false;
    $("adjustments").disabled = false;
    $("fields").disabled = !retainedFields;
    $("extract").disabled = !selected;
    $("extract").textContent = "Repérer les champs →";
    document.querySelector(".result").setAttribute("aria-busy", "false");
    updateActions();
    updateEngine();
  }
});
text.addEventListener("input", updateActions);
$("copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(text.value);
    announce("Texte copié dans le presse-papiers.");
  } catch {
    document.querySelector(".retained-summary").open = true;
    text.focus(); text.select();
    announce("Copie automatique indisponible. Le texte est sélectionné : utilisez Ctrl+C ou Cmd+C.");
  }
});
$("download").addEventListener("click", () => {
  const url = URL.createObjectURL(new Blob([text.value], {type: "text/plain;charset=utf-8"}));
  const link = document.createElement("a");
  link.href = url; link.download = "champs-retenus.txt"; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  announce("Le fichier texte a été préparé pour le téléchargement.");
});
$("download-json").addEventListener("click", () => {
  const fields = Object.fromEntries(Object.entries(fieldNames).map(([key, label]) => {
    const value = fieldInputs[key].value.trim();
    return [key, {libelle: label, valeur: value, statut: value !== retainedFields[key].value ? "modifie_manuellement" : retainedFields[key].status}];
  }));
  const url = URL.createObjectURL(new Blob([JSON.stringify({moteur: retainedEngine, champs: fields}, null, 2)], {type: "application/json;charset=utf-8"}));
  const link = document.createElement("a"); link.href = url; link.download = "champs-retenus.json"; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  announce("Export JSON des sept champs préparé.");
});
fetch("/health").then((response) => {
  if (!response.ok && !selected) announce("Le moteur OCR n’est pas prêt. Consultez le guide d’installation.", "error");
}).catch(() => { if (!selected) announce("Le service local est indisponible. Vérifiez son démarrage.", "error"); });
$("engine").addEventListener("change", updateEngine);
fetch("/api/engines").then(response => response.json()).then(data => { paddleAvailable = data.paddleocr.ready; updateEngine(); }).catch(() => { paddleAvailable = null; });
