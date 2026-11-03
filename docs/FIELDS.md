# Extraction par libellés et règles

Le parcours de l’application conserve uniquement sept champs. Le texte OCR sert d’entrée au repérage, puis les autres informations sont écartées de la réponse, de l’écran de résultat, de la copie et des exports. Aucun modèle d’extraction n’est entraîné, aucun LLM ni API externe n’intervient. Les moteurs OCR eux-mêmes conservent leurs modèles spécialisés existants.

## Champs autorisés

| Clé JSON | Champ | Principaux libellés reconnus |
| --- | --- | --- |
| `nom` | Nom | NOM, NOM DE FAMILLE, SURNAME, LAST NAME |
| `prenoms` | Prénoms | PRÉNOM(S), GIVEN NAME(S), FIRST NAME(S) |
| `date_naissance` | Date de naissance | DATE DE NAISSANCE, DATE OF BIRTH, BIRTH DATE |
| `lieu_naissance` | Lieu de naissance | LIEU DE NAISSANCE, PLACE OF BIRTH, BIRTHPLACE |
| `sexe` | Sexe | SEXE, SEX |
| `taille` | Taille | TAILLE, HEIGHT |
| `profession` | Profession | PROFESSION, PROFFESION, PROFESION, OCCUPATION |

La casse et les accents des libellés n’empêchent pas leur repérage. Les libellés bilingues voisins, par exemple `NOM/SURNAME`, sont réunis en un seul repère. Quelques variantes OCR sont explicites (`N0M`) ; aucun rapprochement flou illimité n’est appliqué. Les valeurs reconnues gardent leur casse et leurs accents.

## Recherche spatiale

1. Le moteur reçoit l’image après rotation, recadrage, redressement et filtres. Tesseract fournit les boîtes de mots via `image_to_data` ; PaddleOCR fournit les polygones des lignes.
2. Les boîtes sont regroupées en lignes proches verticalement. Les libellés sont repérés sur ces lignes, en donnant priorité aux expressions les plus longues.
3. Pour chaque repère, la valeur est cherchée à droite, par mots spatialement contigus et jusqu’au libellé suivant. Un grand écart horizontal coupe la recherche. Si aucun texte n’est présent à droite, la recherche descend dans la même colonne, à proximité du repère, sans franchir un nouveau libellé.
4. Les champs voisins sur une même ligne, tels que sexe et taille, servent de limites de colonne. Les noms, lieux et professions peuvent occuper deux lignes proches et alignées ; une continuation contenant des chiffres n’est pas fusionnée. Dates, sexe et taille restent sur une ligne. Les mots ressemblant à des identifiants alphanumériques longs sont écartés des champs textuels, plutôt qu’ajoutés au nom ou à la profession.
5. Des libellés non retenus — nationalité, numéro de carte, dates de délivrance/expiration, adresse, signature, autorité — peuvent arrêter une recherche, mais ne deviennent jamais des champs de sortie.

Les boîtes PaddleOCR pouvant couvrir une ligne complète, les positions des portions de texte y sont approximées par leur longueur. Des dispositions complexes peuvent donc nécessiter une correction manuelle. Une sélection de zone doit contenir le libellé et sa valeur, pas seulement la valeur.

## Résultats à vérifier

- `propose` : un candidat a été associé au libellé ; ce n’est pas une certification d’exactitude.
- `non_trouve` : libellé ou valeur absent ; le champ reste vide.
- `a_verifier` : plusieurs valeurs différentes ou format suspect. Les conflits laissent le champ vide et présentent les candidats ; les dates/tailles/sexe au format douteux restent visibles avec un avertissement.

Sans libellé reconnu, le système ne devine pas le nom, le sexe ou la profession à partir d’autres informations. Il n’identifie pas la personne représentée. Aucun pourcentage de confiance artificiel n’est affiché.

Les contrôles de format produisent des métadonnées, sans changer automatiquement la valeur OCR : dates numériques valides vers ISO (`2000-12-17`), sexe vers `M`/`F`, taille vers mètres (`1.77 m`). Pour une taille sans unité, une valeur entière supérieure ou égale à 30 est interprétée en centimètres pour cette normalisation. Les chiffres OCR douteux ne sont pas corrigés automatiquement. Le nom, les prénoms, le lieu et la profession restent du texte libre.

## Interface et exports

Les sept champs sont modifiables. Le résumé, la copie et le TXT contiennent seulement les champs renseignés. Le JSON contient exactement les sept clés, leurs valeurs et leur statut ; les corrections sont marquées `modifie_manuellement`. Les indices de repérage restent consultables sous les champs, sans afficher le texte intégral OCR.

Une nouvelle image efface les champs et les corrections précédentes. Une extraction qui échoue conserve les corrections. Une extraction réussie remplace les sept propositions ; aucune fusion silencieuse entre deux documents n’est effectuée. L’ancien ajout libre de zones n’est plus présenté dans ce parcours afin de ne pas réintroduire des informations hors liste.

## API

`POST /api/ocr` utilise maintenant `structured=true` par défaut. Il retourne `text` (résumé filtré), `fields` (les sept clés), `engine` et `language`. Chaque champ contient `label`, `value`, `normalized`, `status`, `message` et des indices `evidence` limités aux libellés/candidats de ce champ. Les boîtes de libellés sont normalisées sur l’image préparée ; elles ne désignent pas les coordonnées de la photo originale.

Pour compatibilité avec les outils internes de mesure OCR, `structured=false` permet encore explicitement l’ancien texte brut. L’interface ne demande jamais ce mode. Les cinq parties multipart `image`, `language`, `options`, `engine`, `structured` sont acceptées. Aucun stockage des champs ou des documents n’est ajouté.

## Vérification et limites

Les tests couvrent libellés français/anglais/bilingues, valeurs à droite/en dessous, deux colonnes, champs absents, conflits, formats invalides, exclusion d’informations annexes et conversion des polygones Paddle. Une image synthétique sans données personnelles vérifie réellement les sept champs avec Tesseract ; un marqueur de numéro de carte doit être absent de toute la réponse. Chromium vérifie aussi les exports TXT/JSON, les corrections et le mobile.

La reconnaissance réelle PaddleOCR reste non validée tant que ses poids ne sont pas disponibles dans l’environnement cloud. Les règles ont été testées avec des sorties Paddle simulées, pas avec une vraie carte traitée par ce moteur. Les photos floues, reflets, libellés mal reconnus ou mises en page inconnues peuvent provoquer des associations incorrectes : relire les propositions et compléter manuellement les champs manquants.
