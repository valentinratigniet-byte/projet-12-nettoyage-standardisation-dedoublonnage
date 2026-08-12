"""
Pipeline complet de dédoublonnage.
  2 sources -> standardisation -> clustering flou -> golden record + crosswalk
  -> évaluation vs true_id -> rapport avant/après.

Usage : python src/run.py   (générer d'abord les sources : python src/generate_sources.py)
"""
from pathlib import Path
import pandas as pd

from dedupe import standardize, cluster, golden_record, evaluate

ROOT = Path(__file__).resolve().parent.parent
DATA, DOCS = ROOT / "data", ROOT / "docs"


def main() -> None:
    a = pd.read_csv(DATA / "source_a.csv", dtype=str)
    b = pd.read_csv(DATA / "source_b.csv", dtype=str)
    a["source"], b["source"] = "A", "B"
    df = pd.concat([a, b], ignore_index=True)
    df["true_id"] = df["true_id"].astype(int)

    df = standardize(df)
    df["golden_id"] = cluster(df)

    golden = golden_record(df)
    crosswalk = df[["row_id", "source", "golden_id", "true_id"]]
    metrics = evaluate(df)

    golden.to_csv(DATA / "golden_records.csv", index=False, encoding="utf-8")
    crosswalk.to_csv(DATA / "crosswalk.csv", index=False, encoding="utf-8")

    n_in = len(df)
    n_out = len(golden)
    dup_rate = round(100 * (n_in - n_out) / n_in, 1)

    # exemple de fusion (une entité regroupant plusieurs variantes)
    ex_id = df["golden_id"].value_counts().idxmax()
    ex = df[df["golden_id"] == ex_id][["source", "first_name", "last_name", "email", "phone"]]

    lines = [
        "# Rapport de dédoublonnage — golden records\n",
        "Fusion de 2 fichiers clients hétérogènes en un référentiel unique.\n",
        "## Avant / après\n",
        "| Indicateur | Valeur |", "|---|---:|",
        f"| Lignes en entrée (2 sources) | {n_in} |",
        f"| Enregistrements de référence (golden) | {n_out} |",
        f"| Doublons résolus | {n_in - n_out} ({dup_rate} %) |",
        f"| Personnes réelles (vérité terrain) | {df['true_id'].nunique()} |",
        "\n## Qualité du matching (par paires, vs vérité terrain)\n",
        "| Métrique | Score |", "|---|---:|",
        f"| Précision | {metrics['precision']:.1%} |",
        f"| Rappel | {metrics['recall']:.1%} |",
        f"| F1 | {metrics['f1']:.1%} |",
        "\n## Exemple de fusion (une même personne, plusieurs variantes)\n",
        "| Source | Prénom | Nom | Email | Téléphone |", "|---|---|---|---|---|",
    ]
    for _, r in ex.iterrows():
        lines.append(f"| {r['source']} | {r['first_name']} | {r['last_name']} | {r['email']} | {r['phone']} |")
    lines += ["\n## Règles de survivorship",
              "- Chaque champ du golden record = valeur **la plus fréquente** de l'entité ; "
              "à égalité, la **plus complète** (plus longue).",
              "- Traçabilité complète dans `data/crosswalk.csv` (row_id → golden_id)."]
    (DOCS / "rapport-dedoublonnage.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"{n_in} lignes -> {n_out} golden records ({dup_rate}% de doublons résolus)")
    print(f"Matching : précision {metrics['precision']:.1%} · rappel {metrics['recall']:.1%} · F1 {metrics['f1']:.1%}")
    print("Sorties : data/golden_records.csv, data/crosswalk.csv, docs/rapport-dedoublonnage.md")


if __name__ == "__main__":
    main()
