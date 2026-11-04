# Extracteur CNI camerounaise

Une application locale avec un parcours simple : **recto → verso → résultats**. PaddleOCR lit les valeurs dans sept zones prédéfinies après alignement de la carte. Aucun réglage de moteur, filtre, langue ou coordonnées n’est demandé dans l’interface.

Les seules informations retenues sont : nom, prénoms, date et lieu de naissance, sexe, taille et profession. Les propositions restent modifiables et exportables en TXT/JSON.

**Périmètre actuel :** un gabarit provisoire du recto à puce illustré par l’utilisateur. La classification ancien/nouveau est différée. Les références recto et verso du même type de carte sont maintenant décrites dans le gabarit. Les zones du verso sont réservées à la calibration : elles ne sont pas lues ni exportées car elles ne font pas partie des sept champs demandés. Le second modèle reste non défini. Voir [les zones et limites](docs/CNI_ZONES.md).

## Mettre à jour sur Windows

Arrêter le serveur avec Ctrl+C, puis, depuis PowerShell dans le projet :

```powershell
git pull origin main
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-paddle\Scripts\python.exe -m pip install -r requirements-paddle.txt
.\.venv-paddle\Scripts\python.exe scripts/setup_paddle.py
.\.venv\Scripts\python.exe -m app
```

Le script vérifie les empreintes des modèles existants puis teste uniquement la reconnaissance directe des sept zones. Le test de l’ancien détecteur généraliste est optionnel avec `--check-legacy`. Il ne les télécharge à nouveau que si le dossier n’existe pas. Le marqueur `zone_smoke_test` n’est activé qu’après réussite du test réel. Actualiser le navigateur avec Ctrl+F5.

Si `.venv-paddle` n’existe pas, le créer d’abord :

```powershell
py -3.12 -m venv .venv-paddle
```

La validation native Windows reste à effectuer dans cet environnement de développement Linux. Prérequis cible : Python 3.12 x64, Windows x64 et runtime Visual C++ compatible avec PaddlePaddle. Aucun GPU ni clé API requis.

## Nouvelle installation

Sous Windows, avec Python 3.12 installé :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
py -3.12 -m venv .venv-paddle
.\.venv-paddle\Scripts\python.exe -m pip install -r requirements-paddle.txt
.\.venv-paddle\Scripts\python.exe scripts/setup_paddle.py
.\.venv\Scripts\python.exe -m app
```

Sous Linux, utiliser `python3 -m venv` et les exécutables `.venv/bin/python` et `.venv-paddle/bin/python` avec les mêmes commandes pip et script. Paddle reste isolé pour éviter les conflits OpenCV/PaddleX avec l’application Flask.

Ouvrir l’adresse locale affichée dans le terminal sur le port 8000. Le serveur écoute uniquement sur `127.0.0.1`. Il ne doit pas être exposé publiquement. L’interface peut démarrer sans modèles, mais affiche alors un avertissement et refuse clairement la lecture. Tesseract n’est plus requis pour le parcours CNI ; il reste utilisé par les anciens outils et certains tests.

## Utilisation

1. **Recto :** choisir ou déposer une photo PNG/JPEG (10 Mio et 20 millions de pixels maximum). Le programme cherche les contours et redresse la carte. Vérifier les quatre bords et le sens du texte ; « Retourner l’image » corrige un sens inversé. Cliquer sur **Suivant**.
2. **Verso :** ajouter l’autre face de la même carte, vérifier l’aperçu, puis **Suivant**. Un doublon strict des deux photos est refusé. Le verso est seulement recueilli pour relecture dans cette version.
3. **Résultats :** relire et corriger les sept valeurs, puis copier ou exporter. Une lecture incertaine ou un format suspect est signalé. Revoir les photos sans les changer conserve les corrections et ne relance pas l’OCR.

Les photos sombres sont **éclaircies automatiquement après le recadrage**, sans réglage supplémentaire. L’aperçu et les zones OCR utilisent la même image corrigée ; une photo déjà claire est conservée sans modification. Le fichier original n’est pas réécrit. Un manque extrême de lumière ou un reflet peut néanmoins imposer de reprendre la photo.

Un changement de recto efface le verso précédent pour ne pas mélanger deux cartes. Toute modification effective des photos invalide les anciens résultats. « Nouvelle carte » efface la session. Aucun document ni résultat n’est sauvegardé sur le serveur ; seuls les modèles et dépendances sont persistants.

## Ce qui est spécialisé

Le pipeline utilise un gabarit de zones normalisées, pas la recherche de libellés sur toute la carte. Les sept découpes de valeurs sont transmises à **un seul worker et une seule instance `TextRecognition` PaddleOCR**, avec le modèle latin local. Le portrait, la puce et la signature sont en dehors des zones. Les formats sont ensuite vérifiés sans corriger silencieusement les chiffres ou inventer une valeur.

Cela spécialise le **pipeline de lecture et de validation** ; aucun nouveau modèle neuronal camerounais n’est entraîné. Le gabarit a été estimé sur les exemples visuels fournis, sans intégrer leurs photos ou données personnelles dans le dépôt. Sa précision sur des photos réelles reste à mesurer. Une carte d’un autre modèle peut donner des résultats incorrects, car la classification est volontairement différée.

## Développement et validation

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Sur Windows, remplacer l’exécutable par `.\.venv\Scripts\python.exe`. Les tests historiques d’OCR réel nécessitent Tesseract avec `fra` et `eng` et une police DejaVu Sans ou Arial. Les scripts `setup.sh` / `setup.ps1` préparent la base et, si présent, Tesseract ; ils ne remplacent pas la préparation Paddle ci-dessus.

Les tests CNI couvrent le gabarit, l’alignement avec perspective, les sept découpes, les formats, le worker unique, les délais/nettoyages, les doublons et les erreurs. Une substitution **explicite par Tesseract** vérifie réellement que les découpes synthétiques contiennent les bonnes valeurs ; elle ne valide pas PaddleOCR. Les deux tests réels Paddle restent ignorés si les modèles ne sont pas préparés.

Test navigateur facultatif, serveur démarré, avec Playwright/Pillow et Chromium à `/usr/bin/chromium` : `python tests/browser_smoke.py`. Alignement et erreur de modèles manquants sont testés réellement ; la réponse de succès Paddle est simulée pour vérifier l’interface recto/verso/résultats, les corrections et exports sur ordinateur/mobile. Captures dans `.test-artifacts/` ignoré par Git.

Dans l’environnement cloud actuel, l’inférence réelle Paddle reste non validée faute de poids disponibles. Les tests d’interface simulés ne prouvent pas la précision du moteur, ni la qualité du gabarit sur une vraie CNI.

## API

- `POST /api/cni/align` : une partie `image` ; retourne une image PNG alignée encodée en base64 et les informations d’alignement. Aucun OCR.
- `POST /api/cni/read` : deux parties `recto` / `verso` PNG canoniques de 1600 × 1000 ; retourne uniquement les sept champs et les limites du gabarit. PaddleOCR fixe, sans basculement silencieux.
- `GET /api/cni/status` : disponibilité du moteur par zones et périmètre du gabarit.
- `GET /health` : même moteur principal, HTTP 503 tant que la lecture par zones n’est pas prête.

Les anciennes routes `/api/ocr` et `/api/engines` restent disponibles pour compatibilité technique, sans paramètres exposés dans l’interface. Détails : [zones CNI](docs/CNI_ZONES.md), [installation Paddle](docs/PADDLEOCR.md), [documentation générale](docs/README.md).

## Licence

Projet sous [MIT](LICENSE). PaddleOCR/PaddlePaddle/PaddleX et leurs modèles conservent leurs licences officielles ; les dépendances conservent les leurs. Aucun document d’identité réel n’est inclus dans le dépôt.
