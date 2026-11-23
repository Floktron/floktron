# -*- coding: utf-8 -*-
"""Builds the FICTIONAL mailbox for tests/test_mail_watch.py: <folder>/*.eml + flags.json (built at test time,
because .eml files are never committed). Every company, person, address and number here is invented (domains
*.example.com). Run by hand: python3 make_fixtures.py <folder>"""
import json
import os
import sys
from email.message import EmailMessage
from email.utils import format_datetime
import datetime as dt
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, "..", "invoices", "docs", "Paraugs Reagenti", "Rekins_PR-2026-118.pdf")
OWN = "Demo SIA (TEST · FICTIONAL) <office@demo-sia.example.com>"
TZ = ZoneInfo("Europe/Riga")


def at(day, hm):
    h, m = map(int, hm.split(":"))
    return format_datetime(dt.datetime(2026, 11, day, h, m, tzinfo=TZ))


MAILS = [  # file, from, subject, date, body, extra headers, attachment
    ("01_confirm_lv", "Paraugu biedrība (TEST) <pasakumi@biedriba-paraugs.example.com>", "Seminārs par būvūdeņiem",
     at(23, "08:10"), "Labdien!\n\nLūdzam apstiprināt dalību semināram 04.12.2026 plkst. 10:00 līdz 30.11.2026.\n\nAr cieņu,\nAnna Parauga\n+372 5000 0001\nwww.biedriba-paraugs.example.com", {}, None),
    ("02_reply_en", "Max Muster (TEST) <buyer@muster-bau.example.com>", "Quantities for site 7",
     at(22, "14:00"), "Hello,\n\nplease send the quantities and the price for 40 bags before Friday.\n\nBest regards\nMax Muster\nMuster Bau GmbH (TEST · FICTIONAL)\n+49 30 0000 0000\nwww.muster-bau.example.com", {}, None),
    ("03_invite_ru", "Ivan Testov <ivan@klusa-buve.example.com>", "Приглашение на объект",
     at(23, "07:30"), "Добрый день!\n\nПриглашаем вас на встречу на объекте 2 декабря в 11:00.\n\nИван Тестов\n+372 5000 0003", {}, None),
    ("04_deadline_de", "Petra Probe <einkauf@musterchemie.example.com>", "Angebot",
     at(23, "09:00"), "Guten Tag,\n\nFrist für Ihr Angebot ist der 10.12.2026.\n\nPetra Probe", {}, None),
    ("05_question_et", "Mari Näidis <mari@naidis-keemia.example.com>", "Küsimus kotte kohta",
     at(22, "08:00"), "Tere!\n\nKas saate saata ka ohutuskaardi?\n\nMari", {}, None),
    ("06_invoice_lv", "Paraugs Reagenti (TEST) <rekini@paraugs-reagenti.example.com>", "Rēķins PR-2026-118",
     at(23, "06:40"), "Labdien, pielikumā rēķins.\n", {}, "Rekins_PR-2026-118.pdf"),
    ("07_newsletter", "Build News (TEST) <news@buildnews.example.com>", "Weekly: please reply to our survey",
     at(23, "05:00"), "Please reply to our survey. Deadline 30.11.2026.", {"List-Unsubscribe": "<mailto:unsub@buildnews.example.com>"}, None),
    ("08_notice_important", "VID demo portāls (TEST) <noreply@portals.vid-demo.example.com>", "Jauns ziņojums",
     at(23, "07:00"), "Jums ir jauns ziņojums portālā. Lūdzu pieslēdzieties.", {"Auto-Submitted": "auto-generated"}, None),
    ("09_code", "Some Service (TEST) <no-reply@service.example.com>", "Your verification code: 123456",
     at(23, "07:05"), "Your verification code is 123456.", {}, None),
    ("10_autoreply", "Jonas Bandomasis <jonas@bandomoji.example.com>", "Automatic reply: Kaina",
     at(23, "07:10"), "I am out of office until 30.11.2026.", {"Auto-Submitted": "auto-replied"}, None),
    ("11_system", "Demo SIA (TEST) <boss@demo-sia.example.com>", "FLOKTRON# L1 2026-11-23 ACCEPT",
     at(23, "07:45"), "OK", {}, None),
    ("12_star_lt", "Jonas Bandomasis <jonas@bandomoji.example.com>", "Katalogas",
     at(20, "10:00"), "Sveiki,\n\nsiunčiame katalogą.\n\nJonas\n+370 600 00000", {}, None),
    ("13_old_confirm", "Old Org (TEST) <office@old-org.example.com>", "Please confirm your attendance",
     at(16, "10:00"), "Dear partner, please confirm your attendance.", {}, None),
    ("14_sent_reply", OWN, "Re: Quantities for site 7",
     at(22, "16:00"), "Hello Max, 40 bags, price in the attached offer.\n\n> please send the quantities", {"In-Reply-To": "<02_reply_en@muster-bau.example.com>"}, None),
]


def main(out=None):
    OUT = out or (sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "mail"))
    os.makedirs(OUT, exist_ok=True)
    for name, frm, subj, date, body, extra, att in MAILS:
        m = EmailMessage()
        m["From"] = frm
        m["To"] = "buyer@muster-bau.example.com" if name.startswith("14") else OWN
        m["Subject"] = subj
        m["Date"] = date
        m["Message-ID"] = f"<{name}@{frm.split('@')[1].strip('>')}>"
        for k, v in extra.items():
            m[k] = v
        m.set_content(body)
        if att:
            with open(PDF, "rb") as f:
                m.add_attachment(f.read(), maintype="application", subtype="pdf", filename=att)
        with open(os.path.join(OUT, name + ".eml"), "wb") as f:
            f.write(bytes(m))
    with open(os.path.join(OUT, "flags.json"), "w", encoding="utf-8") as f:
        json.dump({"12_star_lt.eml": ["\\Flagged"]}, f, indent=1)
    return OUT


if __name__ == "__main__":
    main()
