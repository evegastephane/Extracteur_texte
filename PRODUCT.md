# Extracteur — Champs par libellés

Application web locale en français pour repérer exactement sept champs à partir de libellés français/anglais et de règles spatiales. Aucun modèle d’extraction n’est entraîné ; aucun LLM ni API d’IA externe n’intervient. Flask, Pillow et OpenCV préparent l’image ; Tesseract reste le moteur OCR spécialisé par défaut. PaddleOCR est optionnel.

## Périmètre et parcours

Les seules clés de champs sont `nom`, `prenoms`, `date_naissance`, `lieu_naissance`, `sexe`, `taille` et `profession`. Les valeurs sont recherchées à droite du libellé, puis en dessous dans la même colonne ; les libellés voisins et les grands écarts spatiaux bornent la recherche. Les autres informations OCR sont écartées du résultat normal, de la copie et des exports. Ces règles peuvent néanmoins associer un mauvais texte à un champ : il ne s’agit pas d’une garantie générale de précision ou de confidentialité.

1. Importer une image PNG/JPEG (une à la fois, 10 Mio et 20 millions de pixels maximum).
2. Ajuster au besoin rotation, quatre coins horaires par poignées ou coordonnées clavier, filtre Original/Photo/Noir et blanc adaptatif et légère inclinaison (±12°). Une sélection doit inclure le libellé et sa valeur. L’aperçu montre la géométrie, pas les filtres.
3. Choisir le moteur. Tesseract propose langue française/anglaise et disposition auto/bloc/dispersée/ligne ; PaddleOCR désactive ces deux réglages et conserve sa segmentation automatique avec modèle latin.
4. Relire et corriger les sept propositions. Le résumé est en lecture seule. Copier ou exporter en TXT reprend seulement les champs renseignés ; le JSON contient les sept clés de champs, valeurs et statuts, avec le moteur utilisé.

Les statuts `propose`, `non_trouve` et `a_verifier` distinguent candidat, absence et doute/conflit. Les conflits restent vides avec candidats consultables ; les formats suspects sont signalés. Les indices de libellé et position restent limités au champ concerné, sans texte OCR intégral. Les métadonnées de normalisation date/sexe/taille ne corrigent pas automatiquement la valeur reconnue. Une correction exportée est marquée `modifie_manuellement`.

Une nouvelle image efface les propositions et corrections. Une extraction réussie remplace les sept champs ; un échec conserve les corrections. L’ancien ajout libre de zones n’est plus présenté.

## API et traitement local

`POST /api/ocr` utilise `structured=true` par défaut : résumé filtré, exactement sept clés dans `fields`, moteur et langue. L’interface demande toujours ce mode. Le texte brut reste accessible uniquement par le mode technique explicite `structured=false`, pour compatibilité avec les mesures OCR ; la restriction des sept champs ne s’applique donc pas à cette option. Aucun stockage des champs ou documents n’est ajouté.

Le navigateur communique avec le serveur local lié à `127.0.0.1`, sans envoi de documents à un service externe. Les fichiers temporaires sont supprimés après traitement ; les résultats restent dans la page jusqu’au nouvel import ou à sa fermeture, sauf copie ou export volontaire. Le sous-processus Tesseract est limité à 30 secondes, hors prétraitement ; PaddleOCR à 90 secondes, imports et chargement compris. Les images de travail sont bornées à 8 millions de pixels et 8 000 pixels sur le plus grand côté.

## Moteur optionnel et limites

PaddleOCR utilise `.venv-paddle` et des modèles neuronaux OCR locaux, téléchargés lors de la préparation. Aucun basculement silencieux vers Tesseract n’a lieu. Les bibliothèques s’importent sous Linux, mais les téléchargements officiels des poids sont bloqués par HTTP 403 : inférence réelle, extraction hors ligne et précision PaddleOCR restent non validées. Les intégrations de polygones sont testées avec des sorties simulées. La validation native Windows reste à effectuer.

Sans libellé reconnu, aucune identité, sexe ou profession n’est deviné. Flou, reflets, libellés mal lus et dispositions inconnues peuvent fausser les associations. Les règles ne reconnaissent pas la personne représentée et n’établissent pas une précision sur des documents réels.

## Vérification actuelle

93 tests réussis, 1 test réel PaddleOCR ignoré faute de modèles. Une image synthétique vérifie réellement les sept champs avec Tesseract et l’exclusion d’un marqueur de numéro de carte. Chromium vérifie les corrections, les exports TXT/JSON et le mobile. Les deux constats de revue concernant les suffixes sur une ligne et les identifiants sur plusieurs lignes sont résolus ; six contrôles de régression indépendants ont confirmé les corrections. Le test navigateur final et les captures `.test-artifacts/desktop-fields-result.png` et `.test-artifacts/mobile-fields-result.png` ont été vérifiés. Le précédent benchmark CER synthétique mesure l’OCR Tesseract, pas la précision générale de cette extraction structurée ni celle de PaddleOCR.

Références : [règles, API et limites](docs/FIELDS.md), [préparation](docs/ACCURACY.md), [PaddleOCR](docs/PADDLEOCR.md), [installation](README.md), [système visuel](DESIGN.md).
