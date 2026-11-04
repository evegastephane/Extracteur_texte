# Extracteur CNI camerounaise

Application web locale en français : **recto → Suivant → verso → Suivant → résultats**. Une seule étape est visible à la fois, sans réglages de moteur, filtre, langue ou coins. Le parcours utilise PaddleOCR pour lire sept zones fixes de valeurs, sans entraînement ni nouveaux poids spécialisés et sans basculement automatique vers Tesseract.

## Parcours et champs

Importer chaque face en PNG/JPEG (10 Mio et 20 millions de pixels maximum par photo). OpenCV cherche un quadrilatère de carte et le projette vers 1600 × 1000. Un cadre déjà compatible peut servir directement. L’utilisateur vérifie les bords et le sens du texte ; « Retourner l’image » applique 180° avant « Suivant ». L’alignement ne reconnaît pas automatiquement l’orientation textuelle, le modèle ou l’authenticité.

Après les deux faces confirmées, les seules clés de champs sont `nom`, `prenoms`, `date_naissance`, `lieu_naissance`, `sexe`, `taille` et `profession`. Un worker CPU charge une seule instance PaddleOCR `TextRecognition` avec `latin_PP-OCRv5_mobile_rec` pour les sept découpes de valeurs du recto, sans recherche de libellés sur la carte entière. Les champs restent modifiables ; copie/TXT reprennent ceux renseignés, JSON conserve les sept clés, leurs statuts et le gabarit.

`non_trouve`, `a_verifier` et `propose` indiquent absence, doute et lecture plausible à relire. Les formats date/sexe/taille, chiffres dans les noms et scores faibles sont signalés. Aucun pourcentage de précision ni valeur manquante n’est inventé ; les normalisations sont des métadonnées, sans correction silencieuse de caractères.

Revoir les photos inchangées conserve les corrections : « Suivant » réouvre les résultats sans nouvelle lecture. Une modification effective des photos invalide les résultats ; remplacer le recto efface aussi le verso précédent. « Nouvelle carte » efface la session.

## Couverture provisoire

Le seul profil est `cni_puce_recto_v1`, estimé sur le recto à puce fourni. Les dernières références fournissent le recto et le verso du même type de carte. Leurs zones sont référencées sans intégrer les photos ou valeurs personnelles dans le dépôt ; aucun second modèle n’est encore défini. La classification ancien/nouveau est différée. La calibration et la précision sur de vraies CNI restent à mesurer.

Le verso est obligatoire, décodé, aligné et affichable pour relecture, mais **n’est pas lu par OCR** : ses zones sont référencées pour calibration mais leurs valeurs sont hors des sept champs autorisés. Cette limite est affichée. Deux photos strictement identiques sont refusées ; deux photos différentes de rectos ne sont pas reconnues comme telles. Le recadrage ne constitue pas un contrôle d’identité. Une carte d’une autre disposition peut produire des champs erronés.

## Préparation et API

Paddle reste isolé dans `.venv-paddle`. `scripts/setup_paddle.py` doit réussir le test synthétique direct de zones et écrire `zone_smoke_test: passed`, y compris pour des modèles existants. Sans modèles préparés, l’interface s’ouvre avec un avertissement mais refuse la lecture ; `/health` renvoie HTTP 503. Le worker est limité à 90 secondes, chargement et sept lectures compris ; le navigateur attend jusqu’à 105 secondes.

`/api/cni/align` aligne une face sans OCR ; `/api/cni/read` reçoit deux PNG canoniques et retourne les sept champs et les limites ; `/api/cni/status` décrit la disponibilité. Les anciennes routes OCR restent pour compatibilité technique, sans réglages dans l’interface.

Le navigateur communique avec le serveur local lié à `127.0.0.1`. Aucun document n’est envoyé à un service externe. Aucun historique ni sauvegarde serveur des pièces n’est ajouté ; les fichiers intermédiaires et caches de requête sont supprimés en succès, erreur et expiration. Les dépendances et modèles restent persistants. Ces mesures ne garantissent ni l’exactitude des associations ni une confidentialité absolue.

## Vérification actuelle

111 tests réussis, 2 tests d’inférence réelle Paddle ignorés faute de poids préparés. L’alignement synthétique et certains contrôles de découpe sont réels ; ces derniers utilisent explicitement Tesseract comme substitution, sans valider Paddle. Chromium vérifie l’alignement et l’erreur de moteur absent, puis une réponse Paddle simulée pour le parcours, les corrections, exports, remise à zéro et mobile. Le défaut de perte des corrections après simple relecture a été corrigé en réutilisant le résultat ; le test navigateur final passe.

Captures revues : `.test-artifacts/desktop-wizard-recto.png`, `desktop-wizard-results.png`, `mobile-wizard-recto.png`, `mobile-wizard-results.png` dans le même dossier. Elles ne prouvent pas une reconnaissance Paddle réelle. La précision sur les CNI fournies et la validation native Windows ne sont pas établies.

Références : [zones et limites](docs/CNI_ZONES.md), [installation](README.md), [système visuel](DESIGN.md).
