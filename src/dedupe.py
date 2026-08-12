"""
Dédoublonnage & golden record (entity resolution) — module réutilisable.

Étapes : standardisation -> blocking -> scoring flou (rapidfuzz) -> clustering
(union-find) -> survivorship (golden record) -> évaluation vs vérité terrain.
Aucune règle n'utilise `true_id` (réservé à l'évaluation).
"""
from __future__ import annotations
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
import pandas as pd
from rapidfuzz import fuzz

# ---------------------------------------------------------------- standardisation
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

def _norm_text(s) -> str:
    if pd.isna(s) or s is None:
        return ""
    return _strip_accents(str(s)).lower().strip()

def _norm_phone(s) -> str:
    d = "".join(ch for ch in str(s) if ch.isdigit()) if pd.notna(s) else ""
    return d[-9:] if len(d) >= 9 else ""          # 9 derniers chiffres = clé stable

def _norm_birth(s) -> str:
    if pd.isna(s) or not str(s).strip():
        return ""
    t = str(s).strip()
    if "/" in t:                                   # DD/MM/YYYY -> YYYY-MM-DD
        d, m, y = t.split("/"); return f"{y}-{m}-{d}"
    return t

def standardize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["name_norm"] = (df["first_name"].map(_norm_text) + " " + df["last_name"].map(_norm_text)).str.strip()
    df["email_norm"] = df["email"].map(_norm_text)
    df["phone_norm"] = df["phone"].map(_norm_phone)
    df["birth_norm"] = df["birthdate"].map(_norm_birth)
    df["city_norm"] = df["city"].map(_norm_text)
    return df

# ---------------------------------------------------------------- blocking + score
def _blocks(df: pd.DataFrame) -> set[tuple[int, int]]:
    """Génère les paires candidates (indices) via des clés de blocking."""
    pairs: set[tuple[int, int]] = set()
    for key_col, use in [("email_norm", True), ("phone_norm", True)]:
        groups = defaultdict(list)
        for idx, val in df[key_col].items():
            if val:
                groups[val].append(idx)
        for members in groups.values():
            pairs.update(combinations(sorted(members), 2))
    # bloc "initiale du nom normalisé" pour rattraper email/phone manquants
    groups = defaultdict(list)
    for idx, val in df["name_norm"].items():
        if val:
            groups[val.split()[-1][:1]].append(idx)   # 1re lettre du dernier token
    for members in groups.values():
        if len(members) <= 400:                        # évite les blocs géants
            pairs.update(combinations(sorted(members), 2))
    return pairs

def _is_match(a: pd.Series, b: pd.Series) -> bool:
    name_sim = fuzz.token_sort_ratio(a["name_norm"], b["name_norm"]) / 100
    same_email = bool(a["email_norm"]) and a["email_norm"] == b["email_norm"]
    same_phone = bool(a["phone_norm"]) and a["phone_norm"] == b["phone_norm"]
    same_birth = bool(a["birth_norm"]) and a["birth_norm"] == b["birth_norm"]
    return (
        same_email                                   # email = ancre forte
        or (same_phone and name_sim >= 0.60)
        or (name_sim >= 0.85 and same_birth)
    )

# ---------------------------------------------------------------- union-find
class _UF:
    def __init__(self, ids): self.p = {i: i for i in ids}
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b): self.p[self.find(a)] = self.find(b)

def cluster(df: pd.DataFrame) -> pd.Series:
    """Renvoie un id d'entité (golden_id) par ligne."""
    uf = _UF(df.index)
    for i, j in _blocks(df):
        if _is_match(df.loc[i], df.loc[j]):
            uf.union(i, j)
    roots = {r: k + 1 for k, r in enumerate(sorted({uf.find(i) for i in df.index}))}
    return pd.Series({i: roots[uf.find(i)] for i in df.index})

# ---------------------------------------------------------------- survivorship
def _best(values) -> str:
    vals = [v for v in values if isinstance(v, str) and v.strip()]
    if not vals:
        return ""
    # valeur la plus fréquente ; à égalité, la plus longue (plus complète)
    freq = Counter(vals)
    top = max(freq.values())
    return sorted([v for v, c in freq.items() if c == top], key=len, reverse=True)[0]

def golden_record(df: pd.DataFrame) -> pd.DataFrame:
    """Un enregistrement de référence par entité (règles de survivorship)."""
    rows = []
    for gid, g in df.groupby("golden_id"):
        rows.append({
            "golden_id": gid,
            "first_name": _best(g["first_name"]),
            "last_name": _best(g["last_name"]),
            "email": _best(g["email"]),
            "phone": _best(g["phone"]),
            "city": _best(g["city"]),
            "birthdate": _best(g["birthdate"]),
            "n_sources": g["row_id"].nunique(),
        })
    return pd.DataFrame(rows).sort_values("golden_id").reset_index(drop=True)

# ---------------------------------------------------------------- évaluation
def evaluate(df: pd.DataFrame) -> dict:
    """Précision/rappel par PAIRES vs true_id (les clusters vs la vérité)."""
    def positive_pairs(label_col):
        s = set()
        for _, g in df.groupby(label_col):
            s.update(combinations(sorted(g.index), 2))
        return s
    pred = positive_pairs("golden_id")
    true = positive_pairs("true_id")
    tp = len(pred & true)
    prec = tp / len(pred) if pred else 1.0
    rec = tp / len(true) if true else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4),
            "paires_predites": len(pred), "paires_vraies": len(true)}
