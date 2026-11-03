# Extracteur de texte

Application web locale et légère, en français, pour récupérer le texte d’une image avec un moteur OCR open source. Elle utilise Flask, Pillow, OpenCV, pytesseract et Tesseract, sans compte ni service d’IA externe. Tesseract reste le moteur par défaut, avec fonctionnement hors ligne après installation des dépendances et des données de reconnaissance. PaddleOCR est un moteur neuronal local optionnel, dont l’extraction réelle n’est pas encore validée dans cet environnement.

## Parcours et périmètre

1. Choisir ou déposer une seule image PNG/JPEG, jusqu’à 10 Mio et 20 millions de pixels.
2. Si nécessaire, tourner l’image par pas de 90°, sélectionner quatre coins dans le sens horaire (haut gauche, haut droit, bas droit, bas gauche), puis affiner les poignées ou les coordonnées X/Y au clavier. Les coordonnées sont normalisées après orientation.
3. Choisir le moteur, puis le filtre Original, Photo (contraste et réduction du bruit) ou Noir et blanc adaptatif ; activer au besoin la correction d’inclinaison (±12°). Avec Tesseract, choisir la disposition automatique, bloc, dispersée ou ligne (PSM 3/6/11/7), puis la langue Français, Anglais ou Français + Anglais. Avec PaddleOCR, langue et disposition sont désactivées : le modèle latin couvre français et anglais, avec segmentation automatique.
4. Extraire, relire et modifier le texte, le copier ou l’exporter en `.txt` UTF-8. Pour plusieurs zones manuelles, saisir un libellé et cocher explicitement « Ajouter au résultat existant » avant les extractions suivantes. Une extraction échouée conserve le texte précédent et ses corrections ; un nouvel import les efface.

Le navigateur communique avec le serveur local, lié à `127.0.0.1`. Aucun document n’est envoyé à un service externe. L’application ne conserve ni historique ni contenu dans ses journaux. Les fichiers temporaires OCR sont supprimés après traitement ; le résultat reste dans la page jusqu’au nouvel import ou à sa fermeture, sauf copie ou export volontaire.

## Moteur optionnel

PaddleOCR utilise un environnement isolé `.venv-paddle` et des modèles officiels préparés localement. Sa préparation nécessite un téléchargement initial ; aucune API d’IA publique n’est utilisée. Le sélecteur indique si l’installation ou les modèles manquent, sans basculer silencieusement vers Tesseract. Une erreur conserve le texte déjà présent. Le sous-processus PaddleOCR est limité à 90 secondes, imports et chargement compris. Voir [le guide et l’état de validation](docs/PADDLEOCR.md).

## Limites

Une image à la fois, sans traitement par lots. Le texte imprimé net donne les meilleurs résultats ; manuscrits, tableaux complexes et photos floues ne sont pas reconnus de manière fiable. Le sous-processus Tesseract est limité à 30 secondes ; le prétraitement peut ajouter du temps. Une reconnaissance vide est signalée. Les images de travail sont bornées à 8 millions de pixels et 8 000 pixels sur le plus grand côté. L’aperçu montre l’orientation et la sélection, pas les filtres. Les coins et zones sont manuels, sans détection automatique des bords ni identification de personne. Tesseract emploie des modèles OCR spécialisés, notamment neuronaux ; aucun modèle génératif n’est intégré. Les objectifs complets de précision, temps et mémoire du SRS restent à mesurer.

## État de livraison

MVP et outils de précision implémentés. Vérification : 55 tests réussis ; le test d’inférence réelle PaddleOCR est ignoré faute de modèles. L’OCR Tesseract réel et le parcours navigateur étendu ont été vérifiés. Chromium a aussi vérifié le sélecteur PaddleOCR, la désactivation langue/PSM, l’erreur de modèles manquants et la conservation du texte précédent. Les tests du worker PaddleOCR emploient des simulations explicites, sans valider le modèle.

Les bibliothèques PaddleOCR/PaddlePaddle ont été installées dans `.venv-paddle` et importées sous Linux. Le téléchargement officiel des modèles est bloqué par HTTP 403 ; l’inférence réelle, l’extraction hors ligne et un gain de précision PaddleOCR ne sont donc pas établis. Le benchmark de six images synthétiques **Tesseract** rapporte un CER moyen de 24,86 % avant préparation et 0 % après corrections connues ; cela ne garantit pas la précision sur des cartes d’identité ou documents réels. Voir [les résultats](docs/benchmark-results.json) et [les méthodes et limites](docs/ACCURACY.md). Le script Windows `scripts/setup.ps1` et le parcours PaddleOCR Windows restent non testés nativement.

Captures locales : `.test-artifacts/desktop-empty.png`, `desktop-result.png`, `mobile-empty.png` et `mobile-result.png` dans le même dossier. Installation et détails techniques : [README.md](README.md). Cadrage initial : [docs/README.md](docs/README.md). Système visuel : [DESIGN.md](DESIGN.md).
