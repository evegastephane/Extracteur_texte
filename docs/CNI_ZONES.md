# CNI : alignement, zones fixes et validation

## Périmètre de cette itération

Le parcours demandé est recto → verso → résultats, avec PaddleOCR principal et sans paramètres techniques. L’identification automatique ancien/nouveau modèle est **différée**. Les dernières images fournissent désormais des références recto et verso du même type de carte, sous plusieurs orientations. Les zones du verso ont été estimées à partir de ces vues ; elles ne définissent pas un second modèle.

Le seul profil est `cni_puce_recto_v1`, descriptif et provisoire. Il ne porte pas de date ou de classement ancien/nouveau non vérifié. Les coordonnées ont été estimées sur le recto illustré, sans conserver ses pixels ni ses valeurs personnelles dans les fichiers du projet. La calibration sur un jeu de vraies cartes autorisées reste nécessaire.

## Ordre des opérations

1. Décoder PNG/JPEG, vérifier 10 Mio / 20 millions de pixels et corriger l’orientation EXIF.
2. Chercher un quadrilatère suffisamment grand par contours et masque de couleur. Vérifier un ratio proche d’une carte et projeter vers 1600 × 1000. Une image déjà recadrée avec un ratio compatible peut utiliser son cadre entier.
3. Afficher le résultat avant « Suivant ». L’axe long devient horizontal ; le sens restant à 180° est confirmé par l’utilisateur via « Retourner l’image ». Le programme ne prétend pas reconnaître automatiquement l’orientation textuelle ou le modèle.
4. Après les deux faces confirmées, découper uniquement les sept zones du recto. Une marge blanche fixe est ajoutée ; aucune binarisation agressive ni recherche de libellés n’intervient.
5. Démarrer un worker CPU unique et charger une fois `TextRecognition` avec `latin_PP-OCRv5_mobile_rec`. Lire chaque découpe séparément pour garder son association exacte au champ. Le détecteur de texte généraliste et les modèles supplémentaires de redressement ne sont pas appelés dans ce chemin.
6. Vérifier les formats de date, sexe et taille, signaler chiffres dans les noms et lectures de faible score. Le score du modèle ne certifie pas l’exactitude ; aucun pourcentage artificiel n’est affiché. Aucune valeur manquante n’est fabriquée.

La limite de 90 secondes couvre le worker complet, chargement et sept reconnaissances compris. Le navigateur attend jusqu’à 105 secondes. Les images, découpes, résultats intermédiaires et caches PaddleX de requête sont supprimés en succès, erreur ou expiration.

## Gabarit de valeurs

Source de vérité : [app/cni_templates.json](../app/cni_templates.json). Les coordonnées `(gauche, haut, droite, bas)` sont relatives à la carte **alignée**, pas à la photographie d’origine. Les libellés se situent au-dessus des valeurs et ne doivent pas entrer dans ces découpes.

| Champ | Gauche | Haut | Droite | Bas |
| --- | ---: | ---: | ---: | ---: |
| Nom | 0,265 | 0,210 | 0,635 | 0,275 |
| Prénoms | 0,265 | 0,335 | 0,640 | 0,402 |
| Date de naissance | 0,265 | 0,462 | 0,595 | 0,510 |
| Lieu de naissance | 0,265 | 0,540 | 0,640 | 0,583 |
| Sexe | 0,265 | 0,615 | 0,340 | 0,662 |
| Taille | 0,385 | 0,615 | 0,530 | 0,662 |
| Profession | 0,265 | 0,700 | 0,640 | 0,755 |

Les zones restent à gauche du portrait et au-dessus de la signature. Le test synthétique a notamment resserré le bas du lieu de naissance pour éviter d’inclure le libellé de la ligne suivante. Cela ne remplace pas une calibration sur des photos réelles et différentes impressions.

## Verso et autres modèles

Le verso est obligatoire dans le parcours pour préparer le dossier et permettre sa relecture. Il est décodé et doit être aligné. Ses régions sont maintenant référencées dans `back.regions` du gabarit, mais aucun de ses champs n’est lu : ils sont hors de la liste des sept informations autorisées. Le serveur retourne explicitement cette limite. Il n’extrait pas de numéro de carte, de signature ou d’autres informations hors des sept champs.

Deux photos strictement identiques sont refusées comme recto/verso. Deux images différentes de deux rectos ne peuvent pas être identifiées comme telles par cette version : il n’y a ni classificateur de face/modèle ni vérification d’authenticité. Le recadrage géométrique n’est pas un contrôle d’identité.

Pour étendre la couverture, il faudra des références du second modèle avec les champs attendus, et décider explicitement si d’autres champs du verso doivent être retenus. Ajouter alors un profil distinct et des tests de calibration ; ne pas réutiliser silencieusement ces zones pour un autre dessin de carte.

## Statuts et corrections

- `non_trouve` : découpe sans valeur lisible.
- `a_verifier` : format invalide, chiffres dans un nom, score absent ou inférieur à 0,70.
- `propose` : lecture et format plausibles, toujours à relire.

Une proposition n’est jamais qualifiée de validée automatiquement. Les valeurs brutes restent modifiables. La date ISO, le sexe normalisé et la taille en mètres sont des métadonnées ; aucune correction silencieuse des caractères OCR. Copier/TXT récupèrent les sept champs renseignés ; JSON conserve les sept clés et le statut manuel si l’utilisateur corrige une valeur.

Les résultats édités sont conservés pendant une simple relecture des photos, et « Suivant » les réouvre sans OCR si les photos n’ont pas changé. Changer une photo invalide les propositions ; remplacer le recto efface aussi le verso précédent. Aucun historique serveur, aucune sauvegarde des pièces d’identité, aucun entraînement supplémentaire.

## Installation et état de validation

La préparation Paddle teste par défaut uniquement la reconnaissance directe des zones CNI. L’ancien pipeline généraliste n’est testé que si `--check-legacy` est explicitement demandé ; il ne bloque plus la préparation CNI par défaut. Relancer `scripts/setup_paddle.py` avec le Python de `.venv-paddle`, même si les modèles sont déjà présents. Un manifeste cohérent est vérifié avant réutilisation ; le marqueur `zone_smoke_test: passed` n’est écrit qu’après réussite du test direct. Sans ce marqueur, le parcours CNI refuse la lecture avec HTTP 503 et propose de préparer le moteur.

Les tests automatisés vérifient géométrie, zones, formats, worker unique, limites et nettoyages. Certains tests de découpe utilisent réellement Tesseract comme substitution de contrôle ; ils ne démontrent pas l’inférence Paddle. Le navigateur utilise réellement l’alignement et l’erreur de moteur absent, puis simule une réponse Paddle pour exercer les résultats et exports. Les captures de résultats de test ne sont pas des preuves de reconnaissance Paddle réelle.

Les deux tests Paddle réels restent ignorés dans le cloud faute de modèles préparés. La validation native Windows et la précision sur les CNI photographiées fournies ne sont pas établies. Pour cette version, le travail vérifié est le pipeline et le parcours ; aucun taux de précision sur de vraies cartes n’est revendiqué.

## Régions du verso référencées, sans lecture

Les références verso reçues ont permis d’ajouter les régions normalisées suivantes. Elles sont provisoires et doivent être calibrées sur des images réellement alignées. Elles ne sont pas envoyées au worker et ne créent aucune clé supplémentaire dans les résultats.

| Région | Gauche | Haut | Droite | Bas |
| --- | ---: | ---: | ---: | ---: |
| Père | 0,040 | 0,080 | 0,680 | 0,145 |
| Mère | 0,040 | 0,205 | 0,680 | 0,265 |
| Code administratif | 0,040 | 0,345 | 0,250 | 0,405 |
| Adresse | 0,040 | 0,440 | 0,285 | 0,505 |
| Date de délivrance | 0,540 | 0,355 | 0,720 | 0,415 |
| Date d’expiration | 0,540 | 0,465 | 0,720 | 0,525 |
| Poste d’identification | 0,735 | 0,355 | 0,970 | 0,415 |
| Identifiant unique | 0,735 | 0,465 | 0,980 | 0,535 |
| Numéro de carte | 0,775 | 0,875 | 0,970 | 0,945 |

Aucune des valeurs personnelles visibles dans les photos de référence n’est enregistrée dans le gabarit ou les tests. Le test de non-rétention vérifie qu’un marqueur synthétique placé sur le verso ne ressort pas dans la réponse.

## Éclaircissement automatique des photos

Après le recadrage, l’application mesure la luminosité dans la zone des valeurs de la carte, afin de ne pas être guidée par le bureau sombre ou le portrait. Si cette zone est globalement sombre, une correction gamma bornée est appliquée à la luminance. En présence de zones claires et de grandes ombres, un gain local lissé et limité relève les ombres sans amplifier les blancs. Les couleurs restent traitées via la luminance Lab, sans binarisation ou génération de détails.

Une photo déjà suffisamment claire est renvoyée sans modification de ses pixels. Les seuils de contours sont également adaptés à la luminosité pendant la recherche de carte. Le fichier importé n’est jamais réécrit. L’aperçu PNG corrigé est conservé dans la session et transmis tel quel pour les découpes OCR ; aucune seconde correction n’est ajoutée à la lecture, ce qui évite de cumuler les éclaircissements.

Aucun curseur, filtre ou réglage utilisateur n’est ajouté. `alignment.lighting.applied` indique si l’éclaircissement a eu lieu ; une courte confirmation apparaît dans l’interface. Une photo presque noire reste signalée comme insuffisante : ce traitement ne peut pas récupérer des caractères absents, flous ou masqués par un reflet.

Les tests couvrent photo claire inchangée, exposition sombre, ombre locale, noirs/blancs préservés, avertissement sur image noire et cohérence entre aperçu et découpes. Une lecture Tesseract sur des champs synthétiques corrigés confirme la conservation des caractères ; aucun gain chiffré de PaddleOCR sur de vraies CNI n’est revendiqué par ces tests. Le test navigateur importe une photo sombre et vérifie la correction automatique sans nouveau contrôle.
