# SRS — Software Requirements Specification

Version : 0.1 — 3 novembre 2026. Statut : exigences proposées pour le MVP.

## 1. Environnement cible

Application web locale, mono-utilisateur, sur Linux, avec Python 3.12 et Tesseract 5.x, données `fra` et `eng` installées. Navigateur récent. Les versions exactes des dépendances devront être verrouillées lors de l’implémentation. Aucun secret ni service distant nécessaire à l’exécution.

## 2. Exigences fonctionnelles

| ID | Exigence | Critère d’acceptation |
| --- | --- | --- |
| F-01 | Importer une seule image PNG ou JPEG | Une image valide de chaque format est acceptée ; les autres formats sont refusés avec un message |
| F-02 | Vérifier taille, décodage et format réel | Refuser fichier vide, corrompu, format falsifié, fichier supérieur à 10 Mio ou image supérieure à 20 millions de pixels avant l’OCR |
| F-03 | Afficher un aperçu adapté à l’écran | L’image garde ses proportions et n’entraîne pas de débordement horizontal de la page |
| F-04 | Proposer Français, Anglais et Français + Anglais | Traduire ces choix en `fra`, `eng` et `fra+eng` ; refuser une langue non autorisée |
| F-05 | Extraire le texte avec Tesseract local | Produire du texte Unicode sans appel réseau ni modèle génératif |
| F-06 | Signaler le traitement et empêcher les doublons | Une seule extraction active ; arrêt de l’OCR après 30 secondes avec erreur explicite |
| F-07 | Afficher et modifier le résultat | Le texte reconnu est éditable et les retours à la ligne sont conservés |
| F-08 | Copier et exporter le texte courant | La copie et le `.txt` UTF-8 incluent les corrections ; si le presse-papiers est indisponible, proposer la sélection manuelle |
| F-09 | Gérer les échecs | Distinguer image invalide, aucun texte, moteur/langue indisponible, délai dépassé et erreur interne ; ne jamais afficher une trace technique |
| F-10 | Réinitialiser le résultat | Un nouvel import supprime l’ancien texte, les anciens messages et les actions liées au résultat précédent |

## 3. Exigences non fonctionnelles

| ID | Exigence | Vérification attendue |
| --- | --- | --- |
| N-01 | Confidentialité | Aucun appel distant lors d’un parcours complet hors ligne ; aucun contenu de document dans les journaux |
| N-02 | Durée de vie des données | Aucune conservation volontaire après la requête ; tout fichier temporaire supprimé en succès et en échec ; résultat gardé en mémoire de la page seulement |
| N-03 | Légèreté | Aucun GPU, base de données ou serveur de modèles ; objectif de mémoire maximale cumulée des processus applicatifs et OCR inférieur à 512 Mio pendant le scénario de performance |
| N-04 | Performance | Objectif de 95 % des extractions en moins de 10 secondes sur le jeu de référence, machine Linux de 2 vCPU et 4 Gio de RAM ; mesurer et publier les résultats avant livraison |
| N-05 | Sécurité locale | Écouter sur `127.0.0.1` par défaut, limiter le corps HTTP, valider les pixels avant décodage complet et passer les arguments OCR sans shell |
| N-06 | Accessibilité | Parcours complet au clavier, focus visible, champs étiquetés et annonces des états de traitement et d’erreur |
| N-07 | Distribution open source | Inventaire des dépendances et licences fourni ; licence du projet choisie avant distribution |

La fermeture de la page ne garantit pas l’effacement physique des données en mémoire ou des mécanismes internes du système. L’application ne doit pas organiser de stockage persistant de ces données.

## 4. Contrat d’interface proposé

- `GET /` : interface locale.
- `GET /health` : état du service, présence du moteur et des langues ; HTTP 200 si prêt, 503 sinon. Aucun chemin sensible exposé.
- `POST /api/ocr` : formulaire multipart contenant `image` et `language` parmi `fra`, `eng`, `fra+eng`.
- Succès : HTTP 200, JSON `{"text":"...","language":"fra"}` ; texte vide si rien n’est reconnu.
- Erreur : JSON `{"error":{"code":"...","message":"..."}}` ; HTTP 400 pour fichier invalide ou langue non autorisée, 413 pour limite dépassée, 503 pour moteur ou données de langue manquants, 504 pour délai OCR dépassé, 500 pour erreur inattendue.
- Réponse contenant un document : `Cache-Control: no-store`. Export et édition effectués dans le navigateur, sans nouvel envoi au serveur.

## 5. Plan de validation

Préparer un jeu versionné de dix images synthétiques sans données personnelles : quatre françaises, quatre anglaises et deux bilingues, contenant du texte imprimé net et leurs transcriptions UTF-8. Inclure PNG et JPEG, de 1 à 4 millions de pixels. Ajouter des fichiers distincts pour les tests d’erreur et de limites.

| Test | Vérification | Exigences |
| --- | --- | --- |
| V-01 | Importer PNG et JPEG, choisir les trois langues et comparer les sorties aux transcriptions | F-01, F-03 à F-05 |
| V-02 | Refuser fichier vide, faux JPEG, image corrompue, format non supporté et dépassements de limites | F-02, N-05 |
| V-03 | Corriger le résultat, copier et exporter ; comparer les caractères et sauts de ligne | F-07, F-08 |
| V-04 | Tester image blanche, absence de moteur ou langue, erreur interne et délai dépassé | F-06, F-09 |
| V-05 | Importer une nouvelle image après succès et après erreur ; tenter un double lancement | F-06, F-10 |
| V-06 | Exécuter hors ligne et vérifier nettoyage temporaire, journaux et absence de persistance | N-01, N-02 |
| V-07 | Mesurer temps et mémoire sur trois passages du jeu, après un passage de chauffe | N-03, N-04 |
| V-08 | Effectuer le parcours au clavier et vérifier les annonces d’état | N-06 |

Objectif qualité : taux d’erreur de caractères agrégé inférieur ou égal à 5 % sur ce jeu imprimé net, avec distance de Levenshtein divisée par le nombre de caractères de référence. Normaliser Unicode en NFC et les fins de ligne en LF, sans supprimer accents ou ponctuation. Ce seuil est un objectif à mesurer et ne s’étend pas à toutes les photos.

Ce document conserve le plan de validation initial. Des tests fonctionnels ont depuis été exécutés ; tous les objectifs complets de performance et de précision restent à valider.

## 6. Extension précision implémentée

| ID | Exigence | Validation |
| --- | --- | --- |
| F-11 | Rotation manuelle par pas de 90° | OCR réel d’une image tournée et contrôles navigateur |
| F-12 | Sélection de quatre coins, recadrage et correction de perspective | Géométrie synthétique, rejet des coins invalides, souris et coordonnées clavier |
| F-13 | Original, contraste/bruit et seuil adaptatif | OCR réel dans chaque mode ; original conservé pour comparaison |
| F-14 | Correction d’inclinaison faible et choix du PSM | Mesure d’angle sur lignes et OCR synthétique ; modes auto/bloc/dispersé/ligne |
| F-15 | Extraction manuelle de zones et ajout avec libellés | Parcours navigateur ; conservation du texte corrigé en cas d’échec |
| F-16 | Comparaison chiffrée avant/après | Script de benchmark CER avec six exemples synthétiques reproductibles |

Le [guide de précision](ACCURACY.md) définit les réglages et le champ API `options`. La limite des images intermédiaires est de 8 millions de pixels et 8 000 pixels de côté. La rotation et les coins restent manuels ; aucune détection automatique de document ou interprétation des champs d’identité n’est promise. Le benchmark synthétique ne remplace pas l’évaluation sur des photos réelles autorisées.

## 7. Extraction par libellés et règles

Le nouveau parcours remplace le texte libre et l’ajout de zones par sept champs autorisés : nom, prénoms, date/lieu de naissance, sexe, taille et profession. Aucun autre champ n’est présenté ni exporté par l’interface. La recherche utilise les libellés français/anglais et les positions OCR, sans entraîner de modèle. Voir [FIELDS.md](FIELDS.md) pour les règles, statuts, limites et API.

Exigences supplémentaires : repérer les valeurs à droite ou en dessous, arrêter l’association aux champs voisins ou aux grands écarts, signaler absence/conflit/format invalide, permettre la correction des sept valeurs et exporter seulement leur résumé TXT ou leur JSON. Une nouvelle image efface les résultats et un échec d’extraction conserve les corrections. Le texte intégral OCR reste uniquement transitoire pour le repérage. Les tests vérifient qu’un identifiant synthétique annexe n’apparaît ni dans les champs, ni dans les indices, ni dans les exports.

## 8. Parcours CNI spécialisé par zones

Le parcours principal est désormais recto → verso → résultats, sans sélecteur de moteur, réglages OCR ou coordonnées. PaddleOCR lit sept zones de valeurs prédéfinies sur un recto aligné à 1600 × 1000. Les propositions restent modifiables et exportables. La classification ancien/nouveau est différée ; un seul profil provisoire est défini. Le verso est obligatoire pour relecture. Ses régions sont maintenant référencées pour calibration, mais ne sont pas lues car elles sont hors des sept champs autorisés. Voir [CNI_ZONES.md](CNI_ZONES.md).

Vérifications requises : contours et projection, orientation confirmée, images distinctes et canoniques, découpage excluant portrait/signature, une instance de reconnaissance directe pour les sept zones, validation sans invention, limite globale de 90 secondes et nettoyage. La limite HTTP totale accepte deux images de 10 Mio ; les limites de chaque fichier sont contrôlées séparément. Une simple relecture sans changement doit conserver les corrections sans OCR supplémentaire. Changer le recto invalide le verso et les anciens résultats.

`/health` porte maintenant sur PaddleOCR par zones, et non sur Tesseract : HTTP 503 sans préparation réussie du moteur direct. Le test réel de préparation ajoute le marqueur `zone_smoke_test` après réussite. Les tests synthétiques et les réponses UI simulées ne prouvent pas la précision sur les photos de CNI fournies.


La préparation CNI ne dépend plus du test de l’ancien pipeline généraliste : celui-ci est optionnel avec `--check-legacy`. Les marqueurs et contrôles de disponibilité sont indépendants. Les erreurs de téléchargement et de test local sont distinguées, avec étapes du worker affichées sans tampon pendant la préparation synthétique.
