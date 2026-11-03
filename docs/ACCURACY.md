# Améliorer la reconnaissance

Les outils ci-dessous fonctionnent localement avec Pillow, OpenCV et Tesseract, sans API externe. Ils aident à préparer une photo ; ils ne permettent pas de récupérer du texte masqué par un reflet ou rendu illisible par le flou.

## Pour une carte photographiée

1. Importer la photo et utiliser **Tourner de 90°** jusqu’à remettre le texte à l’endroit. La rotation est manuelle ; aucune détection fiable d’orientation d’une petite carte n’est supposée.
2. Cocher **Recadrer et redresser le document**. Cliquer **Placer les quatre coins sur l’image**, puis sélectionner haut gauche, haut droit, bas droit, bas gauche, dans cet ordre. Déplacer les poignées pour affiner. Les coordonnées X/Y en pourcentage permettent aussi le réglage au clavier.
3. Choisir **Texte dispersé / carte** et essayer **Photo — contraste et bruit**. Pour un fond très chargé, essayer aussi **Noir et blanc adaptatif**. Le mode **Original — sans filtre** reste disponible : aucun filtre n’est meilleur pour toutes les images.
4. Cocher la correction de légère inclinaison seulement si nécessaire. Elle cherche des lignes proches de l’horizontale (±12°), après le recadrage. Elle ne remplace pas une rotation de 90° ou 180° et peut se tromper sur des motifs de sécurité.
5. Extraire puis relire le résultat. Pour les cartes bilingues, sélectionner **Français + Anglais** si nécessaire.

**Image entière** désactive la sélection et restaure ses coins, sans changer la rotation ni les filtres. Une rotation réinitialise les coins afin d’éviter d’appliquer une ancienne sélection à une autre orientation. Une sélection croisée ou trop petite est refusée avec un message.

## Lire les zones séparément

Recadrer autour d’un seul champ, par exemple le nom, et choisir **Une seule ligne** si adapté. Ouvrir **Reconnaître plusieurs zones séparément**, indiquer un libellé et lancer l’extraction. Pour les champs suivants, cocher **Ajouter au résultat existant**, déplacer les coins et changer le libellé. Le texte s’ajoute à la zone éditable ; copier et exporter récupèrent le texte complet, avec les corrections.

Il s’agit d’une sélection manuelle de zones, pas d’une reconnaissance automatique du type de carte ou de ses champs. Il n’y a aucune identification de la personne représentée. Importer une nouvelle image efface le résultat et les libellés ; décocher l’ajout remplace le texte lors de la prochaine extraction.

## Traitement et limites

Ordre : orientation EXIF → rotation demandée → sélection et transformation de perspective → filtre choisi → correction de faible inclinaison → Tesseract.

- Original : pas de filtre tonal ; l’image source importée n’est jamais réécrite.
- Photo : agrandissement limité, niveaux de gris, réduction du bruit et contraste local CLAHE.
- Noir et blanc : même préparation, puis seuillage adaptatif gaussien.
- Disposition : automatique (`--psm 3`), bloc (`6`), texte dispersé (`11`), ligne (`7`).

Pour limiter la mémoire, les images de travail sont bornées à 8 millions de pixels et 8 000 pixels sur le plus grand côté. Le mode Photo agrandit au plus d’un facteur 2, en visant un grand côté de 2 200 pixels sous ces plafonds. L’import conserve ses limites de 10 Mio et 20 millions de pixels. Le délai de 30 secondes s’applique au sous-processus Tesseract ; le prétraitement peut ajouter du temps. Aucun essai multiple caché ni modèle supplémentaire n’est chargé.

L’aperçu montre l’image orientée et la sélection, pas le résultat tonal des filtres. Comparer les extractions en changeant le filtre si nécessaire. Aucune détection automatique des bords de la carte n’est incluse.

## Mesurer les gains

Depuis la racine du dépôt :

```powershell
# Windows, après installation des dépendances
.\.venv\Scripts\python.exe -m scripts.benchmark --output .test-artifacts/benchmark-windows.json
```

```sh
# Linux
.venv/bin/python -m scripts.benchmark --output .test-artifacts/benchmark.json
```

Le script génère six images et leurs transcriptions sans données personnelles : texte net, rotation de 180°, inclinaison de 6°, faible contraste, perspective et texte entouré d’un fond contenant d’autres mots. Il mesure la distance de Levenshtein par caractère (CER), normalisée en Unicode NFC et fins de ligne LF, ainsi que la durée de chaque extraction. Les corrections géométriques sont des sélections connues à l’avance, représentant un réglage manuel correct. Le traitement ne les détecte pas automatiquement.

Les [résultats de référence](benchmark-results.json) contiennent les textes reconnus, réglages, scores et versions. Sur ce petit jeu Linux, le CER moyen passe d’environ 24,9 % à 0 %. Ce résultat contrôlé ne mesure ni la précision sur des documents réels, ni la conformité aux objectifs de performance du SRS. Il ne démontre pas qu’un filtre améliore toutes les photos : le texte net et le faible contraste étaient déjà correctement reconnus sans filtre. Les polices et versions de Tesseract affectent les scores.

Pour une évaluation réelle, utiliser uniquement des documents dont l’usage est autorisé, anonymiser les données et conserver les exemples privés hors du dépôt. Ajouter leurs transcriptions et mesurer chaque cas avant/après, sans corriger les sorties OCR avant le calcul.

## API

`POST /api/ocr` conserve `image` et `language` et accepte un champ multipart `options` contenant un objet JSON :

```json
{
  "rotation": 0,
  "corners": [[0.1, 0.1], [0.9, 0.15], [0.85, 0.9], [0.15, 0.85]],
  "mode": "contrast",
  "layout": "sparse",
  "deskew": false
}
```

Les coordonnées sont normalisées entre 0 et 1, relatives à l’image après correction EXIF et rotation. `corners: null` traite l’image entière. L’omission d’`options` conserve le comportement original. Les réglages invalides produisent HTTP 400. L’accumulation et les libellés des zones sont gérés dans le navigateur, sans stockage serveur.
