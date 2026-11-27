# -*- coding: utf-8 -*-
"""Fixes after the outside code review of v0.37.1 stay fixed (0.37.2). Offline, no network, fictional data only.
  1. mail: certificate check is relaxed only for Proton Bridge on this computer, or pinned to its exported certificate;
  2. run.py: one run at a time with an atomic OS lock that never goes stale;
  3. safe_xlsx: outside text never becomes a formula (all writers, sub-folders included);
  4. invoices: duplicates, payment matching, currency, incoming money, unreadable records."""
import json
import multiprocessing
import os
import shutil
import ssl
import subprocess
import sys

import openpyxl
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "scripts")
sys.path.insert(0, S)
import invoices as inv  # noqa: E402
import runlock  # noqa: E402
import safe_xlsx  # noqa: E402,F401
from mail import send  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "invoices")


# ---------------------------------------------------------------- 1. TLS
@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.2", "::1", "[::1]", "localhost", "LOCALHOST"])
def test_local_addresses(host):
    assert send.is_local(host)


@pytest.mark.parametrize("host", ["10.0.0.5", "192.168.1.10", "mail.example.com", "localhost.example.com",
                                  "127.0.0.1.example.com", "", None])
def test_not_local_addresses(host):
    assert not send.is_local(host)


def test_normal_servers_are_always_checked():
    ctx = send.tls_context("imap.gmail.com", False, {})
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname


def test_bridge_on_this_computer_only():
    ctx = send.tls_context("127.0.0.1", True, {})
    assert ctx.verify_mode == ssl.CERT_NONE
    with pytest.raises(send.MailError, match="Refused"):
        send.tls_context("bridge.example.com", True, {})
    with pytest.raises(send.MailError, match="Refused"):
        send.tls_context("192.168.1.20", True, {"imap_host": "192.168.1.20"})


def test_bridge_pinned_certificate(tmp_path):
    cert = tmp_path / "cert.pem"
    r = subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=127.0.0.1",
                        "-keyout", str(tmp_path / "key.pem"), "-out", str(cert), "-days", "2"],
                       capture_output=True) if shutil.which("openssl") else None
    if not r or r.returncode != 0:
        pytest.skip("openssl not available")
    ctx = send.tls_context("bridge.example.com", True, {"tls_cert": str(cert)})   # pinned: allowed even off this computer
    assert ctx.verify_mode == ssl.CERT_REQUIRED and not ctx.check_hostname
    assert len(ctx.get_ca_certs()) == 1                                             # exactly that certificate, nothing else
    with pytest.raises(send.MailError, match="not found"):
        send.tls_context("127.0.0.1", True, {"tls_cert": str(tmp_path / "missing.pem")})


def test_no_certificate_check_switched_off_anywhere_else():
    hits = []
    for d, _, files in os.walk(S):
        for f in files:
            if f.endswith(".py"):
                p = os.path.join(d, f)
                if "CERT_NONE" in open(p, encoding="utf-8").read() and not p.endswith(os.path.join("mail", "send.py")):
                    hits.append(os.path.relpath(p, S))
    assert not hits, f"certificate check switched off outside mail/send.py tls_context: {hits}"


# ---------------------------------------------------------------- 2. run lock
def _hold(path, ready, release):
    lk = runlock.RunLock(path)
    assert lk.acquire()
    ready.set()
    release.wait(20)
    lk.release()


def _try(path, q):
    lk = runlock.RunLock(path)
    q.put(lk.acquire())
    lk.release()


def test_lock_is_exclusive_between_processes(tmp_path):
    path = str(tmp_path / ".floktron.lock")
    ctx = multiprocessing.get_context("spawn")
    ready, release, q = ctx.Event(), ctx.Event(), ctx.Queue()
    holder = ctx.Process(target=_hold, args=(path, ready, release))
    holder.start()
    assert ready.wait(20)
    try:
        assert not runlock.RunLock(path).acquire()        # same moment, other process: refused
        rivals = [ctx.Process(target=_try, args=(path, q)) for _ in range(4)]
        for p in rivals:
            p.start()
        for p in rivals:
            p.join(20)
        assert [q.get(timeout=5) for _ in rivals] == [False] * 4
    finally:
        release.set()
        holder.join(20)
    lk = runlock.RunLock(path)                              # holder gone: free again
    assert lk.acquire()
    lk.release()


def test_lock_freed_when_a_run_crashes(tmp_path):
    path = str(tmp_path / ".floktron.lock")
    code = ("import os,sys; sys.path.insert(0, %r); import runlock; l = runlock.RunLock(%r); "
            "assert l.acquire(); os._exit(3)") % (S, path)
    assert subprocess.run([sys.executable, "-c", code]).returncode == 3   # died holding the lock, no clean-up
    lk = runlock.RunLock(path)
    assert lk.acquire(), "a crashed run must not leave a stale lock"
    assert "pid" in open(path).read()
    lk.release()


def test_old_lock_file_is_not_a_lock(tmp_path):
    path = tmp_path / ".floktron.lock"
    path.write_text("left over by FLOKTRON 0.37.1")
    lk = runlock.RunLock(str(path))
    assert lk.acquire()
    lk.release()


def test_run_py_uses_the_os_lock():
    src = open(os.path.join(S, "run.py"), encoding="utf-8").read()
    assert "RunLock(LOCK)" in src and "os.remove(LOCK)" not in src and "getmtime(LOCK)" not in src


# ---------------------------------------------------------------- 3. formulas
def test_every_xlsx_writer_in_every_folder_uses_safe_xlsx():
    missing = []
    for d, _, files in os.walk(S):
        for f in files:
            if f.endswith(".py") and f != "safe_xlsx.py":
                txt = open(os.path.join(d, f), encoding="utf-8").read()
                if "import openpyxl" in txt and "import safe_xlsx" not in txt:
                    missing.append(os.path.relpath(os.path.join(d, f), S))
    assert not missing, missing


def test_formula_like_text_stays_text(tmp_path):
    wb = openpyxl.Workbook()
    wb.active.append(['=CMD|" /C calc"!A0', "+1+1", "-2", "@SUM(1)", "=1+1", " =1+1"])
    p = tmp_path / "x.xlsx"
    wb.save(p)
    ws = openpyxl.load_workbook(p).active
    assert all(c.data_type == "s" for c in ws[1])                  # nothing is stored as a formula
    assert ws["A1"].value.startswith("'=") and ws["B1"].value == "+1+1" and ws["D1"].value == "@SUM(1)"


# ---------------------------------------------------------------- 4. invoices
def _doc(**k):
    d = dict(file="X/a.pdf", supplier="SIA Paraugs (TEST)", reg="LV40000000001", type="invoice", number="PR-2026/118",
             date="2026-11-10", due=None, net=100.0, vat=21.0, total=121.0, currency="EUR", pay_method="bank",
             bank_kw=["PARAUGS"])
    d.update(k)
    return d


def _t(amount, cp, details, date="2026-11-12", cur="EUR"):
    import datetime as dt
    return dict(date=dt.date.fromisoformat(date), cp=cp, amount=amount, details=details, cur=cur, code="CSV", arch=cp + details)


def test_number_must_stand_on_its_own():
    assert inv.number_in("PR-2026/118", "Rēķins PR 2026-118") == "strong"
    assert inv.number_in("2026110", "VS 2026110") == "strong"
    assert inv.number_in("12", "payment 2026-11-12") == "weak"    # short: never enough alone (next test)
    assert inv.number_in("118", "Rēķins PR-2026/118") == "weak"
    assert inv.number_in("7781", "Arve 77810") == ""             # part of a longer number
    assert inv.number_in("118", "inv 118") == "weak"
    assert inv.number_in("ABC", "ABC") == ""                      # no digit: not a number


def test_short_number_alone_does_not_mark_paid():
    doc = _doc(number="12", bank_kw=[])
    inv.match_payments([doc], [_t(121.0, "RIMI", "card 2026-11-12")])   # was a false "paid" before 0.37.2
    assert "pay" not in doc and doc.get("similar")
    doc = _doc(number="12")
    inv.match_payments([doc], [_t(121.0, "SIA PARAUGS", "rekins 12")])  # short number + name: taken
    assert doc["pay"]["how"] == "name + amount + date"


def test_legal_form_is_not_a_supplier_name():
    doc = _doc(number="Z-9", bank_kw=["SIA"])
    inv.match_payments([doc], [_t(121.0, "SIA CITS UZNEMUMS", "rekins")])
    assert "pay" not in doc


def test_other_currency_is_not_the_payment():
    doc = _doc(currency="USD")
    inv.match_payments([doc], [_t(121.0, "SIA PARAUGS", "PR-2026/118", cur="EUR")])
    assert "pay" not in doc
    doc = _doc()
    inv.match_payments([doc], [_t(121.0, "SIA PARAUGS", "PR-2026/118")])
    assert doc["pay"]["how"] == "number in payment"


def _csv(path, text):
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_signed_csv_skips_incoming_and_overlaps_count_once(tmp_path):
    a = _csv(tmp_path / "oct.csv", "Date;Counterparty;Details;Amount\n12.11.2026;SIA PARAUGS;PR-2026/118;-121,00\n"
                                   "13.11.2026;CUSTOMER TEST;payment;121,00\n")
    b = _csv(tmp_path / "oct_nov.csv", "Date;Counterparty;Details;Amount\n12.11.2026;SIA PARAUGS;PR-2026/118;-121,00\n")
    ra = inv.read_csv(a)
    assert len(ra) == 1 and ra[0]["cp"] == "SIA PARAUGS"         # incoming 121,00 is not a payment
    txns, used = inv.read_statements(str(tmp_path))
    assert len(txns) == 1 and len(used) == 2                       # same payment in two statements = one payment
    c = _csv(tmp_path / "two.csv", "Date;Counterparty;Details;Amount;Currency\n01.11.2026;SHOP;x;-5,00;USD\n"
                                   "01.11.2026;SHOP;x;-5,00;USD\n")
    rc = inv.read_csv(c)
    assert len(rc) == 2 and rc[0]["cur"] == "USD"                  # two equal payments in one file stay two


def _run(tmp, docs, extra=()):
    folder = tmp / "docs"
    for d in docs:
        if d.get("file"):
            p = folder / d["file"]
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_bytes(("TEST · FICTIONAL " + d["file"]).encode())
    (tmp / "extraction.json").write_text(json.dumps({"docs": docs}), encoding="utf-8")
    (tmp / "st").mkdir(exist_ok=True)
    if not (tmp / "floktron_base.xlsx").exists():
        shutil.copy(os.path.join(ROOT, "templates", "floktron_base_empty.xlsx"), tmp / "floktron_base.xlsx")
    return inv.main(["--config", str(tmp / "none.yaml"), "--folder", str(folder), "--extraction",
                     str(tmp / "extraction.json"), "--statements", str(tmp / "st"), "--base",
                     str(tmp / "floktron_base.xlsx"), "--today", "2026-11-22", "--test", *extra])


def test_same_document_in_two_files_is_one_document(tmp_path, capsys):
    docs = [_doc(file="P/scan.pdf"), _doc(file="P/photo.jpg", number="pr 2026 118")]
    assert _run(tmp_path, docs, ["--apply"]) == 0
    out = capsys.readouterr().out
    assert "New documents: 1" in out and "same supplier, type and number" in out
    docs2 = [_doc(file="P/again.pdf", number="PR2026-118", reg="LV 40000000001")]
    assert _run(tmp_path, docs2, ["--apply"]) == 0                   # next week, written differently: still a duplicate
    assert "already in the base" in capsys.readouterr().out


def test_unreadable_record_is_not_booked_and_does_not_crash(tmp_path, capsys):
    docs = [_doc(file="P/blur.pdf", total=None, note="total unreadable"), _doc(file="P/odd.pdf", type="receipt"),
            _doc(file="P/ok.pdf", number="OK-0001")]
    assert _run(tmp_path, docs, ["--apply"]) == 0
    out = capsys.readouterr().out
    assert "needs a look: 2" in out and "total" in out and "type 'receipt' unknown" in out
    assert "not read yet: 0" in out                                  # known files, just not booked
    ws = openpyxl.load_workbook(tmp_path / "floktron_base.xlsx")["Invoices"]
    assert [r[5] for r in ws.iter_rows(min_row=2, values_only=True)] == ["OK-0001"]


def test_ids_continue_after_the_highest(tmp_path, capsys):
    assert _run(tmp_path, [_doc(file="P/1.pdf", number="A-0001"), _doc(file="P/2.pdf", number="A-0002")], ["--apply"]) == 0
    wb = openpyxl.load_workbook(tmp_path / "floktron_base.xlsx")
    wb["Invoices"].delete_rows(2)                                     # someone deleted the first row
    wb.save(tmp_path / "floktron_base.xlsx")
    assert _run(tmp_path, [_doc(file="P/3.pdf", number="A-0003")], ["--apply"]) == 0
    ids = [r[0] for r in openpyxl.load_workbook(tmp_path / "floktron_base.xlsx")["Invoices"].iter_rows(min_row=2, values_only=True)]
    assert ids == ["TINV-0002", "TINV-0003"] and len(set(ids)) == len(ids)


def test_apply_waits_for_a_running_floktron(tmp_path, capsys):
    shutil.copy(os.path.join(ROOT, "templates", "floktron_base_empty.xlsx"), tmp_path / "floktron_base.xlsx")
    before = (tmp_path / "floktron_base.xlsx").read_bytes()
    ctx = multiprocessing.get_context("spawn")
    ready, release = ctx.Event(), ctx.Event()
    holder = ctx.Process(target=_hold, args=(str(tmp_path / ".floktron.lock"), ready, release))
    holder.start()
    assert ready.wait(20)
    try:
        assert _run(tmp_path, [_doc(file="P/1.pdf")], ["--apply"]) == 2
    finally:
        release.set()
        holder.join(20)
    assert "Another FLOKTRON run" in capsys.readouterr().out
    assert (tmp_path / "floktron_base.xlsx").read_bytes() == before

