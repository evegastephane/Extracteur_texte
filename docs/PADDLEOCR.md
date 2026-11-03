# PaddleOCR optionnel

PaddleOCR est proposé en complément de Tesseract, sans remplacer l’installation légère par défaut. Il peut mieux lire certaines photos, mais n’est pas systématiquement plus précis. Comparer les deux moteurs sur les mêmes images avant de choisir.

## Installation Windows

Prérequis : Python 3.12 **64 bits**, Windows x64, connexion Internet pendant l’installation. Depuis PowerShell dans le projet, arrêter le serveur puis :

```powershell
git pull origin main
py -3.12 -m venv .venv-paddle
.\.venv-paddle\Scripts\python.exe -m pip install -r requirements-paddle.txt
.\.venv-paddle\Scripts\python.exe scripts/setup_paddle.py
.\.venv\Scripts\python.exe -m app
```

Après la réussite du test synthétique affiché par le script, actualiser le navigateur (Ctrl+F5) et choisir **PaddleOCR — optionnel**. L’application principale continue d’utiliser `.venv` ; `.venv-paddle` sert seulement au sous-processus OCR. Ne pas installer ces dépendances dans `.venv`, afin d’éviter les conflits OpenCV/PaddleX.

La validation native Windows reste à effectuer. Si une dépendance native ne charge pas, vérifier Python x64 et le runtime Microsoft Visual C++ requis par PaddlePaddle ; consulter son [guide officiel](https://www.paddlepaddle.org.cn/documentation/docs/en/install/index_en.html). Aucune clé API n’est nécessaire. Le moteur Tesseract reste disponible si PaddleOCR n’est pas préparé.

## Linux

```sh
python3 -m venv .venv-paddle
.venv-paddle/bin/python -m pip install -r requirements-paddle.txt
.venv-paddle/bin/python scripts/setup_paddle.py
.venv/bin/python -m app
```

PaddleOCR 3.3.3, PaddlePaddle CPU 3.2.2 et PaddleX 3.3.13 sont épinglés. L’environnement optionnel est nettement plus volumineux (plusieurs centaines de Mo à plusieurs Go selon la plateforme) et consomme davantage de mémoire. Aucun GPU n’est requis.

## Modèles et confidentialité

Les modèles officiels choisis sont `PP-OCRv5_mobile_det` (détection) et `latin_PP-OCRv5_mobile_rec` (reconnaissance française et anglaise). La langue et les réglages de disposition propres à Tesseract sont désactivés dans l’interface lorsque PaddleOCR est sélectionné. Rotation, recadrage, perspective et filtres restent communs aux deux moteurs.

Le script télécharge uniquement deux archives depuis `paddle-model-ecology.bj.bcebos.com`, par HTTPS avec vérification TLS. Il refuse les archives excessives, les liens et les chemins dangereux. Les modèles sont préparés dans un répertoire temporaire et activés seulement après un test réel sur une image synthétique `LOCAL OCR 123`. Leur manifeste local conserve les URL, les SHA-256 des archives et ceux des fichiers. Ces empreintes sont calculées après téléchargement depuis la source officielle TLS, pas comparées à une signature indépendante de l’éditeur. L’application vérifie ensuite l’intégrité des fichiers avant usage.

Les modèles restent dans `.ocr-data/paddle/`, ignoré par Git. Le script peut être relancé pour retester les modèles existants ; il refuse de remplacer des modèles dont le manifeste est absent ou incohérent. Préserver ou renommer ce dossier avant une réinstallation si nécessaire.

Pendant l’extraction, les chemins des deux modèles sont explicites et les modèles supplémentaires d’orientation/redressement Paddle sont désactivés. Aucun téléchargement automatique n’est demandé. La sonde de connexion aux hébergeurs de modèles est désactivée pour cet usage local, sans désactiver TLS. Les images, résultats et caches PaddleX de la requête sont placés dans un répertoire temporaire privé, supprimé en succès, échec et expiration. Les journaux du worker ne sont ni conservés ni renvoyés, car ils pourraient contenir du texte reconnu.

## Délais et erreurs

Chaque extraction PaddleOCR démarre un sous-processus CPU séparé. Le plafond est de 90 secondes, incluant imports et chargement des modèles ; le navigateur attend jusqu’à 105 secondes. Ce choix borne la durée et libère la mémoire après traitement, au prix d’un chargement des modèles à chaque extraction. La file reste limitée à une extraction active, quel que soit le moteur. Aucun basculement silencieux vers Tesseract : le choix de l’utilisateur est respecté, et une erreur claire s’affiche si PaddleOCR est indisponible.

Le résultat n’expose pas de score de précision globale : les scores internes d’un modèle ne prouvent pas l’exactitude du texte. Relire les champs importants.

## API et comparaison

`GET /api/engines` décrit les deux moteurs sans charger Paddle dans Flask. Le statut Paddle indique qu’un environnement existe et que les modèles correspondent au manifeste d’une préparation testée ; il ne remplace pas la vérification d’une extraction sur la machine courante.

`POST /api/ocr` accepte `engine=tesseract` (valeur par défaut) ou `engine=paddleocr`, en plus d’`image`, `language` et `options`. PaddleOCR utilise le modèle latin pour les trois choix de langue existants ; la segmentation est automatique et ignore `options.layout`. Les erreurs d’installation retournent HTTP 503, le délai dépassé HTTP 504 et un moteur inconnu HTTP 400.

Après préparation réussie, depuis l’environnement principal :

```powershell
.\.venv\Scripts\python.exe -m scripts.benchmark --engine tesseract --output .test-artifacts/tesseract.json
.\.venv\Scripts\python.exe -m scripts.benchmark --engine paddleocr --output .test-artifacts/paddleocr.json
```

Sur Linux, remplacer l’exécutable par `.venv/bin/python`. Comparer les CER sur les mêmes exemples synthétiques, puis sur un jeu réel autorisé et anonymisé. Les résultats Tesseract existants ne sont pas des résultats PaddleOCR.

## État de validation dans l’environnement cloud

Les bibliothèques PaddleOCR et PaddlePaddle s’importent réellement sous Linux. Les tests du protocole worker, des erreurs, délais, nettoyages et empreintes utilisent des simulations explicites ; ils ne valident pas la précision du modèle. Le téléchargement officiel des poids reste bloqué par le proxy (HTTP 403). L’extraction réelle PaddleOCR et le benchmark comparatif sont donc **non exécutés**, et aucun gain de précision n’est revendiqué.

L’ajout de `paddle-model-ecology.bj.bcebos.com` est sauvegardé dans le brouillon réseau de l’environnement. Pour lever ce blocage cloud, examiner et enregistrer les paramètres, puis publier l’environnement et relancer la préparation. Cette restriction cloud n’établit pas que le téléchargement sera bloqué sur votre ordinateur Windows.

PaddleOCR, PaddlePaddle et PaddleX utilisent des licences Apache-2.0 ; leurs dépendances conservent leurs propres licences.
