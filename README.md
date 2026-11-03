# Extracteur de texte

Une application locale et légère pour récupérer le texte d’une image PNG ou JPEG. Interface en français, OCR français/anglais, résultat modifiable, copie et export `.txt` UTF-8. Fonctionne hors ligne après installation, sans compte ni API d’IA externe.

## Installation

Cible testée : Linux, Python 3.12, Tesseract 5. Prérequis : Python avec `venv`, Tesseract, `curl` et `sha256sum`. Sur Debian/Ubuntu, si nécessaire :

```sh
sudo apt-get update
sudo apt-get install python3-venv tesseract-ocr curl
```

Dans le dossier du projet :

```sh
bash scripts/setup.sh
.venv/bin/python -m app
```

Ouvrez l’adresse locale affichée dans le terminal, sur le port 8000. Le serveur écoute uniquement sur `127.0.0.1` et ne doit pas être exposé sur Internet. Arrêt avec Ctrl+C.

Le script installe les dépendances Python et télécharge les données officielles Tesseract `tessdata_fast`, versionnées et contrôlées par SHA-256, dans `.ocr-data/` (ignoré par Git). Il peut être relancé. Les données OCR sont conservées entre les lancements ; aucun téléchargement n’est effectué pendant l’extraction. Une variable `TESSDATA_PREFIX` déjà définie est respectée : elle doit alors désigner des données compatibles contenant `fra` et `eng`.

## Utilisation

1. Choisir ou déposer une image PNG/JPEG, jusqu’à 10 Mio et 20 millions de pixels.
2. Sélectionner la langue et lancer l’extraction.
3. Relire et corriger le résultat, puis le copier ou l’exporter.

Une image à la fois. Le texte imprimé net donne les meilleurs résultats ; les manuscrits, tableaux complexes et photos floues ne sont pas pris en charge de manière fiable. Une reconnaissance vide est signalée. Le traitement est limité à 30 secondes ; un nouvel import efface le résultat précédent.

Les images transitent uniquement entre le navigateur et le serveur local. Le moteur utilise des fichiers temporaires supprimés par pytesseract en succès comme en échec. L’application ne conserve ni historique ni contenu dans ses journaux. Le texte reste dans la page jusqu’au nouvel import ou à sa fermeture, sauf copie ou export volontaire.

Tesseract utilise des modèles OCR spécialisés, notamment neuronaux : aucun modèle génératif, chatbot ou service distant n’est intégré.

## Développement et tests

```sh
.venv/bin/python -m pytest -q
```

Les tests génèrent des images synthétiques avec Pillow, puis exercent l’API et le vrai moteur OCR. Sur Linux, la police DejaVu Sans est requise pour ces fixtures (`fonts-dejavu-core` sur Debian/Ubuntu). Le reste couvre formats et tailles invalides, langues, sécurité locale, concurrence et erreurs. Les tests OCR ne sont pas remplacés par des simulations.

Test navigateur facultatif : installer Playwright dans un environnement Python disposant aussi de Pillow, puis lancer `python tests/browser_smoke.py` avec le serveur démarré et Chromium installé à `/usr/bin/chromium`. Ce test vérifie l’OCR réel sur deux tailles d’écran, la correction, le presse-papiers, le téléchargement et les états d’erreur. Il garde ses captures dans `.test-artifacts/`, ignoré par Git.

```sh
# Contrôle des prérequis sans envoyer de document
curl --fail http://127.0.0.1:8000/health
# Extraction d’une image locale
curl --fail -F image=@image.png -F language=fra http://127.0.0.1:8000/api/ocr
```

Architecture : Flask, Waitress, Pillow, pytesseract et Tesseract. Aucun build frontend ni base de données. Voir les [documents BRS, PRD, SRS et SAD](docs/README.md).

## Licence

Code du projet sous [licence MIT](LICENSE). Les dépendances conservent leurs licences : Flask/Waitress (BSD), Pillow (HPND), pytesseract/Tesseract et données tessdata_fast (Apache-2.0). Les données OCR téléchargées ne sont pas incluses dans le dépôt ; leur [licence officielle](https://github.com/tesseract-ocr/tessdata_fast/blob/87416418657359cb625c412a48b6e1d6d41c29bd/LICENSE) s’applique.

Les objectifs complets de précision, temps et mémoire du SRS restent à mesurer sur son jeu de référence avant de déclarer une conformité complète.
