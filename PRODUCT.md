# Extracteur de texte

Application web locale et légère, en français, pour récupérer le texte d’une image avec un moteur OCR open source. Elle utilise Flask, Pillow, pytesseract et Tesseract, sans compte ni service d’IA externe. Elle fonctionne hors ligne après installation des dépendances et des données de reconnaissance.

## Parcours et périmètre

1. Choisir ou déposer une seule image PNG/JPEG, jusqu’à 10 Mio et 20 millions de pixels.
2. Sélectionner Français, Anglais ou Français + Anglais, puis lancer l’extraction.
3. Relire et modifier le texte, le copier ou l’exporter en `.txt` UTF-8.

Le navigateur communique avec le serveur local, lié à `127.0.0.1`. Aucun document n’est envoyé à un service externe. L’application ne conserve ni historique ni contenu dans ses journaux. Les fichiers temporaires OCR sont supprimés après traitement ; le résultat reste dans la page jusqu’au nouvel import ou à sa fermeture, sauf copie ou export volontaire.

## Limites

Une image à la fois, sans traitement par lots. Le texte imprimé net donne les meilleurs résultats ; manuscrits, tableaux complexes et photos floues ne sont pas reconnus de manière fiable. Le traitement est limité à 30 secondes et une reconnaissance vide est signalée. Tesseract emploie des modèles OCR spécialisés, notamment neuronaux ; aucun modèle génératif n’est intégré. Les objectifs complets de précision, temps et mémoire du SRS restent à mesurer.

## État de livraison

MVP implémenté. Vérification de livraison : 19 tests pytest réussis avec OCR réel, délai maximal et nettoyage ; test navigateur fonctionnel sur ordinateur et mobile, sans requête externe observée. Revue finale : livraison, sans constat restant.

Captures locales : `.test-artifacts/desktop-empty.png`, `desktop-result.png`, `mobile-empty.png` et `mobile-result.png` dans le même dossier. Installation et détails techniques : [README.md](README.md). Cadrage initial : [docs/README.md](docs/README.md). Système visuel : [DESIGN.md](DESIGN.md).
