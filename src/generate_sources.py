"""
Génère 2 exports clients hétérogènes (source_a, source_b) avec des doublons
volontaires et des variations réalistes : casse, accents, ordre du nom,
initiales, fautes de frappe, formats de téléphone/date, champs manquants.
`true_id` est conservé UNIQUEMENT pour évaluer le dédoublonnage (jamais utilisé
par le matching). Reproductible (seed fixe).
"""
import csv
import random
import unicodedata
from pathlib import Path
from faker import Faker

fake = Faker("fr_FR")
Faker.seed(42)
random.seed(42)

DATA = Path(__file__).resolve().parent.parent / "data"
N_PERSONS = 800


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def make_persons(n: int) -> list[dict]:
    people = []
    for i in range(n):
        first, last = fake.first_name(), fake.last_name()
        email = f"{strip_accents(first).lower()}.{strip_accents(last).lower()}@example.com"
        people.append({
            "true_id": i + 1, "first": first, "last": last, "email": email,
            "phone": fake.phone_number(),
            "city": fake.city(),
            "birth": fake.date_of_birth(minimum_age=18, maximum_age=90).isoformat(),
        })
    return people


def vary_name(first: str, last: str) -> tuple[str, str]:
    style = random.choice(["as_is", "upper", "lower", "swap", "initial", "accentless", "typo"])
    if style == "upper":  return first.upper(), last.upper()
    if style == "lower":  return first.lower(), last.lower()
    if style == "swap":   return last, first            # ordre inversé
    if style == "initial": return first[0] + ".", last
    if style == "accentless": return strip_accents(first), strip_accents(last)
    if style == "typo" and len(last) > 3:               # supprime une lettre
        i = random.randrange(len(last)); return first, last[:i] + last[i + 1:]
    return first, last


def vary_phone(ph: str) -> str:
    digits = "".join(ch for ch in ph if ch.isdigit())
    fmt = random.choice(["orig", "dashes", "plus", "raw", "missing"])
    if fmt == "missing":  return ""
    if fmt == "dashes":   return "-".join(digits[i:i + 2] for i in range(0, len(digits), 2))
    if fmt == "plus":     return "+33 " + digits[-9:]
    if fmt == "raw":      return digits
    return ph


def vary_birth(b: str) -> str:
    fmt = random.choice(["iso", "fr", "missing"])
    if fmt == "missing": return ""
    y, m, d = b.split("-")
    return f"{d}/{m}/{y}" if fmt == "fr" else b


def make_row(p: dict, row_id: str) -> dict:
    f, l = vary_name(p["first"], p["last"])
    return {
        "row_id": row_id, "true_id": p["true_id"],
        "first_name": f, "last_name": l,
        "email": p["email"] if random.random() > 0.10 else "",   # 10% email manquant
        "phone": vary_phone(p["phone"]),
        "city": random.choice([p["city"], p["city"].upper(), strip_accents(p["city"])]),
        "birthdate": vary_birth(p["birth"]),
    }


def write_source(path: Path, persons: list[dict], prefix: str, extra_dupes: int) -> int:
    rows, k = [], 1
    for p in persons:
        rows.append(make_row(p, f"{prefix}{k:05d}")); k += 1
    # doublons intra-source (même personne, autre variation)
    for p in random.sample(persons, extra_dupes):
        rows.append(make_row(p, f"{prefix}{k:05d}")); k += 1
    random.shuffle(rows)
    cols = ["row_id", "true_id", "first_name", "last_name", "email", "phone", "city", "birthdate"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    return len(rows)


def main() -> None:
    people = make_persons(N_PERSONS)
    a = people[:600]          # personnes 1..600
    b = people[200:]          # personnes 201..800  -> chevauchement 201..600 (400 communes)
    na = write_source(DATA / "source_a.csv", a, "A", extra_dupes=40)
    nb = write_source(DATA / "source_b.csv", b, "B", extra_dupes=40)
    print(f"source_a.csv : {na} lignes | source_b.csv : {nb} lignes | total {na + nb}")
    print(f"Personnes uniques réelles impliquées : {len({p['true_id'] for p in a + b})}")


if __name__ == "__main__":
    main()
