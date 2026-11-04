"use strict";
const $ = id => document.getElementById(id);
const fieldNames = {nom:"Nom", prenoms:"Prénoms", date_naissance:"Date de naissance", lieu_naissance:"Lieu de naissance", sexe:"Sexe", taille:"Taille", profession:"Profession"};
let step = 1, busy = false, result = null;
const photos = {recto: null, verso: null}, fieldInputs = {};
const side = () => step === 1 ? "recto" : "verso";
const announce = (message, error = false) => { $("status").textContent = message; $("status").className = error ? "status error" : "status"; };
for (const [key, name] of Object.entries(fieldNames)) {
  const group = document.createElement("div"); group.className = "field";
  const label = document.createElement("label"); label.htmlFor = `field-${key}`; label.textContent = name;
  const input = document.createElement("input"); input.id = `field-${key}`; input.type = "text"; input.maxLength = 200; input.autocomplete = "off"; input.spellcheck = false;
  const note = document.createElement("small"); note.id = `note-${key}`; input.setAttribute("aria-describedby", note.id);
  input.addEventListener("input", () => { group.dataset.state = "modifie"; note.textContent = "Modifié manuellement — à vérifier sur la carte."; updateCount(); });
  group.append(label, input, note); $("field-list").append(group); fieldInputs[key] = input;
}
function updateCount() {
  const count = Object.values(fieldInputs).filter(input => input.value.trim()).length;
  $("count").textContent = `${count}/7 champs renseignés`;
  $("copy").disabled = count === 0; $("download").disabled = count === 0;
}
function discardPhoto(key) {
  if (photos[key]) URL.revokeObjectURL(photos[key].url);
  photos[key] = null;
}
function clearResult() {
  result = null;
  for (const input of Object.values(fieldInputs)) input.value = "";
  $("result-front").removeAttribute("src"); $("result-back").removeAttribute("src");
  document.querySelector(".photos").open = false;
}
function renderStep(focus = true) {
  $("upload-step").hidden = step === 3;
  $("result-step").hidden = step !== 3 || !result;
  $("loading-step").hidden = true;
  for (let n = 1; n <= 3; n++) {
    if (n === step) $(`step-${n}`).setAttribute("aria-current", "step");
    else $(`step-${n}`).removeAttribute("aria-current");
  }
  if (step < 3) {
    const key = side(), photo = photos[key];
    $("upload-title").textContent = `Ajoutez le ${key}`;
    $("side-count").textContent = `Photo ${step} sur 2`;
    $("choose-label").textContent = `Choisir le ${key}`;
    $("upload-instruction").textContent = step === 1 ? "Photographiez la face qui porte le nom et le portrait, avec les quatre coins visibles." : "Ajoutez maintenant l’autre face de la même carte.";
    $("back-notice").hidden = step !== 2;
    $("back").hidden = step === 1;
    $("return-results").hidden = !result;
    $("preview").hidden = !photo; $("empty-upload").hidden = !!photo; $("photo-tools").hidden = !photo;
    if (photo) $("preview").src = photo.url;
    else $("preview").removeAttribute("src");
    $("next").disabled = busy || !photo;
    if (focus) $("upload-title").focus();
  } else if (focus) $("result-title").focus();
}
function setBusy(value) {
  busy = value;
  for (const id of ["image", "back", "return-results", "change-photo", "flip-photo", "next"]) $(id).disabled = value;
  if (!value && step < 3) $("next").disabled = !photos[side()];
  $("upload-step").setAttribute("aria-busy", String(value));
}
async function requestJSON(url, body, timeout) {
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, {method:"POST", body, signal:controller.signal});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error?.message || "Le traitement a échoué. Réessayez.");
    return payload;
  } finally { clearTimeout(timer); }
}
function errorMessage(error) {
  if (error.name === "AbortError") return "Le traitement a dépassé le délai d’attente. Les photos restent disponibles pour réessayer.";
  if (error instanceof TypeError) return "Le service local ne répond pas. Vérifiez qu’il est démarré.";
  return error.message;
}
async function upload(file) {
  if (!file || busy || step === 3) return;
  if (!file.size || file.size > 10 * 1024 * 1024) { announce("Choisissez une photo non vide de 10 Mio maximum.", true); return; }
  if (file.type && !["image/png", "image/jpeg"].includes(file.type)) { announce("Choisissez une photo PNG ou JPEG.", true); return; }
  const key = side(); setBusy(true); announce("Recadrage automatique de la carte en cours…");
  try {
    const form = new FormData(); form.append("image", file);
    const data = await requestJSON("/api/cni/align", form, 30000);
    const bytes = Uint8Array.from(atob(data.image), char => char.charCodeAt(0));
    const blob = new Blob([bytes], {type:"image/png"});
    discardPhoto(key); photos[key] = {blob, url:URL.createObjectURL(blob)};
    // A changed front invalidates the old back; never combine different cards.
    if (key === "recto") discardPhoto("verso");
    clearResult(); renderStep(false);
    announce(data.alignment.method === "image_cadree" ? "Vérifiez que la carte occupe tout le cadre et que le texte est à l’endroit, puis appuyez sur Suivant." : "Carte recadrée. Vérifiez que les quatre bords sont présents et que le texte est à l’endroit, puis appuyez sur Suivant.");
  } catch (error) {
    announce(errorMessage(error) + (photos[key] ? " La photo précédente est conservée." : ""), true);
  } finally { setBusy(false); }
}
$("image").addEventListener("change", () => { const file = $("image").files[0]; $("image").value = ""; upload(file); });
$("change-photo").addEventListener("click", () => $("image").click());
for (const name of ["dragenter", "dragover"]) $("dropzone").addEventListener(name, event => { event.preventDefault(); if (!busy) $("dropzone").classList.add("dragging"); });
for (const name of ["dragleave", "drop"]) $("dropzone").addEventListener(name, event => { event.preventDefault(); $("dropzone").classList.remove("dragging"); });
$("dropzone").addEventListener("drop", event => { if (event.dataTransfer.files.length !== 1) announce("Ajoutez une seule face à la fois.", true); else upload(event.dataTransfer.files[0]); });
$("flip-photo").addEventListener("click", async () => {
  if (busy || !photos[side()]) return;
  const key = side(); setBusy(true);
  try {
    const bitmap = await createImageBitmap(photos[key].blob), canvas = document.createElement("canvas");
    canvas.width = bitmap.width; canvas.height = bitmap.height;
    const context = canvas.getContext("2d"); context.translate(canvas.width, canvas.height); context.rotate(Math.PI); context.drawImage(bitmap, 0, 0); bitmap.close();
    const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
    if (!blob) throw new Error("Impossible de retourner cette photo.");
    discardPhoto(key); photos[key] = {blob, url:URL.createObjectURL(blob)};
    clearResult(); renderStep(false); announce("Image retournée. Vérifiez le sens du texte.");
  } catch (error) { announce(errorMessage(error), true); }
  finally { setBusy(false); }
});
$("back").addEventListener("click", () => { if (!busy) { step = 1; renderStep(); announce("Vous pouvez revoir le recto."); } });
$("next").addEventListener("click", async () => {
  if (busy || !photos[side()]) return;
  if (step === 1) { step = 2; renderStep(); announce("Ajoutez le verso de la même carte."); return; }
  if (result) { step = 3; renderStep(); announce("Photos inchangées : vos corrections sont conservées."); return; }
  setBusy(true); step = 3; renderStep(false); $("loading-step").hidden = false; $("result-step").hidden = true; $("loading-title").focus();
  announce("PaddleOCR lit les sept zones prédéfinies du recto…");
  try {
    const form = new FormData(); form.append("recto", photos.recto.blob, "recto.png"); form.append("verso", photos.verso.blob, "verso.png");
    const data = await requestJSON("/api/cni/read", form, 105000);
    if (!data.fields || Object.keys(fieldNames).some(key => !data.fields[key])) throw new Error("Le serveur n’a pas renvoyé les sept champs attendus.");
    $("engine-warning").hidden = true;
    result = data;
    for (const key of Object.keys(fieldNames)) {
      const field = data.fields[key]; fieldInputs[key].value = field.value || "";
      fieldInputs[key].parentElement.dataset.state = field.status;
      $(`note-${key}`).textContent = field.message;
    }
    $("result-front").src = photos.recto.url; $("result-back").src = photos.verso.url;
    updateCount(); renderStep(); announce("Lecture terminée. Vérifiez les valeurs proposées avant de les exporter.");
  } catch (error) { step = 2; renderStep(); announce(errorMessage(error), true); }
  finally { setBusy(false); }
});
function retainedText() { return Object.entries(fieldNames).filter(([key]) => fieldInputs[key].value.trim()).map(([key, name]) => `${name} : ${fieldInputs[key].value.trim()}`).join("\n"); }
function download(content, type, filename) {
  const url = URL.createObjectURL(new Blob([content], {type})), link = document.createElement("a");
  link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText(retainedText()); announce("Champs copiés."); }
  catch { announce("Le presse-papiers n’est pas disponible. Utilisez l’export TXT.", true); }
});
$("download").addEventListener("click", () => { download(retainedText(), "text/plain;charset=utf-8", "champs-cni.txt"); announce("Export TXT préparé."); });
$("download-json").addEventListener("click", () => {
  const fields = Object.fromEntries(Object.entries(fieldNames).map(([key, label]) => [key, {libelle:label, valeur:fieldInputs[key].value.trim(), statut:fieldInputs[key].value.trim() !== result.fields[key].value ? "modifie_manuellement" : result.fields[key].status}]));
  download(JSON.stringify({moteur:"paddleocr", gabarit:result.profile, champs:fields}, null, 2), "application/json;charset=utf-8", "champs-cni.json"); announce("Export JSON préparé.");
});
$("review-photos").addEventListener("click", () => { step = 1; renderStep(); announce("Les corrections sont conservées tant que les photos ne changent pas."); });
$("return-results").addEventListener("click", () => { if (!busy && result) { step = 3; renderStep(); announce("Corrections précédentes conservées."); } });
$("restart").addEventListener("click", () => { discardPhoto("recto"); discardPhoto("verso"); clearResult(); step = 1; renderStep(); announce("Ajoutez le recto de la nouvelle carte."); });
fetch("/api/cni/status").then(response => response.json()).then(data => { $("engine-warning").hidden = data.ready; }).catch(() => { announce("Le service local n’est pas disponible. Vérifiez son démarrage.", true); });
renderStep(false);
