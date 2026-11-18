# -*- coding: utf-8 -*-
"""FLOKTRON · base_create.py — creates an empty FLOKTRON base (Excel file). Run once.

Usage:
    python3 scripts/base_create.py                      # uses config/config.yaml
    python3 scripts/base_create.py --config my.yaml     # other settings file
    python3 scripts/base_create.py --out base.xlsx      # other output file
    python3 scripts/base_create.py --force              # overwrite an existing base

No company data inside this file: departments (rays), people and addresses come from the config.
Without a config the base is created with the default rays and empty addresses.
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

DEFAULT_RAYS = [
    ("L1", "Sales and clients"),
    ("L2", "Stock"),
    ("L3", "Purchasing and suppliers"),
    ("L4", "Production and quality"),
    ("L5", "Logistics and delivery"),
    ("L6", "Marketing and social media"),
    ("L7", "Compliance, IP, grants, finance"),
    ("L8", "Market research and partners"),
]
# Default routes: a reply becomes the next task. Edit freely in the "Routes" sheet.
# Event "+" = done, "-" = not done. Keywords (; separated) must appear in the answer; empty = any answer.
# "To ray" "=" = the same ray. "*" in "From ray" = any ray. {task} and {report} are filled in.
DEFAULT_ROUTES = [
    ["M01", "L8", "+", "", "L1", "Contact the lead from market research: {report} (source task: {task})", 1, "Ray", "Yes", "lead → sales"],
    ["M02", "L6", "+", "request;enquiry;inquiry;client", "L1", "Answer the request from social media / website: {report}", 1, "Ray", "Yes", "request → sales"],
    ["M03", "L1", "+", "order", "L2", "Prepare the shipment for the order: {report}", 1, "Ray", "Yes", "order → stock"],
    ["M04", "L1", "+", "order", "L7", "Invoice / advance for the order: {report}", 1, "Company", "Yes", "order → finance"],
    ["M05", "L3", "+", "", "L5", "Receive the incoming goods: {report}", 1, "Ray", "Yes", "purchase → logistics"],
    ["M06", "L4", "+", "", "L2", "Take the finished batch into stock: {report}", 1, "Ray", "Yes", "production → stock"],
    ["M07", "L2", "+", "low;minimum;running out;reorder", "L3", "Reorder: {report}", 1, "Ray", "Yes", "stock → purchasing"],
    ["M08", "L2", "+", "shipped;ready to ship", "L5", "Deliver to the client: {report}", 1, "Ray", "Yes", "stock → logistics"],
    ["M99", "*", "-", "", "=", "{task}", 1, "Ray", "Yes", "any ray: not done → again next working day; second failure → manager"],
]

TASK_STATUSES = "New,Sent,Accepted,Question,Cannot,Done,Not done,Moved,Cancelled"
HEADER_FILL = PatternFill("solid", fgColor="1A365D")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def load_config(path):
    """Read config.yaml if it exists. Returns {} when there is no file."""
    if not os.path.exists(path):
        print(f"No config at {path} — using default rays, empty addresses.")
        return {}
    try:
        import yaml
    except ImportError:
        sys.exit("Missing package: run  pip install pyyaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def add_sheet(wb, name, head, rows=(), widths=None, first=False):
    ws = wb.active if first else wb.create_sheet(name)
    ws.title = name
    ws.append(head)
    for c in ws[1]:
        c.fill, c.font = HEADER_FILL, HEADER_FONT
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for r in rows:
        ws.append(list(r))
    for i, w in enumerate(widths or [18] * len(head), start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    return ws


def build(cfg):
    company = (cfg.get("company") or {}).get("name", "")
    manager = (cfg.get("mail") or {}).get("manager_address", "")
    rays_cfg = cfg.get("rays") or [{"id": i, "name": n} for i, n in DEFAULT_RAYS]
    today = datetime.date.today().isoformat()

    wb = openpyxl.Workbook()
    add_sheet(wb, "README", [f"FLOKTRON base · {company or 'your company'} · created {today}"], [
        ["Rays — who is responsible for each direction and where the morning message goes."],
        ["Tasks — what goes into the morning message (status not Done, date today or earlier)."],
        ["Receipts and Evening_reports are filled by the reply collector. Do not edit by hand."],
        ["Stock, Movements, Orders, Purchases, Rentals, Thresholds — fill in when the ray starts working."],
        ["Every figure carries a status: PUBLIC / ESTIMATE / SCENARIO / DEAL."],
    ], [120], first=True)

    rays = []
    for r in rays_cfg:
        rays.append([r.get("id", ""), r.get("name", ""), r.get("lead", ""),
                     r.get("email", "") or manager, r.get("language", "en"),
                     r.get("send_at", "07:40"), "Yes", "", r.get("lead_email", "")])
    rays.append(["L0", "Manager", "", manager, "en", "07:40", "Yes", "escalations end here", ""])
    add_sheet(wb, "Rays", ["ID", "Ray", "Responsible", "E-mail / messenger", "Language",
                           "Send at", "Active", "Comment", "Team lead e-mail"], rays,
              [6, 32, 18, 28, 9, 10, 8, 26, 28])

    ws = add_sheet(wb, "Tasks", ["Task ID", "Date", "Ray", "Task", "Source / rule", "Due",
                                 "Status", "Report (from evening reply)", "Updated", "Letter", "Route"],
                   [["T001", today, rays[0][0], "TEST: confirm you received this message", "setup",
                     today, "New", "", "", "", ""]],
                   [10, 11, 6, 70, 22, 11, 12, 40, 16, 16, 30])
    dv = DataValidation(type="list", formula1=f'"{TASK_STATUSES}"')
    ws.add_data_validation(dv)
    dv.add("G2:G5000")

    add_sheet(wb, "Routes", ["ID", "From ray", "Event (+ / −)", "Keywords in report (; separated)",
                             "To ray", "Task template ({task}, {report})", "Due, working days",
                             "Decision level", "Active", "Comment"],
              DEFAULT_ROUTES, [6, 8, 10, 30, 8, 60, 10, 12, 8, 34])
    add_sheet(wb, "Escalation", ["Level", "Who", "After, hours without reply", "Comment"],
              [["1", "Ray", "", "the person who got the task"],
               ["2", "Team lead", "24", ""],
               ["3", "Manager (L0)", "48", ""]], [8, 20, 22, 30])
    add_sheet(wb, "Receipts", ["Received", "Message ID", "Ray", "Answer", "Comment", "From",
                               "Mail Message-ID"], widths=[17, 16, 6, 12, 50, 26, 40])
    add_sheet(wb, "Evening_reports", ["Received", "Message ID", "Ray", "Report text", "From",
                                      "Mail Message-ID"], widths=[17, 16, 6, 80, 26, 40])
    add_sheet(wb, "Stock", ["Item", "Code", "Unit", "On hand", "Counted on", "Min. stock",
                            "Figure status", "Comment"], widths=[36, 12, 6, 10, 12, 10, 13, 24])
    add_sheet(wb, "Movements", ["Date", "Code", "In / Out / Packing / Scrap", "Qty", "Batch",
                                "Document", "Comment"], widths=[11, 10, 24, 9, 12, 18, 30])
    add_sheet(wb, "Orders", ["ID", "Date", "Client", "What", "Qty", "Advance paid", "Status",
                             "Delivery", "Comment"], widths=[8, 11, 26, 26, 8, 12, 12, 16, 30])
    add_sheet(wb, "Purchases", ["ID", "Supplier", "Item code", "Qty", "Ordered", "Expected",
                                "Status", "Tracking", "Comment"], widths=[8, 20, 10, 8, 12, 12, 12, 20, 30])
    add_sheet(wb, "Rentals", ["Item no.", "Type / size", "Where (site)", "From", "Status", "Comment"],
              widths=[9, 14, 26, 11, 12, 30])
    add_sheet(wb, "Thresholds", ["Rule", "Parameter", "Value", "Figure status", "Comment"], [
        ["Finished stock", "warn when fewer days of stock than", "", "ESTIMATE", ""],
        ["Receipt", "reminder if no 'Accepted' by", "08:30", "SCENARIO", ""],
        ["Receipt", "summary to manager at", "09:00", "SCENARIO", ""],
        ["Client", "escalate after hours without reply", "24", "SCENARIO", ""],
    ], [24, 40, 10, 13, 24])
    add_sheet(wb, "Run_log", ["Date/time", "Script", "What was done", "Result"],
              [[datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "base_create", "empty base created", "OK"]],
              [17, 20, 60, 20])
    return wb


def main():
    ap = argparse.ArgumentParser(description="Create an empty FLOKTRON base.")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "floktron_base.xlsx"))
    ap.add_argument("--force", action="store_true", help="overwrite an existing base")
    a = ap.parse_args()

    if os.path.exists(a.out) and not a.force:
        sys.exit(f"Base already exists: {a.out}  (use --force to overwrite)")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    build(load_config(a.config)).save(a.out)
    print("OK:", a.out)


if __name__ == "__main__":
    main()
