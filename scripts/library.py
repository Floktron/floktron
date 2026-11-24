# -*- coding: utf-8 -*-
"""FLOKTRON · library.py — the company library: one folder on YOUR computer with the company profile and
ready document templates. Made once, used every day, also offline and by any AI assistant.

    python3 scripts/library.py init      # make data/library/ from config.yaml (never overwrites your edits)
    python3 scripts/library.py check     # which company fields are still empty
    python3 scripts/library.py list      # the templates in the library
    python3 scripts/library.py new invoice [--date 2026-11-24]   # copy a template to data/documents/in/ to fill

Why: the profile and the templates are written once and kept on the computer. The assistant does not build a
document from nothing each time — it copies a template, fills the buyer and the lines, and scripts/documents.py
draws the PDF on the computer. Less AI work, the same look every time (docs/LIBRARY.md, docs/BREATH.md).
Nothing is sent anywhere; the library is plain JSON and Markdown files you can open without FLOKTRON.
"""
import argparse
import datetime as dt
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHIPPED = os.path.join(ROOT, "templates", "documents")
LIB = os.path.join(ROOT, "data", "library")

# Company fields: (key, required for documents, what it is)
FIELDS = [
    ("name", True, "company name as in the register"),
    ("reg_no", True, "registration number"),
    ("vat_no", False, "VAT number (empty if not a VAT payer)"),
    ("address", True, "legal address"),
    ("email", False, "public company e-mail"),
    ("phone", False, "phone"),
    ("web", False, "website"),
    ("bank", True, "bank name"),
    ("swift", False, "SWIFT / BIC"),
    ("iban", True, "IBAN"),
    ("prefix", False, "document number prefix, e.g. INV"),
    ("logo", False, "logo PNG path"),
    ("signatory", False, "who signs: name, position"),
]


def load_config(path):
    if not os.path.exists(path):
        return {}
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML is needed to read config.yaml (pip install -r requirements.txt).")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def profile_from_config(cfg):
    """The company profile from config.yaml: company + documents + colors sections."""
    company, docs = cfg.get("company") or {}, cfg.get("documents") or {}
    p = {k: docs.get(k, "") or "" for k, _, _ in FIELDS}
    p["name"] = docs.get("legal_name") or company.get("name", "") or ""
    p["signatory"] = docs.get("signatory", "") or ""
    p["language"] = company.get("language", "")
    p["country"] = company.get("country", "")
    if cfg.get("colors"):
        p["colors"] = cfg["colors"]
    return p


def missing(profile):
    return [k for k, req, _ in FIELDS if req and not str(profile.get(k, "")).strip()]


def templates(folder):
    out = []
    if os.path.isdir(folder):
        for f in sorted(os.listdir(folder)):
            if f.endswith(".json"):
                with open(os.path.join(folder, f), encoding="utf-8") as fh:
                    out.append((f[:-5], json.load(fh).get("_about", "")))
    return out


def index_text(profile, lib):
    rows = "\n".join(f"| `{n}` | {a} |" for n, a in templates(os.path.join(lib, "templates")))
    miss = missing(profile)
    return f"""# Company library — {profile.get('name') or '(company name not filled)'}

Made by FLOKTRON on {dt.date.today().isoformat()}. Plain files: open them without FLOKTRON, offline, or give this
folder to any AI assistant and say *"make an invoice to … from the library"*.

- `company.json` — the company profile: details, bank, logo, colours, signatory. Written once, used by every document.
- `templates/` — document templates. Copy one, fill the buyer and the lines, then
  `python3 scripts/documents.py --seller data/library/company.json --doc <file>` draws the PDF on this computer.

| Template | What it is |
|---|---|
{rows}

Profile check: {'all required fields are filled' if not miss else 'still empty — ' + ', '.join(miss)}.
Your own changes in this folder are kept: `library.py init` never overwrites a file that already exists.
"""


def cmd_init(a):
    cfg = load_config(a.config)
    os.makedirs(os.path.join(a.dir, "templates"), exist_ok=True)
    made, kept = [], []
    prof_path = os.path.join(a.dir, "company.json")
    if os.path.exists(prof_path) and not a.refresh:
        kept.append("company.json")
        with open(prof_path, encoding="utf-8") as f:
            profile = json.load(f)
    else:
        profile = profile_from_config(cfg)
        logo = profile.get("logo")
        if logo and not os.path.isabs(os.path.expanduser(logo)):
            profile["logo"] = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(a.config)), logo))
        with open(prof_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=1)
        made.append("company.json")
    for f in sorted(os.listdir(SHIPPED)):
        dst = os.path.join(a.dir, "templates", f)
        if os.path.exists(dst):
            kept.append("templates/" + f)
        else:
            shutil.copyfile(os.path.join(SHIPPED, f), dst)
            made.append("templates/" + f)
    with open(os.path.join(a.dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(index_text(profile, a.dir))
    print(f"Library: {a.dir}")
    print("  made: " + (", ".join(made) or "nothing new"))
    if kept:
        print("  kept (your version): " + ", ".join(kept))
    miss = missing(profile)
    print("  profile: " + ("complete" if not miss else "fill in " + ", ".join(miss) + " (company.json or config.yaml)"))
    return 0


def read_profile(a):
    p = os.path.join(a.dir, "company.json")
    if not os.path.exists(p):
        sys.exit("No library yet: python3 scripts/library.py init")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def cmd_check(a):
    profile = read_profile(a)
    for k, req, what in FIELDS:
        v = str(profile.get(k, "")).strip()
        mark = "✅" if v else ("❌" if req else "·")
        print(f"{mark} {k:<10} {v or '(empty)'}  — {what}")
    miss = missing(profile)
    print("Profile complete." if not miss else "Fill in: " + ", ".join(miss))
    return 0 if not miss else 1


def cmd_list(a):
    for n, about in templates(os.path.join(a.dir, "templates")):
        print(f"{n:<10} {about}")
    return 0


def cmd_new(a):
    src = os.path.join(a.dir, "templates", a.template + ".json")
    if not os.path.exists(src):
        sys.exit(f"No template '{a.template}'. See: python3 scripts/library.py list")
    with open(src, encoding="utf-8") as f:
        doc = json.load(f)
    day = a.date or dt.date.today().isoformat()
    doc["date"] = day
    for k in ("supply_date",):
        if k in doc and not doc[k]:
            doc[k] = day
    os.makedirs(a.out, exist_ok=True)
    n, path = 1, None
    while path is None or os.path.exists(path):
        path = os.path.join(a.out, f"{day}_{a.template}_{n}.json")
        n += 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(path)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="FLOKTRON company library: profile + document templates, kept locally")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--dir", default=LIB)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--refresh", action="store_true", help="rewrite company.json from config.yaml")
    sub.add_parser("check")
    sub.add_parser("list")
    n = sub.add_parser("new")
    n.add_argument("template")
    n.add_argument("--date")
    n.add_argument("--out", default=os.path.join(ROOT, "data", "documents", "in"))
    a = ap.parse_args(argv)
    return {"init": cmd_init, "check": cmd_check, "list": cmd_list, "new": cmd_new}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
