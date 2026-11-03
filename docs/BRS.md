# BRS — Business Requirements Specification

Version : 0.1 — 3 novembre 2026. Statut : proposition MVP.

## 1. Besoin métier

Permettre à une personne de récupérer le texte présent dans une image sans le recopier manuellement et sans transmettre son document à un fournisseur externe.

## 2. Utilisateurs et usages

- Particulier souhaitant copier le texte d’une capture d’écran ou d’une photo nette.
- Utilisateur administratif souhaitant récupérer le contenu d’un document imprimé photographié ou numérisé.

Le cas prioritaire est un texte imprimé en français ou en anglais, sur fond suffisamment contrasté.

## 3. Objectifs métier

| ID | Besoin | Indicateur de réussite |
| --- | --- | --- |
| B-01 | Éviter la ressaisie | Une image produit un texte sélectionnable et modifiable |
| B-02 | Préserver la confidentialité | Aucun contenu d’image ou de résultat envoyé à un service externe |
| B-03 | Réduire les coûts et dépendances | Aucun abonnement, clé API ou service payant requis |
| B-04 | Rester simple et léger | Une interface unique ; aucune base de données ni GPU requis |
| B-05 | Fonctionner hors ligne | Extraction possible après installation des dépendances et langues |

## 4. Périmètre

Le MVP couvre l’import d’une image PNG ou JPEG, l’OCR local, la consultation et la correction du texte, sa copie et son export en fichier texte UTF-8.

Sont hors périmètre : PDF, traitement par lots, écriture manuscrite, traduction, résumé, chatbot, mise en page fidèle, extraction structurée de tableaux, comptes utilisateurs et hébergement public partagé.

## 5. Contraintes

- Utiliser des composants open source et documenter leurs licences avant distribution.
- Ne pas intégrer de service d’IA externe ni de modèle génératif.
- Ne pas conserver les documents après leur traitement.
- Privilégier une exécution sur ordinateur standard, avec un processeur et sans GPU.

## 6. Risques et limites

L’exactitude dépend de la netteté, de l’orientation, de la taille des caractères et de la langue sélectionnée. L’utilisateur doit pouvoir vérifier et corriger le résultat ; aucune exactitude universelle n’est promise. Le MVP ne garantit pas la reconnaissance des photos inclinées, documents complexes ou écritures manuscrites.

## 7. Validation métier

Le MVP est acceptable si un utilisateur peut importer une image imprimée lisible, extraire puis corriger et exporter son texte, sans compte et avec le réseau désactivé. Les critères mesurables sont définis dans le SRS.
