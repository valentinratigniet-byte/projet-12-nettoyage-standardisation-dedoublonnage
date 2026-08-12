# Rapport de dédoublonnage — golden records

Fusion de 2 fichiers clients hétérogènes en un référentiel unique.

## Avant / après

| Indicateur | Valeur |
|---|---:|
| Lignes en entrée (2 sources) | 1280 |
| Enregistrements de référence (golden) | 813 |
| Doublons résolus | 467 (36.5 %) |
| Personnes réelles (vérité terrain) | 800 |

## Qualité du matching (par paires, vs vérité terrain)

| Métrique | Score |
|---|---:|
| Précision | 97.2% |
| Rappel | 95.9% |
| F1 | 96.5% |

## Exemple de fusion (une même personne, plusieurs variantes)

| Source | Prénom | Nom | Email | Téléphone |
|---|---|---|---|---|
| A | ÉRIC | BOULAY | eric.boulay@example.com | 0498926610 |
| A | ÉRIC | BOULAY | eric.boulay@example.com | nan |
| A | éric | boulay | eric.boulay@example.com | 33456327560 |
| B | Éric | Boulay | eric.boulay@example.com | 33-45-63-27-56-0 |
| B | Eric | Boulay | eric.boulay@example.com | nan |

## Règles de survivorship
- Chaque champ du golden record = valeur **la plus fréquente** de l'entité ; à égalité, la **plus complète** (plus longue).
- Traçabilité complète dans `data/crosswalk.csv` (row_id → golden_id).