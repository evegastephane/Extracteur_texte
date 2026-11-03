"use strict";
const $ = (id) => document.getElementById(id);
const input = $("image"), preview = $("preview"), text = $("text"), status = $("status");
let selected = null, previewURL = null, busy = false;

function announce(message, kind = "") {
  status.textContent = message;
  status.className = `status ${kind}`;
}
function updateActions() {
  const available = !busy && text.value.length > 0;
  $("copy").disabled = !available;
  $("download").disabled = !available;
  $("count").textContent = text.disabled ? "Prêt à être extrait" : `${text.value.length.toLocaleString("fr-FR")} caractères`;
}
function clearImage() {
  if (previewURL) URL.revokeObjectURL(previewURL);
  previewURL = null;
  selected = null;
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
    preview.hidden = false;
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
  busy = true;
  text.value = ""; text.disabled = true;
  input.disabled = true; $("language").disabled = true; $("extract").disabled = true;
  $("extract").textContent = "Extraction en cours…";
  document.querySelector(".result").setAttribute("aria-busy", "true");
  updateActions();
  announce("Lecture de l’image en cours. Cela peut prendre quelques secondes.", "busy");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 40000);
  try {
    const form = new FormData();
    form.append("image", selected); form.append("language", $("language").value);
    const response = await fetch("/api/ocr", {method: "POST", body: form, signal: controller.signal});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message || "L’extraction a échoué. Réessayez.");
    text.value = data.text;
    text.disabled = false;
    announce(data.text ? "Texte extrait. Relisez-le : la reconnaissance peut comporter des erreurs." : "Aucun texte détecté. Essayez une image plus nette ou une autre langue.");
    text.focus();
  } catch (error) {
    announce(error.name === "AbortError" ? "Le délai d’attente est dépassé. Réessayez avec une image plus petite." : error.message === "Failed to fetch" ? "Le service local ne répond pas. Vérifiez qu’il est démarré, puis réessayez." : error.message, "error");
  } finally {
    clearTimeout(timer);
    busy = false; input.disabled = false; $("language").disabled = false;
    $("extract").disabled = !selected;
    $("extract").textContent = "Extraire le texte →";
    document.querySelector(".result").setAttribute("aria-busy", "false");
    updateActions();
  }
});
text.addEventListener("input", updateActions);
$("copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(text.value);
    announce("Texte copié dans le presse-papiers.");
  } catch {
    text.focus(); text.select();
    announce("Copie automatique indisponible. Le texte est sélectionné : utilisez Ctrl+C ou Cmd+C.");
  }
});
$("download").addEventListener("click", () => {
  const url = URL.createObjectURL(new Blob([text.value], {type: "text/plain;charset=utf-8"}));
  const link = document.createElement("a");
  link.href = url; link.download = "texte-extrait.txt"; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  announce("Le fichier texte a été préparé pour le téléchargement.");
});
fetch("/health").then((response) => {
  if (!response.ok && !selected) announce("Le moteur OCR n’est pas prêt. Consultez le guide d’installation.", "error");
}).catch(() => { if (!selected) announce("Le service local est indisponible. Vérifiez son démarrage.", "error"); });
