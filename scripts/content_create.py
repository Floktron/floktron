# -*- coding: utf-8 -*-
"""FLOKTRON · content_create.py — creates the content workbook (data/floktron_content.xlsx). Run once.

Sheets: Plan (posts with date, time, platform, text, picture, reason) · Reserve · Media (which picture or video
was already published on which platform — protection against duplicates) · Run_log.
Next to it: data/published_links.txt — paste the link of a published post there (one line, from the phone is fine);
content_check.py marks the post Published every morning.
The AI agent fills the plan (prompts/40_content_plan.md); content_check.py checks it every morning.
FLOKTRON never publishes by itself — a person copies the text and publishes.
"""
import argparse
import datetime
import os
import sys

try:
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:
    sys.exit("Missing package: run  pip install openpyxl")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORMS = ["Facebook", "Instagram", "LinkedIn", "TikTok", "YouTube", "X", "Telegram", "WhatsApp"]
PLAN = ["Date", "Time", "Platform", "Language", "Rubric", "Hook", "Text to copy", "First comment", "Picture / video file",
        "Alt text", "Reason / source", "Figures source", "Status", "Link after publishing", "Check"]
STATUSES = "Draft,Ready,Scheduled,Published,Moved,Duplicate,Cancelled"


LINKS_TEMPLATE = """# FLOKTRON · links of published posts
# Published a post? Paste its link below "## NEW" — one link per line. A note is optional:
#   https://www.linkedin.com/feed/update/urn:li:activity:...   personal profile
#   https://x.com/yourname/status/...
#   21.11 Instagram carousel        (no link? date + platform + a few words)
# Every morning content_check.py matches each line to the plan (platform from the link, date from the link
# or the note, ±1 day), sets status Published and moves the line under "## DONE".
# A line it cannot match stays here with "← no matching post".

## NEW

## DONE
"""


def sheet(wb, name, head, widths, first=False, rows=()):
    ws = wb.active if first else wb.create_sheet(name)
    ws.title = name
    ws.append(head)
    for c in ws[1]:
        c.fill, c.font = PatternFill("solid", fgColor="1A365D"), Font(bold=True, color="FFFFFF")
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    return ws


def build():
    wb = openpyxl.Workbook()
    w = [11, 7, 11, 8, 14, 30, 70, 30, 30, 30, 34, 24, 11, 36, 30]
    ws = sheet(wb, "Plan", PLAN, w, first=True)
    dv = DataValidation(type="list", formula1=f'"{STATUSES}"')
    ws.add_data_validation(dv)
    dv.add("M2:M3000")
    dv2 = DataValidation(type="list", formula1='"' + ",".join(PLATFORMS) + '"')
    ws.add_data_validation(dv2)
    dv2.add("C2:C3000")
    sheet(wb, "Reserve", PLAN[2:], w[2:])
    sheet(wb, "Media", ["Picture / video file", "What it shows"] + PLATFORMS, [36, 40] + [22] * len(PLATFORMS))
    sheet(wb, "Run_log", ["Date/time", "Run", "What was done", "Comment"], [17, 18, 60, 40],
          rows=[[datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "content_create", "empty content plan created", ""]])
    return wb


def main():
    ap = argparse.ArgumentParser(description="Create the FLOKTRON content workbook.")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "floktron_content.xlsx"))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if os.path.exists(a.out) and not a.force:
        sys.exit(f"Content plan already exists: {a.out}  (use --force to overwrite)")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    build().save(a.out)
    print("OK:", a.out)
    links = os.path.join(os.path.dirname(os.path.abspath(a.out)), "published_links.txt")
    if not os.path.exists(links):
        with open(links, "w", encoding="utf-8") as f:
            f.write(LINKS_TEMPLATE)
        print("OK:", links)


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    main()
