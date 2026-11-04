# Documentation — Extracteur de texte

État courant : parcours CNI recto → verso → résultats, lecture par zones fixes du recto avec PaddleOCR. Les documents BRS/PRD/SRS/SAD conservent le cadrage initial et ses évolutions.

Le moteur principal est PaddleOCR local, sans service d’IA externe. Le gabarit du recto fourni est provisoire ; classification ancien/nouveau différée ; régions du verso référencées mais hors des sept champs retenus.

| Document | Rôle |
| --- | --- |
| [Zones CNI](CNI_ZONES.md) | Parcours actuel, alignement, sept zones, validation et limites |
| [BRS](BRS.md) | Besoin métier, valeur et limites |
| [PRD](PRD.md) | Produit, parcours utilisateur et périmètre du MVP |
| [SRS](SRS.md) | Exigences fonctionnelles et critères vérifiables |
| [SAD](SAD.md) | Architecture et choix techniques proposés |
| [Précision OCR](ACCURACY.md) | Ancien moteur réglable et benchmark OCR technique |
| [PaddleOCR](PADDLEOCR.md) | Installation Windows/Linux et limites de validation |
| [Champs par libellés](FIELDS.md) | Moteur historique, conservé seulement dans l’ancienne API |

Le parcours actuel est décrit dans [Zones CNI](CNI_ZONES.md) et le [guide d’installation](../README.md). Les objectifs de précision sur des photos réelles restent à mesurer ; les essais synthétiques ne les établissent pas.

PaddleOCR emploie un modèle neuronal spécialisé préexistant, téléchargé lors de la préparation. Aucun nouveau modèle n’est entraîné ici et aucun modèle n’est téléchargé pendant la lecture.
