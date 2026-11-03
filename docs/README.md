# Documentation — Extracteur de texte

Version : 0.1 — 3 novembre 2026. Statut : proposition initiale pour le MVP.

Le produit lit une image et en extrait du texte grâce à un moteur OCR open source exécuté localement. Aucun service d’IA générative, compte utilisateur ou abonnement n’est nécessaire.

| Document | Rôle |
| --- | --- |
| [BRS](BRS.md) | Besoin métier, valeur et limites |
| [PRD](PRD.md) | Produit, parcours utilisateur et périmètre du MVP |
| [SRS](SRS.md) | Exigences fonctionnelles et critères vérifiables |
| [SAD](SAD.md) | Architecture et choix techniques proposés |
| [Précision OCR](ACCURACY.md) | Recadrage, perspective, filtres, zones et mesure des gains |
| [PaddleOCR](PADDLEOCR.md) | Moteur optionnel, installation Windows/Linux et limites de validation |
| [Champs par libellés](FIELDS.md) | Sept champs autorisés, règles spatiales, correction et exports filtrés |

Périmètre : une petite application web utilisée sur une machine locale, pour une image à la fois. Le MVP est désormais implémenté ; voir le [guide d’installation](../README.md). Les documents ci-dessous conservent le cadrage initial. Les objectifs complets de performance et précision du SRS restent à mesurer.

Par « sans IA », on entend ici sans modèle génératif, API d’IA ou modèle téléchargé à la demande. Tesseract est un moteur OCR spécialisé dont les versions modernes utilisent des réseaux neuronaux pour reconnaître les caractères. Ses données de reconnaissance françaises et anglaises sont installées avec l’application.
