"""One version everywhere: README «Version X.Y.Z», the first CHANGELOG entry, START.md and llms-full.txt.

release.yml makes the tag and the GitHub Release from README and CHANGELOG, so if these agree, the Release,
README and CHANGELOG agree too. floktron.com is checked against the latest Release by the website's own
«Site sync check». Outside reviewers read CHANGELOG first — it must never lag behind a Release.
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()

def readme_version():
    m = re.search(r"Version (\d+\.\d+\.\d+)", read("README.md"))
    assert m, "README.md has no «Version X.Y.Z» line"
    return m.group(1)

def changelog_versions():
    return re.findall(r"^## (\d+\.\d+\.\d+) — (\d\d\.\d\d\.\d{4})", read("CHANGELOG.md"), re.M)

def test_changelog_first_entry_is_readme_version():
    v = readme_version()
    entries = changelog_versions()
    assert entries, "CHANGELOG.md has no «## X.Y.Z — DD.MM.YYYY» entries"
    assert entries[0][0] == v, f"README says {v}, CHANGELOG starts with {entries[0][0]}"

def test_changelog_is_newest_first_without_gaps_in_order():
    vs = [tuple(int(x) for x in v.split(".")) for v, _ in changelog_versions()]
    assert vs == sorted(vs, reverse=True), "CHANGELOG entries must be newest first"
    assert len(vs) == len(set(vs)), "a version appears twice in CHANGELOG"

def test_start_and_llms_full_show_the_same_version():
    v = readme_version()
    for name in ("START.md", "llms-full.txt"):
        m = re.search(r"Version (\d+\.\d+\.\d+) · last update", read(name))
        assert m and m.group(1) == v, f"{name} shows {m and m.group(1)}, README {v} — run scripts/build_llms_full.py"

def test_llms_txt_points_to_live_sources():
    t = read("llms.txt")
    assert "CHANGELOG.md" in t and "releases/latest" in t
