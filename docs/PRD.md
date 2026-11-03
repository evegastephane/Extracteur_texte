# PRD — Product Requirements Document

Version : 0.1 — 3 novembre 2026. Statut : proposition MVP.

## 1. Vision du produit

Une application locale simple : importer une image, lancer la reconnaissance, récupérer le texte. Le moteur proposé est Tesseract OCR, open source. Aucun service d’IA externe n’intervient.

## 2. Expérience principale

1. L’utilisateur ouvre l’interface locale dans son navigateur.
2. Il choisit une image PNG ou JPEG ; les limites sont affichées avant l’import.
3. Il consulte l’aperçu et sélectionne Français, Anglais ou Français + Anglais ; Français est la valeur initiale.
4. Il clique sur « Extraire le texte » et voit un état de traitement.
5. Il consulte et corrige le texte dans une zone éditable.
6. Il copie le contenu ou télécharge un fichier `.txt` UTF-8.
7. Il peut choisir une nouvelle image ; le résultat précédent est alors effacé.

## 3. Fonctionnalités prioritaires

| Priorité | Fonctionnalité | Référence SRS |
| --- | --- | --- |
| P0 | Import et validation d’une image | F-01, F-02 |
| P0 | Aperçu et choix de langue | F-03, F-04 |
| P0 | Extraction locale et état de traitement | F-05, F-06 |
| P0 | Résultat modifiable, copie et export | F-07, F-08 |
| P0 | Messages d’erreur et absence de texte | F-09 |
| P0 | Réinitialisation lors d’un nouvel import | F-10 |

Toutes les fonctionnalités P0 sont nécessaires à la première version. Les PDF, lots, améliorations automatiques des photos, autres langues et historique restent pour une éventuelle version ultérieure.

## 4. États de l’interface

- Vide : consignes, formats et limites visibles.
- Image prête : aperçu, langue et action d’extraction disponibles.
- En cours : message de progression sans pourcentage fictif ; nouveau lancement désactivé.
- Succès : texte éditable et actions de récupération disponibles.
- Aucun texte : message invitant à utiliser une image plus nette ou à vérifier la langue.
- Erreur : message compréhensible avec possibilité de réessayer ou de changer d’image.

L’interface ne doit pas afficher de détails internes ou de trace technique à l’utilisateur. Les contrôles ont des libellés explicites et sont accessibles au clavier.

## 5. Contraintes produit

Une image à la fois, au maximum 10 Mio et 20 millions de pixels décodés. Pas d’enregistrement automatique, de télémétrie ou d’historique. Aucune connexion Internet nécessaire à l’utilisation après installation. Le support initial visé est Linux avec un navigateur récent ; Windows et macOS ne sont pas des plateformes validées pour le MVP.

## 6. Critères de livraison

Le parcours complet et les cas d’erreur du SRS doivent être validés. Les performances et la qualité OCR doivent être mesurées sur un jeu d’images de référence décrit dans le SRS. La documentation d’installation doit permettre un démarrage reproductible et indiquer les dépendances et licences. Aucun résultat de validation n’est encore disponible.
