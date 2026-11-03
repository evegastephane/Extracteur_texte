# Extracteur de texte

Application web locale et légère, en français, pour récupérer le texte d’une image avec un moteur OCR open source. Elle utilise Flask, Pillow, OpenCV, pytesseract et Tesseract, sans compte ni service d’IA externe. Elle fonctionne hors ligne après installation des dépendances et des données de reconnaissance.

## Parcours et périmètre

1. Choisir ou déposer une seule image PNG/JPEG, jusqu’à 10 Mio et 20 millions de pixels.
2. Si nécessaire, tourner l’image par pas de 90°, sélectionner quatre coins dans le sens horaire (haut gauche, haut droit, bas droit, bas gauche), puis affiner les poignées ou les coordonnées X/Y au clavier. Les coordonnées sont normalisées après orientation.
3. Choisir le filtre Original, Photo (contraste et réduction du bruit) ou Noir et blanc adaptatif ; activer au besoin la correction d’inclinaison (±12°). Choisir la disposition automatique, bloc, dispersée ou ligne (PSM 3/6/11/7), puis la langue Français, Anglais ou Français + Anglais.
4. Extraire, relire et modifier le texte, le copier ou l’exporter en `.txt` UTF-8. Pour plusieurs zones manuelles, saisir un libellé et cocher explicitement « Ajouter au résultat existant » avant les extractions suivantes. Une extraction échouée conserve le texte précédent et ses corrections ; un nouvel import les efface.

Le navigateur communique avec le serveur local, lié à `127.0.0.1`. Aucun document n’est envoyé à un service externe. L’application ne conserve ni historique ni contenu dans ses journaux. Les fichiers temporaires OCR sont supprimés après traitement ; le résultat reste dans la page jusqu’au nouvel import ou à sa fermeture, sauf copie ou export volontaire.

## Limites

Une image à la fois, sans traitement par lots. Le texte imprimé net donne les meilleurs résultats ; manuscrits, tableaux complexes et photos floues ne sont pas reconnus de manière fiable. Le sous-processus Tesseract est limité à 30 secondes ; le prétraitement peut ajouter du temps. Une reconnaissance vide est signalée. Les images de travail sont bornées à 8 millions de pixels et 8 000 pixels sur le plus grand côté. L’aperçu montre l’orientation et la sélection, pas les filtres. Les coins et zones sont manuels, sans détection automatique des bords ni identification de personne. Tesseract emploie des modèles OCR spécialisés, notamment neuronaux ; aucun modèle génératif n’est intégré. Les objectifs complets de précision, temps et mémoire du SRS restent à mesurer.

## État de livraison

MVP et outils de précision implémentés. Vérification : 45 tests pytest réussis et test navigateur étendu réussi, notamment conservation du texte après échec et indication explicite de l’ajout. Le benchmark de six images synthétiques rapporte un CER moyen de 24,86 % avant préparation et 0 % après corrections connues ; cela ne garantit pas la précision sur des cartes d’identité ou documents réels. Voir [les résultats](docs/benchmark-results.json) et [les méthodes et limites](docs/ACCURACY.md). Le script Windows `scripts/setup.ps1` est fourni mais n’a pas été testé nativement sous Windows.

Captures locales : `.test-artifacts/desktop-empty.png`, `desktop-result.png`, `mobile-empty.png` et `mobile-result.png` dans le même dossier. Installation et détails techniques : [README.md](README.md). Cadrage initial : [docs/README.md](docs/README.md). Système visuel : [DESIGN.md](DESIGN.md).
