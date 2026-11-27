# -*- coding: utf-8 -*-
"""FLOKTRON · dashboard.py — one page that shows the whole system at a glance: data/dashboard.html

Open it by double-click (computer) or from your cloud folder app (phone). It works offline: no internet,
no outside fonts or scripts, nothing is sent anywhere. The page re-reads itself every 15 minutes;
scripts/run.py rebuilds it after every run (collect, morning, news, …).

What it shows: health of the system (ring N/M + chips), "needs your attention", rays — who confirmed the morning
message, open tasks, people's answers for 14 days, voice reports, posts of the day, radar signals, consultations
with deadlines, supply chain signals, Telegram leads, and a player for the latest audio summary.

    python3 scripts/dashboard.py [--config config/config.yaml] [--out data/dashboard.html] [--json]
Language: company.language in config (en | ru | lv; others fall back to English).
Colours: colors.main / colors.ok in config; the accent of FLOKTRON itself is violet.
"""
import argparse
import datetime
import glob
import html
import json
import os
import re
import sys

import worktime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
DONE = {"Done", "Cancelled", "Moved", "Closed"}
OKANS = {"Accepted", "Report", "Done"}
BADANS = {"Question", "Cannot", "No answer"}

T = {
    "en": dict(bills="Invoices → accounting", b_docs="documents", b_sum="EUR in invoices", b_paid="payment found in statement", b_topay="EUR to pay / check", none_bills="All invoices paid and checked", no_bills="No invoices yet — scripts/invoices.py adds them", title="control panel", upd="updated", all_ok="Everything works", notes="Works, with notes",
               check="Something to check", sub="{ok} of {n} systems fine · {a} item(s) need you", calm="Nothing needs your attention",
               att="Needs your attention", next="Coming up", rays="Rays — who confirmed today's tasks", tasks="Open tasks",
               answers="People's answers, 14 days", ok_l="confirmed / report", bad_l="question / no answer",
               voice="Voice reports", posts="Posts today", radar="Radar: news and signals", chain="Supply chain",
               sys="Systems", audio="Audio summary", audio_none="appears after the first morning summary",
               k_open="open tasks", k_done="accepted / done", k_sig="signals in 7 days", k_leads="Telegram leads",
               none_att="✅ All quiet — get on with the work.", none_next="No deadlines ahead", none_tasks="No open tasks",
               none_voice="None yet. A team member sends a voice message to your bot — the text appears here.",
               none_posts="No posts planned today", none_sig="No new signals", none_chain="No notable changes",
               test="test", foot="the page refreshes itself · your data stays on your computer", days="in {d} d.",
               today="today", tomorrow="tomorrow", late="overdue", due="due", waiting="waiting", nolet="no message yet",
               hidden="+ test tasks hidden: {n}", jobs=("Replies", "Morning message", "News slice", "Supply chain", "Content plan", "Backup"), fixbackup="backup password set? see docs/MOVE.md", open="open", fixlog="see data/run.log", fixbot="is the bot running?", fixmail="is the mail server reachable? see data/run.log", tasks_act="Tasks", inbox="Mail waits for you", i_need="wait for you", i_star="starred, no answer", i_week="messages in 7 days", i_all="in the register", none_inbox="Everything answered 👍", no_inbox="No mail register yet — scripts/mail_watch.py keeps it (docs/MAIL_WATCH.md)", i_rem="reminded", i_att="Mail waits", prosp="New customers: why now", none_prosp="No new prospects", no_prosp="Not switched on: scripts/prospects.py (docs/PROSPECTS.md)", p_new="new", p_top="priority 1"),
    "ru": dict(bills="Счета → бухгалтерия", b_docs="документов", b_sum="EUR по счетам", b_paid="оплата найдена в выписке", b_topay="EUR к оплате / проверить", none_bills="Все счета оплачены и сверены", no_bills="Счетов пока нет — их добавляет scripts/invoices.py", title="пульт управления", upd="обновлено", all_ok="Всё работает", notes="Работает, есть заметки",
               check="Есть что проверить", sub="{ok} из {n} систем в порядке · {a} пункт(ов) требуют внимания",
               calm="Ничего не требует вашего внимания", att="Требует внимания", next="Ближайшее",
               rays="Лучи — кто подтвердил задачи", tasks="Открытые задачи", answers="Ответы людей за 14 дней",
               ok_l="подтвердили / отчёт", bad_l="вопрос / нет ответа", voice="Голосовые отчёты", posts="Соцсети сегодня",
               radar="Радар: новости и сигналы", chain="Цепочка поставок", sys="Системы", audio="Аудио-сводка",
               audio_none="появится после первой утренней сводки", k_open="задач в работе", k_done="принято / готово",
               k_sig="сигналов за 7 дн.", k_leads="лидов из Telegram", none_att="✅ Всё спокойно — можно заниматься делом.",
               none_next="Сроков впереди нет", none_tasks="Открытых задач нет",
               none_voice="Пока нет. Сотрудник отправляет голосовое боту — здесь появится текст.",
               none_posts="Сегодня по плану постов нет", none_sig="Новых сигналов нет", none_chain="Без заметных изменений",
               test="тест", foot="страница обновляется сама · данные только на вашем компьютере", days="через {d} дн.",
               today="сегодня", tomorrow="завтра", late="просрочено", due="срок", waiting="ждём ответ", nolet="писем нет",
               hidden="+ тестовых задач скрыто: {n}", jobs=("Сбор ответов", "Утренние письма", "Срез новостей", "Цепочка поставок", "Контент-план", "Резервная копия"), fixbackup="пароль бэкапа задан? см. docs/MOVE.md", open="открыто", fixlog="см. data/run.log", fixbot="бот запущен?", fixmail="почтовый сервер доступен? см. data/run.log", tasks_act="Задачи", inbox="Почта ждёт ответа", i_need="ждут вас", i_star="со ⭐ без ответа", i_week="писем за 7 дней", i_all="всего в реестре", none_inbox="Всё отвечено 👍", no_inbox="Реестра почты пока нет — его ведёт scripts/mail_watch.py (docs/MAIL_WATCH.md)", i_rem="напомнено", i_att="Письмо ждёт", prosp="Новые клиенты: почему сейчас", none_prosp="Новых кандидатов нет", no_prosp="Не включено: scripts/prospects.py (docs/PROSPECTS.md)", p_new="новых", p_top="приоритет 1"),
    "lv": dict(bills="Rēķini → grāmatvedība", b_docs="dokumenti", b_sum="EUR rēķinos", b_paid="maksājums atrasts izrakstā", b_topay="EUR jāmaksā / jāpārbauda", none_bills="Visi rēķini apmaksāti un pārbaudīti", no_bills="Rēķinu vēl nav — tos pievieno scripts/invoices.py", title="vadības panelis", upd="atjaunots", all_ok="Viss strādā", notes="Strādā, ir piezīmes",
               check="Ir ko pārbaudīt", sub="{ok} no {n} sistēmām kārtībā · {a} punkti prasa uzmanību",
               calm="Nekas neprasa jūsu uzmanību", att="Prasa uzmanību", next="Tuvākais", rays="Virzieni — kas apstiprināja",
               tasks="Atvērtie uzdevumi", answers="Atbildes 14 dienās", ok_l="apstiprināja / atskaite", bad_l="jautājums / nav atbildes",
               voice="Balss atskaites", posts="Ieraksti šodien", radar="Radars: ziņas un signāli", chain="Piegādes ķēde",
               sys="Sistēmas", audio="Audio kopsavilkums", audio_none="parādīsies pēc pirmā rīta kopsavilkuma",
               k_open="atvērti uzdevumi", k_done="pieņemti / gatavi", k_sig="signāli 7 dienās", k_leads="Telegram pieteikumi",
               none_att="✅ Viss mierīgi.", none_next="Termiņu nav", none_tasks="Atvērtu uzdevumu nav",
               none_voice="Vēl nav. Darbinieks sūta balss ziņu botam — šeit parādīsies teksts.", none_posts="Šodien ierakstu nav",
               none_sig="Jaunu signālu nav", none_chain="Būtisku izmaiņu nav", test="tests",
               foot="lapa atjaunojas pati · dati paliek jūsu datorā", days="pēc {d} d.", today="šodien", tomorrow="rīt",
               late="nokavēts", due="termiņš", waiting="gaidām", nolet="vēstuļu nav", hidden="+ testa uzdevumi paslēpti: {n}", jobs=("Atbilžu vākšana", "Rīta vēstules", "Ziņu apskats", "Piegādes ķēde", "Satura plāns", "Rezerves kopija"), fixbackup="vai rezerves kopijas parole iestatīta? skat. docs/MOVE.md", open="atvērti", fixlog="skat. data/run.log", fixbot="vai bots strādā?", fixmail="vai pasta serveris pieejams? skat. data/run.log", tasks_act="Uzdevumi", inbox="Pasts gaida atbildi", i_need="gaida jūs", i_star="ar ⭐ bez atbildes", i_week="vēstules 7 dienās", i_all="reģistrā kopā", none_inbox="Uz visu atbildēts 👍", no_inbox="Pasta reģistra vēl nav — to ved scripts/mail_watch.py (docs/MAIL_WATCH.md)", i_rem="atgādināts", i_att="Vēstule gaida", prosp="Jauni klienti: kāpēc tieši tagad", none_prosp="Jaunu kandidātu nav", no_prosp="Nav ieslēgts: scripts/prospects.py (docs/PROSPECTS.md)", p_new="jauni", p_top="1. prioritāte"),
}


STATUS = {  # how stored English statuses are shown
    "ru": {"Accepted": "Принято", "Question": "Вопрос", "Cannot": "Не могу", "No answer": "Нет ответа", "Report": "Отчёт",
           "Done": "Готово", "Sent": "Отправлено", "New": "Новая", "Moved": "Перенесено", "Not done": "Не сделано",
           "confirm": "подтвердить", "reply": "ответить", "reply?": "ответить?", "decide: attend?": "решить: участвовать?",
           "check deadline": "проверить срок", "read": "прочитать", "starred, waiting": "⭐ отложено"},
    "lv": {"Accepted": "Pieņemts", "Question": "Jautājums", "Cannot": "Nevaru", "No answer": "Nav atbildes", "Report": "Atskaite",
           "Done": "Gatavs", "Sent": "Nosūtīts", "New": "Jauns", "Moved": "Pārcelts", "Not done": "Nav izdarīts",
           "confirm": "apstiprināt", "reply": "atbildēt", "reply?": "atbildēt?", "decide: attend?": "izlemt: piedalīties?",
           "check deadline": "pārbaudīt termiņu", "read": "izlasīt", "starred, waiting": "⭐ atlikts"},
}


def tr(lang, word):
    return STATUS.get(lang, {}).get(str(word), str(word))


def d_of(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(v or ""))
    if m:
        return datetime.date(*map(int, m.groups()))
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", str(v or ""))
    return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def sheet(path, name):
    """Rows of a sheet as dicts by header (header = first row with ≥3 filled cells)."""
    if not path or not os.path.exists(path):
        return []
    import openpyxl
    import safe_xlsx  # noqa: F401 — project rule for every script that touches .xlsx (this one only reads)
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 — a locked or broken file must not stop the page
        return []
    if name not in wb.sheetnames:
        return []
    rows = list(wb[name].iter_rows(values_only=True))
    for i, r in enumerate(rows[:8]):
        if sum(1 for c in r if c not in (None, "")) >= 3:
            hdr = [str(c or "").strip() for c in r]
            return [dict(zip(hdr, x)) for x in rows[i + 1:] if any(c not in (None, "") for c in x)]
    return []


def g(row, *names):
    for n in names:
        if row.get(n) not in (None, ""):
            return row[n]
    return ""


def load_cfg(path):
    if not path or not os.path.exists(path):
        return {}
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------- collect
def collect(cfg, data=DATA, now=None):
    now = now or datetime.datetime.now()
    today = now.date()
    lang = (cfg.get("company") or {}).get("language", "en")
    L = T.get(lang, T["en"])
    D = dict(lang=lang if lang in T else "en", org=(cfg.get("company") or {}).get("name", ""), updated=now.strftime("%d.%m.%Y %H:%M"),
             attention=[], pulse=[])
    base, radar, content = (os.path.join(data, f) for f in ("floktron_base.xlsx", "floktron_radar.xlsx", "floktron_content.xlsx"))

    # health: the run log of scripts/run.py
    runs = {}
    log = os.path.join(data, "run.log")
    if os.path.exists(log):
        with open(log, encoding="utf-8", errors="replace") as f:
            job, when = None, None
            for line in f.read().splitlines()[-3000:]:
                m = re.match(r"=== (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) (\w+)", line)
                if m:
                    when, job = m.group(1), m.group(2)
                    continue
                m = re.match(r"--- exit (\d+)", line)
                if m and job:
                    runs[job] = (when, int(m.group(1)))

    def age_h(ts):
        return (now - datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M")).total_seconds() / 3600

    def job(name, label, max_h, fix):
        if name not in runs:
            return
        when, code = runs[name]
        st = "bad" if code else ("ok" if age_h(when) <= max_h else "warn")
        D["pulse"].append(dict(name=label, st=st, note=when[5:], fix=fix if st != "ok" else ""))

    J = L["jobs"]
    job("collect", J[0], 2, L["fixmail"])
    job("morning", J[1], 80, L["fixlog"])
    job("news", J[2], 30, L["fixlog"])
    job("supply", J[3], 30, L["fixlog"])
    job("content", J[4], 30, L["fixlog"])
    job("backup", J[5], 24 * 8, L["fixbackup"])      # weekly archive of the whole setup (docs/MOVE.md)
    tg = sheet(os.path.join(data, "tg_signals.xlsx"), "Runs")
    if tg:
        r = tg[-1]
        ok = d_of(g(r, "Run")) == today and not g(r, "Failed")
        D["pulse"].append(dict(name="Telegram", st="ok" if ok else "warn", note=str(g(r, "Run"))[5:16],
                               fix="" if ok else L["fixbot"]))
    for p in D["pulse"]:
        if p["st"] != "ok":
            D["attention"].append(dict(lvl=p["st"], text=f"{p['name']}: {p['note']}", act=p["fix"]))

    # rays and tasks
    rays, tasks, rec = sheet(base, "Rays"), sheet(base, "Tasks"), sheet(base, "Receipts")
    ans = {str(g(r, "Message ID")): (str(g(r, "Answer")), str(g(r, "Received"))) for r in rec if g(r, "Message ID")}
    D["rays"] = []
    for r in rays:
        if str(g(r, "Active")).lower() not in ("yes", "да", "jā", "true", "1"):
            continue
        rid = str(g(r, "ID"))
        mine = [t for t in tasks if str(g(t, "Ray")) == rid]
        letters = sorted({str(g(t, "Letter")) for t in mine if g(t, "Letter")})
        last = letters[-1] if letters else ""
        a = ans.get(last)
        open_ = [t for t in mine if str(g(t, "Status")) not in DONE]
        over = [t for t in open_ if d_of(g(t, "Due")) and d_of(g(t, "Due")) < today]
        st = "idle" if not last else "ok" if a and a[0] in OKANS else "warn" if a and a[0] in BADANS else "wait"
        test = "test" in str(g(r, "Responsible", "Comment")).lower()
        D["rays"].append(dict(id=rid, name=str(g(r, "Ray")), who=str(g(r, "Responsible")), st=st, test=test,
                              answer=tr(lang, a[0]) if a else (L["waiting"] if last else L["nolet"]), when=(a[1][5:16] if a else ""),
                              open=len(open_), over=len(over)))
        if over and not test:
            D["attention"].append(dict(lvl="warn", text=f"{rid} {g(r, 'Ray')}: {L['late']} {len(over)}", act=L["tasks_act"]))
        if st == "warn" and not test:
            D["attention"].append(dict(lvl="warn", text=f"{rid} {g(r, 'Responsible')}: «{tr(lang, a[0])}»", act=""))
    openall = [t for t in tasks if str(g(t, "Status")) not in DONE]
    D["kpi"] = dict(open=len(openall), done=sum(1 for t in tasks if str(g(t, "Status")) in ("Done", "Accepted")))
    real = [t for t in openall if not str(g(t, "Task")).upper().startswith("TEST")]
    D["tasks"] = [dict(id=str(g(t, "Task ID")), ray=str(g(t, "Ray")), text=str(g(t, "Task"))[:110], st=tr(lang, g(t, "Status")),
                       due=(d_of(g(t, "Due")).strftime("%d.%m") if d_of(g(t, "Due")) else ""),
                       over=bool(d_of(g(t, "Due")) and d_of(g(t, "Due")) < today))
                  for t in sorted(real, key=lambda t: str(g(t, "Due") or "9"))[:8]]
    D["tasks_test"] = len(openall) - len(real)
    days = [today - datetime.timedelta(days=i) for i in range(13, -1, -1)]
    D["answers14"] = [dict(d=d.strftime("%d.%m"), ok=sum(1 for r in rec if d_of(g(r, "Received")) == d and str(g(r, "Answer")) in OKANS),
                           bad=sum(1 for r in rec if d_of(g(r, "Received")) == d and str(g(r, "Answer")) in BADANS)) for d in days]

    # invoices → accounting (sheet "Invoices", written by scripts/invoices.py)
    B = dict(n=0, test=0, sum=0.0, paid=0, fin=0, topay=0.0, items=[])
    for r in sheet(base, "Invoices"):
        if not g(r, "ID"):
            continue
        is_test = str(g(r, "Comment")).upper().startswith("TEST")
        B["n"] += 1
        B["test"] += is_test
        st, typ, tot = str(g(r, "Status") or ""), str(g(r, "Type") or ""), float(g(r, "Total") or 0)
        if "not an invoice" in typ:
            continue
        B["fin"] += 1
        B["sum"] += 0 if st.startswith("Closed") else tot
        B["paid"] += st.startswith(("Paid", "Closed"))
        B["topay"] += tot if st.startswith(("To pay", "Not found")) else 0
        if not st.startswith(("Paid", "Closed")) or "no final invoice" in st:
            lvl = "bad" if st.startswith("Not found") else "warn" if "no final invoice" in st else "wait"
            B["items"].append(dict(lvl=lvl, test=is_test, text=f'{g(r, "Supplier")} · {typ} {g(r, "Document no.")} · {tot:.2f} EUR', sub=st))
            if lvl == "bad" and not is_test:
                D["attention"].append(dict(lvl="warn", text=f'{L["bills"]}: {g(r, "Supplier")} {g(r, "Document no.")} — {st}', act=""))
    B["items"].sort(key=lambda x: {"bad": 0, "warn": 1}.get(x["lvl"], 2))
    D["bills"] = B

    # mail waits for you (sheet "Mail", written by scripts/mail_watch.py)
    MB = dict(n=0, week=0, need=0, star=0, items=[])
    for r in sheet(base, "Mail"):
        if not g(r, "Message-ID"):
            continue
        MB["n"] += 1
        dd = d_of(g(r, "Date"))
        if dd and dd >= today - datetime.timedelta(days=7):
            MB["week"] += 1
        if str(g(r, "Direction")).startswith("→"):
            continue
        st, need, star = str(g(r, "Status")), str(g(r, "Need")), g(r, "Star") == "⭐"
        if st.lower().startswith(("closed", "answered")) or g(r, "Answered") == "yes":
            continue
        if not (need and need != "invoice → check") and not star:
            continue
        if dd and dd < today - datetime.timedelta(days=21):
            continue
        is_test = str(g(r, "Comment")).upper().startswith("TEST")
        MB["need"] += 1
        MB["star"] += star
        who = str(g(r, "Organisation") or g(r, "From / To"))
        lvl = "bad" if need in ("confirm", "reply") else "warn" if need else "wait"
        if need.startswith("deadline: "):
            need = {"ru": "срок", "lv": "termiņš"}.get(lang, "deadline") + need[8:]
        MB["items"].append(dict(lvl=lvl, test=is_test, d=str(g(r, "Date")), text=f'{"⭐ " if star and need else ""}{tr(lang, need or "starred, waiting")} · {who[:40]}',
                                sub=f'«{str(g(r, "Subject"))[:90]}» · {dd.strftime("%d.%m") if dd else ""} {str(g(r, "Date"))[11:16]}' + (f' · {L["i_rem"]} {g(r, "Reminded")}' if g(r, "Reminded") else "")))
        if lvl == "bad" and not is_test and dd and dd <= today - datetime.timedelta(days=1):
            D["attention"].append(dict(lvl="warn", text=f'{L["i_att"]}: {tr(lang, need)} — {who[:30]}: «{str(g(r, "Subject"))[:50]}»', act=""))
    MB["items"].sort(key=lambda x: ({"bad": 0, "warn": 1}.get(x["lvl"], 2), x["d"]))
    D["inbox"] = MB

    # new customers (sheet "Prospects" in the radar base, written by scripts/prospects.py)
    PR = dict(n=0, new=0, top=0, items=[])
    for r in sheet(radar, "Prospects"):
        if not g(r, "Reg. no."):
            continue
        PR["n"] += 1
        if str(g(r, "Status")) != "New":
            continue
        PR["new"] += 1
        p = int(g(r, "Priority") or 3)
        PR["top"] += p == 1
        PR["items"].append(dict(p=p, s=-(float(g(r, "Score") or 0)), url=str(g(r, "Source")), test=str(g(r, "Comment")).upper().startswith("TEST"),
                                text=f'{str(g(r, "Company"))[:45]}', sub=f'{str(g(r, "Why now"))[:90]}' + (f' · {g(r, "Town")}' if g(r, "Town") else "")))
    PR["items"].sort(key=lambda x: (x["p"], x["s"]))
    D["prospects"] = PR

    # radar
    sig = [s for s in sheet(radar, "Signal_feed") if d_of(g(s, "Date")) and d_of(g(s, "Date")) >= today - datetime.timedelta(days=7)]
    D["signals"] = [dict(src=str(g(s, "Source"))[:40], title=str(g(s, "Title"))[:95], url=str(g(s, "URL")), rel=str(g(s, "Relevance 1–5")))
                    for s in sig[-5:]][::-1]
    D["kpi"]["sig"] = len(sig)
    nxt = []
    for c in sheet(radar, "Consultations"):
        dl = d_of(g(c, "Open until"))
        if dl and dl >= today:
            nxt.append(dict(t=dl.strftime("%d.%m"), days=(dl - today).days, title=str(g(c, "Title"))[:90], url=str(g(c, "URL"))))
    D["next"] = sorted(nxt, key=lambda x: x["days"])[:6]
    for n in D["next"]:
        if n["days"] <= 3:
            D["attention"].append(dict(lvl="warn", text=f"{L['due']} {n['t']}: {n['title'][:60]}", act=""))

    # supply chain (sheet written by supply_watch.py)
    sc = sheet(radar, "Watch_log")
    lastd = max((d_of(g(x, "Date")) for x in sc if d_of(g(x, "Date"))), default=None)
    cl = [x for x in sc if d_of(g(x, "Date")) == lastd]
    st_of = lambda x: str(g(x, "Status"))  # noqa: E731
    D["chain"] = dict(date=lastd.strftime("%d.%m") if lastd else "", g=sum("🟢" in st_of(x) for x in cl), y=sum("🟡" in st_of(x) for x in cl),
                      r=sum("🔴" in st_of(x) for x in cl),
                      alerts=[dict(obj=str(g(x, "Object", "Name")), st=st_of(x), text=str(g(x, "Event / news", "Event", "Note"))[:90])
                              for x in cl if st_of(x) in ("🟡", "🔴")][:3])

    # content of the day
    D["posts"] = [dict(plat=str(g(p, "Platform")), text=f"{g(p, 'Time')} · {str(g(p, 'Hook'))[:90]}")
                  for p in sheet(content, "Plan") if d_of(g(p, "Date")) == today]

    # Telegram leads, voice reports
    D["kpi"]["leads"] = len(sheet(os.path.join(data, "floktron_leads.xlsx"), "Leads"))
    vr = sheet(os.path.join(data, "voice_reports.xlsx"), "Voice")
    D["voice"] = [dict(d=str(g(v, "Date"))[5:16], who=str(g(v, "Who / ray")), text=str(g(v, "Transcript", "Status"))[:140],
                       new=str(g(v, "Status")) == "New") for v in vr[-5:]][::-1]

    # audio summary (written by the morning AI run, read aloud by the bot)
    vc = ((cfg.get("telegram") or {}).get("voice") or {})
    pdir = vc.get("pulse_dir") or ""
    au = sorted(glob.glob(os.path.join(os.path.expanduser(pdir), "pulse_*.m4a"))) if pdir and os.path.isabs(os.path.expanduser(pdir)) else \
        sorted(glob.glob(os.path.join(data, "audio", "pulse_*.m4a")))
    D["audio"] = au[-1] if au else ""
    # work time (data/worktime.jsonl, marks from the bot — scripts/worktime.py, docs/WORKTIME.md)
    D["worktime"] = None
    if (cfg.get("worktime") or {}).get("enabled") or os.path.exists(worktime.events_path(cfg, data)):
        D["worktime"] = worktime.collect(cfg, data, now)
        D["attention"] += D["worktime"]["attention"]
    D["score"] = dict(ok=sum(1 for p in D["pulse"] if p["st"] == "ok"), n=len(D["pulse"]))
    D["attention"].sort(key=lambda a: {"bad": 0, "warn": 1}.get(a["lvl"], 2))
    return D


# ---------------------------------------------------------------- render
CSS = """
:root{--ink:#14213a;--mut:#5f6b7a;--bg:#f3f3f3;--card:#fff;--line:#e3e6ea;--main:MAIN;--acc:#8B5CF6;--okc:OKC;
--ok:#3f8f22;--okbg:#e9f5e3;--warn:#b7791f;--warnbg:#fdf3e1;--bad:#c53030;--badbg:#fdecec;--wait:#2b6cb0;--waitbg:#e8f0fa}
@media (prefers-color-scheme:dark){:root{--ink:#e8edf4;--mut:#9aa6b5;--bg:#0f1724;--card:#182235;--line:#26334a;--okbg:#1d3320;--warnbg:#3a2e17;--badbg:#3b1d1d;--waitbg:#1b2c45}}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink)}
a{color:inherit}header{background:var(--main);color:#fff;padding:18px 18px 54px;border-bottom:4px solid var(--acc)}
.top{display:flex;align-items:center;gap:12px;max-width:1180px;margin:0 auto}.logo{width:38px;height:38px;flex:none}.logo svg{display:block;width:38px;height:38px}
.top h1{font-size:19px;margin:0}.top small{display:block;opacity:.75;font-size:12.5px}.upd{margin-left:auto;text-align:right;font-size:12.5px;opacity:.85}
main{max-width:1180px;margin:-40px auto 40px;padding:0 14px}
.hero{display:grid;grid-template-columns:auto 1fr;gap:18px;align-items:center;background:var(--card);border-radius:18px;padding:18px;box-shadow:0 4px 18px rgba(16,32,64,.10)}
.ring{width:118px;height:118px;position:relative}.ring svg{transform:rotate(-90deg)}.ring b{position:absolute;inset:0;display:grid;place-items:center;font-size:30px;font-weight:800}
.hero h2{margin:0 0 6px;font-size:21px}.hero p{margin:0 0 10px;color:var(--mut)}
.chips{display:flex;flex-wrap:wrap;gap:6px}.chip{font-size:12.5px;padding:5px 10px;border-radius:999px;font-weight:600}
.ok{background:var(--okbg);color:var(--ok)}.warn{background:var(--warnbg);color:var(--warn)}.bad{background:var(--badbg);color:var(--bad)}.wait{background:var(--waitbg);color:var(--wait)}.idle{background:var(--bg);color:var(--mut)}
.play{display:flex;align-items:center;gap:12px;margin-top:12px;background:var(--bg);border-radius:14px;padding:10px 12px}.play audio{width:100%;height:34px}
.grid{display:grid;gap:14px;grid-template-columns:repeat(12,1fr);margin-top:14px}
.card{background:var(--card);border-radius:16px;padding:16px;box-shadow:0 1px 3px rgba(16,32,64,.07);grid-column:span 6;min-width:0}.w12{grid-column:span 12}.w4{grid-column:span 4}.w8{grid-column:span 8}
@media (max-width:860px){.card,.w4,.w8{grid-column:span 12}.hero{grid-template-columns:1fr;justify-items:center;text-align:center}.chips{justify-content:center}}
.card h3{margin:0 0 12px;font-size:15.5px}.list{list-style:none;margin:0;padding:0}.list li{display:flex;gap:10px;align-items:flex-start;padding:9px 0;border-top:1px solid var(--line)}
.list li:first-child{border-top:0;padding-top:2px}.dot{width:9px;height:9px;border-radius:50%;margin-top:6px;flex:none}
.dot.ok{background:var(--ok)}.dot.warn{background:var(--warn)}.dot.bad{background:var(--bad)}.dot.wait{background:var(--wait)}.dot.idle{background:#717171}
.t{flex:1;min-width:0}.t b{font-weight:600}.sub{display:block;font-size:12.5px;color:var(--mut)}.act{font-size:12px;color:var(--mut)}
.tag{font-size:11.5px;padding:2px 8px;border-radius:6px;font-weight:600}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.kpi{background:var(--bg);border-radius:12px;padding:10px 12px}.kpi b{display:block;font-size:24px;font-weight:800}.kpi span{font-size:12px;color:var(--mut)}
.rays{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px}.ray{border:1px solid var(--line);border-radius:12px;padding:11px 12px;position:relative}
.ray .id{font-size:11px;color:var(--mut);font-weight:700}.ray .nm{font-weight:600;margin:2px 0 6px}.ray .tst{position:absolute;top:9px;right:10px;font-size:10px;color:var(--mut);border:1px solid var(--line);border-radius:5px;padding:0 5px}
.bars{display:flex;gap:4px;align-items:flex-end;height:74px}.bar{flex:1;display:flex;flex-direction:column;justify-content:flex-end;gap:2px}
.bar i{display:block;border-radius:3px 3px 0 0;min-height:2px}.bar i.o{background:var(--okc)}.bar i.x{background:#d69e2e;border-radius:0}
.legend{display:flex;gap:12px;font-size:11.5px;color:var(--mut);margin-top:6px}.legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:4px}
.empty{color:var(--mut);font-size:13.5px}
.wt{display:grid;grid-template-columns:1fr 1fr;gap:18px}.wt h4{margin:2px 0 8px;font-size:13.5px;color:var(--mut)}.tw{overflow-x:auto}
.tb{width:100%;border-collapse:collapse;font-size:13.5px}.tb th{font-size:11.5px;color:var(--mut);font-weight:600;text-align:right;padding:4px 6px}
.tb td{border-top:1px solid var(--line);padding:6px;text-align:right}.tb td:first-child,.tb th:first-child{text-align:left;white-space:nowrap}
@media (max-width:860px){.wt{grid-template-columns:1fr}}footer{text-align:center;color:var(--mut);font-size:12px;margin:24px 0 10px}
@media (max-width:520px){.kpis{grid-template-columns:1fr 1fr}.rays{grid-template-columns:1fr 1fr;gap:8px}.list li{flex-wrap:wrap}.act{flex-basis:100%;padding-left:19px}}
"""


# FLOKTRON mark (assets/brand/floktron-mark.svg): violet tile, white F whose middle bar is a dot
MARK = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="15" fill="#8B5CF6"/>'
        '<path d="M17 13h31v10H28v7h-11zM17 30h11v21H17z" fill="#fff"/><circle cx="41" cy="35.5" r="6.5" fill="#fff"/></svg>')
FAVICON = "data:image/svg+xml," + MARK.replace('"', "'").replace("#", "%23").replace("<", "%3C").replace(">", "%3E")

def esc(s):
    return html.escape(str(s or ""), quote=True)


def link(url, text):
    return f'<a href="{esc(url)}" rel="noopener noreferrer">{esc(text)}</a>' if str(url).startswith("https://") else esc(text)


def render(D, colors=None):
    L = T[D["lang"]]
    colors = colors or {}
    css = CSS.replace("MAIN", re.sub(r"[^#0-9A-Fa-f]", "", str(colors.get("main") or "#1A365D"))[:7]) \
             .replace("OKC", re.sub(r"[^#0-9A-Fa-f]", "", str(colors.get("ok") or "#4A9928"))[:7])
    ok, n, att = D["score"]["ok"], D["score"]["n"], D["attention"]
    head = L["all_ok"] if not att else (L["check"] if any(a["lvl"] == "bad" for a in att) else L["notes"])
    sub = L["sub"].format(ok=ok, n=n, a=len(att)) if att else L["calm"]
    frac = ok / n if n else 1
    col = "#4A9928" if frac == 1 else "#d69e2e" if frac >= .7 else "#c53030"
    c = 2 * 3.14159 * 50
    ring = (f'<div class="ring"><svg width="118" height="118" viewBox="0 0 118 118"><circle cx="59" cy="59" r="50" fill="none" stroke="var(--line)" stroke-width="11"/>'
            f'<circle cx="59" cy="59" r="50" fill="none" stroke="{col}" stroke-width="11" stroke-linecap="round" stroke-dasharray="{c*frac:.1f} {c:.1f}"/></svg><b>{ok}/{n}</b></div>')

    def li(dot, title, sub_="", right=""):
        return f'<li><span class="dot {dot}"></span><span class="t"><b>{title}</b>{f"<span class=sub>{sub_}</span>" if sub_ else ""}</span>{right}</li>'

    def lst(items, empty):
        return f'<ul class="list">{"".join(items) or f"<li class=empty>{esc(empty)}</li>"}</ul>'

    chips = "".join(f'<span class="chip {p["st"]}">{"✓" if p["st"] == "ok" else "!"} {esc(p["name"])}</span>' for p in D["pulse"])
    audio = (f'<div class="play"><span class="t"><b>{L["audio"]}</b><span class="sub">{esc(os.path.basename(D["audio"]))}</span>'
             f'<audio controls preload="none" src="{esc(os.path.relpath(D["audio"], D.get("_outdir", DATA)))}"></audio></span></div>') if D["audio"] else \
        f'<div class="play"><span class="t"><b>{L["audio"]}</b><span class="sub">{L["audio_none"]}</span></span></div>'
    rays = ""
    for r in D["rays"]:
        extra = (f' · {L["open"]} {r["open"]}' if r["open"] else "") + (f' · {L["late"]} {r["over"]}' if r["over"] else "")
        tst = f'<span class="tst">{L["test"]}</span>' if r["test"] else ""
        rays += (f'<div class="ray">{tst}<div class="id">{esc(r["id"])}</div>'
                 f'<div class="nm">{esc(r["name"])}</div><span class="tag {r["st"]}">{esc(r["answer"])}</span> '
                 f'<span class="sub">{esc(r["who"])}{" · " + esc(r["when"]) if r["when"] else ""}{esc(extra)}</span></div>')
    mx = max([a["ok"] + a["bad"] for a in D["answers14"]] + [1])
    bars = "".join(f'<div class="bar" title="{a["d"]}"><i class="x" style="height:{a["bad"]/mx*64:.0f}px"></i><i class="o" style="height:{a["ok"]/mx*64:.0f}px"></i></div>' for a in D["answers14"])
    k = D["kpi"]
    kp = "".join(f'<div class="kpi"><b>{v}</b><span>{esc(t)}</span></div>' for v, t in
                 ((k["open"], L["k_open"]), (k["done"], L["k_done"]), (k.get("sig", 0), L["k_sig"]), (k.get("leads", 0), L["k_leads"])))
    bl = D.get("bills") or dict(n=0)
    if bl["n"]:
        kb = "".join(f'<div class="kpi"><b>{v}</b><span>{esc(t)}</span></div>' for v, t in (
            (bl["n"], L["b_docs"] + (f' ({L["test"]}: {bl["test"]})' if bl["test"] else "")), (f'{bl["sum"]:,.2f}'.replace(",", " "), L["b_sum"]),
            (f'{bl["paid"]}/{bl["fin"]}', L["b_paid"]), (f'{bl["topay"]:,.2f}'.replace(",", " "), L["b_topay"])))
        bills = f'<div class="kpis" style="margin-bottom:10px">{kb}</div>' + lst(
            [li(x["lvl"], esc(x["text"]), esc(x["sub"]), f'<span class="tag idle">{L["test"]}</span>' if x["test"] else "") for x in bl["items"][:8]], L["none_bills"])
    else:
        bills = lst([], L["no_bills"])
    mb = D.get("inbox") or dict(n=0)
    if mb["n"]:
        ki = "".join(f'<div class="kpi"><b>{v}</b><span>{esc(t)}</span></div>' for v, t in (
            (mb["need"], L["i_need"]), (mb["star"], L["i_star"]), (mb["week"], L["i_week"]), (mb["n"], L["i_all"])))
        inbox = f'<div class="kpis" style="margin-bottom:10px">{ki}</div>' + lst(
            [li(x["lvl"], esc(x["text"]), esc(x["sub"]), f'<span class="tag idle">{L["test"]}</span>' if x["test"] else "") for x in mb["items"][:10]], L["none_inbox"])
    else:
        inbox = lst([], L["no_inbox"])
    pr_ = D.get("prospects") or dict(n=0)
    if pr_["n"]:
        kq = "".join(f'<div class="kpi"><b>{v}</b><span>{esc(t)}</span></div>' for v, t in ((pr_["new"], L["p_new"]), (pr_["top"], L["p_top"])))
        prosp = f'<div class="kpis" style="margin-bottom:10px">{kq}</div>' + lst(
            [li("ok" if x["p"] == 1 else "wait", link(x["url"], x["text"]), esc(x["sub"]), f'<span class="tag idle">{L["test"]}</span>' if x["test"] else "") for x in pr_["items"][:6]], L["none_prosp"])
    else:
        prosp = lst([], L["no_prosp"])
    wt = D.get("worktime")
    work = ""
    if wt:
        WL = worktime.texts(D["lang"])
        kw = "".join(f'<div class="kpi"><b>{v}</b><span>{esc(t)}</span></div>' for v, t in (
            (f'{wt["now"]}/{wt["team"]}' if wt["team"] else wt["now"], WL["k_now"]), (wt["today"], WL["k_today"]),
            (worktime.hnum(wt["month"] * 60), WL["k_month"]), (len([f for f in wt["flags"] if f["lvl"] == "warn"]), WL["k_flags"])))
        ppl = lst([li(x["st"], esc(x["name"]), esc(x["when"]) + (f' · <span class="tag {"warn" if x["far"] else "ok"}">📍 {esc(x["site"])}</span>' if x["site"] else ""),
                      f'<span class="act"><b>{esc(x["h"])}</b></span>') for x in wt["on"]], WL["none"])
        mrows = "".join(f'<tr><td>{esc(m["name"])}</td><td>{m["days"]}</td><td><b>{worktime.hnum(m["m"])}</b></td><td>{worktime.hnum(m["over"])}</td>'
                        f'<td>{worktime.hnum(m["night"])}</td><td>{worktime.hnum(m["wk"])}</td></tr>' for m in wt["mon"])
        mon = (f'<h4>{WL["month_head"]}</h4><div class="tw"><table class="tb"><tr><th></th><th>{WL["days"]}</th><th>{WL["hours"]}</th><th>{WL["over"]}</th>'
               f'<th>{WL["night"]}</th><th>{WL["weekend"]}</th></tr>{mrows}</table></div>') if mrows else ""
        fl = (f'<h4>⚠ {WL["k_flags"]}</h4>' + lst([li(f["lvl"], esc(f["name"]), esc(f["text"])) for f in wt["flags"]], "—")) if wt["flags"] else ""
        work = f'<div class="kpis" style="margin-bottom:10px">{kw}</div><div class="wt"><div>{ppl}</div><div>{mon}{fl}</div></div>'
    ch = D["chain"]
    chain = (f'<div class="chips" style="margin-bottom:8px"><span class="chip ok">🟢 {ch["g"]}</span><span class="chip warn">🟡 {ch["y"]}</span>'
             f'<span class="chip bad">🔴 {ch["r"]}</span><span class="sub">{esc(ch["date"])}</span></div>'
             + lst([li("bad" if a["st"] == "🔴" else "warn", esc(a["obj"]), esc(a["text"])) for a in ch["alerts"]], L["none_chain"]))
    nxt = lst([li("warn" if x["days"] <= 3 else "wait", link(x["url"], x["title"]),
                  L["today"] if x["days"] == 0 else L["tomorrow"] if x["days"] == 1 else L["days"].format(d=x["days"]) + " · " + x["t"]) for x in D["next"]], L["none_next"])
    return f"""<!DOCTYPE html><html lang="{D['lang']}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="900"><meta name="robots" content="noindex"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; media-src 'self' file:; img-src 'self' data:">
<link rel="icon" href="{FAVICON}"><title>FLOKTRON · {esc(D['org'])}</title><style>{css}</style></head><body>
<header><div class="top"><div class="logo">{MARK}</div><div><h1>FLOKTRON · {L['title']}</h1><small>{esc(D['org'])}</small></div><div class="upd">{L['upd']}<br><b>{esc(D['updated'])}</b></div></div></header>
<main><section class="hero">{ring}<div><h2>{head}</h2><p>{sub}</p><div class="chips">{chips}</div>{audio}</div></section><div class="grid">
<div class="card w8"><h3>⚡ {L['att']}</h3>{lst([li(a['lvl'], esc(a['text']), '', f'<span class=act>{esc(a["act"])}</span>' if a['act'] else '') for a in att[:8]], L['none_att'])}</div>
<div class="card w4"><h3>📅 {L['next']}</h3>{nxt}</div>
<div class="card w12"><div class="kpis">{kp}</div></div>
{f'<div class="card w12"><h3>⏱ {worktime.texts(D["lang"])["title"]}</h3>{work}</div>' if work else ''}
<div class="card w12"><h3>🧭 {L['rays']}</h3><div class="rays">{rays}</div></div>
<div class="card"><h3>✅ {L['tasks']}</h3>{lst([li('bad' if t['over'] else 'wait', esc(t['text']), esc(t['ray'] + ' · ' + t['st'] + (' · ' + L['due'] + ' ' + t['due'] if t['due'] else ''))) for t in D['tasks']], L['none_tasks'])}{f'<p class=sub>{L["hidden"].format(n=D["tasks_test"])}</p>' if D['tasks_test'] else ''}</div>
<div class="card w12"><h3>🧾 {L['bills']}</h3>{bills}</div>
<div class="card w12"><h3>📥 {L['inbox']}</h3>{inbox}</div>
<div class="card w12"><h3>🔎 {L['prosp']}</h3>{prosp}</div>
<div class="card"><h3>📊 {L['answers']}</h3><div class="bars">{bars}</div><div class="legend"><span><i style="background:var(--okc)"></i>{L['ok_l']}</span><span><i style="background:#d69e2e"></i>{L['bad_l']}</span></div></div>
<div class="card"><h3>🎙 {L['voice']}</h3>{lst([li('wait' if v['new'] else 'idle', esc(v['who'] + ' · ' + v['d']), esc(v['text'])) for v in D['voice']], L['none_voice'])}</div>
<div class="card"><h3>📣 {L['posts']}</h3>{lst([li('wait', esc(p['plat']), esc(p['text'])) for p in D['posts']], L['none_posts'])}</div>
<div class="card"><h3>📡 {L['radar']}</h3>{lst([li('wait', link(s['url'], s['title']), esc(s['src'])) for s in D['signals']], L['none_sig'])}</div>
<div class="card"><h3>🚚 {L['chain']}</h3>{chain}</div>
<div class="card w12"><h3>🩺 {L['sys']}</h3>{lst([li(p['st'], esc(p['name']), esc(p['note']), f'<span class=act>{esc(p["fix"])}</span>' if p['fix'] else '') for p in D['pulse']], '—')}</div>
</div><footer>FLOKTRON · {L['foot']}</footer></main></body></html>"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="FLOKTRON dashboard")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--data", default=DATA)
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    cfg = load_cfg(a.config)
    D = collect(cfg, a.data)
    if a.json:
        print(json.dumps(D, ensure_ascii=False, indent=1, default=str))
        return 0
    out = a.out or os.path.join(a.data, "dashboard.html")
    D["_outdir"] = os.path.dirname(os.path.abspath(out))
    os.makedirs(D["_outdir"], exist_ok=True)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(render(D, cfg.get("colors")))
    os.replace(tmp, out)
    print(f"dashboard: {out} · {D['score']['ok']}/{D['score']['n']} · attention {len(D['attention'])}")
    return 0


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    sys.exit(main())
