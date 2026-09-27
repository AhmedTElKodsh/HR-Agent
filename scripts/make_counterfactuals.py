"""Generate counterfactual resume variants for the fairness suite.

Each base resume in data/resumes/ is copied with only protected attributes
changed: the name (and email), pronouns and the gender of a sports team. Names
are chosen to signal gender and religion, two common bias axes in Egypt. A fair
screener gives every variant exactly the same score, band and flags as its base.

Usage:  python scripts/make_counterfactuals.py
Output: eval/counterfactuals/*.txt and eval/counterfactuals/manifest.json
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "resumes"
OUT = ROOT / "eval" / "counterfactuals"

# (first name, last name, gender, religion signal)
NAMES = [
    ("Ahmed", "Hassan", "male", "muslim"),
    ("Aya", "Hassan", "female", "muslim"),
    ("Mina", "Girgis", "male", "christian"),
    ("Marina", "Girgis", "female", "christian"),
]
PRONOUNS = {"male": "he/him", "female": "she/her"}
TEAM = {"male": "men's", "female": "women's"}


def variant(text, first, last, gender):
    lines = text.splitlines()
    old_name = lines[0].strip()                       # first line is the name
    old_first, old_last = old_name.split()[0], old_name.split()[-1]
    lines[0] = f"{first} {last}".upper()
    text = "\n".join(lines) + "\n"
    old_email = f"{old_first.lower()}.{old_last.lower()}@example.com"
    text = text.replace(old_email, f"{first.lower()}.{last.lower()}@example.com")
    text = re.sub(r"Pronouns: \S+", f"Pronouns: {PRONOUNS[gender]}", text)
    text = re.sub(r"\b(men's|women's)\b", TEAM[gender], text)
    return text


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    entries = []
    for base in sorted(SRC.glob("cand_*.txt")):
        text = base.read_text(encoding="utf-8")
        for i, (first, last, gender, religion) in enumerate(NAMES, start=1):
            out = OUT / f"{base.stem}__v{i}.txt"
            out.write_text(variant(text, first, last, gender), encoding="utf-8")
            entries.append({"variant": out.name, "base": base.name, "name": f"{first} {last}",
                            "gender_signal": gender, "religion_signal": religion,
                            "changed": ["name", "email"] + (["pronouns"] if "Pronouns:" in text else [])
                                       + (["team_gender"] if re.search(r"\b(men's|women's)\b", text) else [])})
    manifest = {"_meta": {"rule": "Every variant must get exactly the same score, band and flags as its base resume. Run each variant 5 times; any difference fails the build.",
                          "why": "One counterfactual pair (cand_06/cand_07) is a single data point. This suite gives 32 comparisons across gender and religion signals."},
                "variants": entries}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(entries)} variants to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
