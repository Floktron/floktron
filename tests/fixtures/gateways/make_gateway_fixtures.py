# -*- coding: utf-8 -*-
"""Builds the FICTIONAL data for tests/test_gateways.py at test time (no .eml or statement files are committed):
<folder>/mail/INBOX/*.eml, <folder>/mail/Spam/*.eml, <folder>/statements_csv/statement.csv and, when reportlab is
installed, <folder>/statements_pdf/statement.pdf (Swedbank-like layout, card payments in EUR and USD).
Every seller, amount, number, IBAN and link is invented (TEST · FICTIONAL; domains *.example). Run by hand:
python3 make_gateway_fixtures.py <folder>"""
import datetime as dt
import io
import os
import sys
from email.message import EmailMessage
from email.utils import format_datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Riga")
TO = "office@demo-sia.example.com"
T = "TEST · FICTIONAL"
IBAN = "LV00TEST0000000000077"


def tiny_pdf(text):
    """A one-page PDF without any library (enough for a receipt attachment)."""
    lines = text.replace("(", "[").replace(")", "]").split("\n")
    stream = "BT /F1 11 Tf 60 780 Td " + " ".join(f"({ln}) Tj 0 -16 Td" for ln in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for n, o in enumerate(objs, 1):
        offs.append(out.tell())
        out.write(f"{n} 0 obj\n{o}\nendobj\n".encode("latin-1", "replace"))
    x = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + "".join(f"{o:010d} 00000 n \n" for o in offs).encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode())
    return out.getvalue()


def mail(out, name, box, frm, subject, day, body, html=None, pdf=None, extra=None):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = frm, TO, subject
    m["Date"] = format_datetime(dt.datetime(2026, *day, tzinfo=TZ))
    m["Message-ID"] = f"<{name}@fixtures.test>"
    for k, v in (extra or {}).items():
        m[k] = v
    m.set_content(body)
    if html:
        m.add_alternative(html, subtype="html")
    if pdf:
        m.add_attachment(tiny_pdf(pdf[1]), maintype="application", subtype="pdf", filename=pdf[0])
    d = os.path.join(out, "mail", box)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name + ".eml"), "wb") as f:
        f.write(bytes(m))


def build_mail(out):
    # A. Stripe with a PDF called "Receipt-…" (an invoice-word filter misses it); A2 the same receipt again in Spam
    for name, box, h in (("A_stripe_pdf", "INBOX", 14), ("A2_stripe_pdf_copy", "Spam", 15)):
        mail(out, name, box, '"TEST Cloudnote Ltd" <receipts+acct_1TEST@stripe.com>', "Your receipt from TEST Cloudnote Ltd #2231-0042",
             (11, 3, 9, h), f"{T}\nReceipt from TEST Cloudnote Ltd\nReceipt number 2231-0042\nDate paid November 3, 2026\n"
             "Amount paid €24.20\nManage your subscription: https://billing.stripe.com/p/login/test_0042\n",
             pdf=("Receipt-2231-0042.pdf", f"{T}\nTEST Cloudnote Ltd Receipt 2231-0042\nAmount paid EUR 24.20"))
    # B. Stripe without a PDF, USD, in Spam; the seller writes from its own domain, the portal link is Stripe's
    mail(out, "B_stripe_usd_spam", "Spam", '"TEST Pixelforge AI" <invoice+statements@mail.pixelforge-test.example>',
         "Your TEST Pixelforge AI receipt [#1907-3316]", (11, 9, 18, 2),
         f"{T}\nTEST Pixelforge AI\nReceipt #1907-3316\nPixelforge Pro (monthly) $20.00\nTotal paid $20.00\n"
         "Questions? Visit https://support.pixelforge-test.example\nView invoice and receipt: https://invoice.stripe.com/i/acct_TEST/test_1907\n")
    mail(out, "C_paddle", "INBOX", '"Paddle.com" <help@paddle.com>', "Your receipt for TEST Formwise", (11, 12, 7, 40),
         f"{T}\nThanks for your purchase. Seller: TEST Formwise (FICTIONAL)\nOrder ID 7712-TEST-55\nTotal €15.00\n"
         "View receipt: https://my.paddle.com/receipt/7712-test/abc\nManage subscription: https://paddle.net/test-manage\n")
    mail(out, "D_lemon", "INBOX", '"TEST Iconkit" <hello@lemonsqueezy.com>', "Your receipt from TEST Iconkit", (11, 14, 11, 5),
         f"{T}\nOrder #ICK-20431\nTEST Iconkit — Lifetime icons\nTotal $9.00\nView receipt https://app.lemonsqueezy.com/my-orders/test-20431\n")
    mail(out, "E_apple", "INBOX", '"Apple" <no_reply@email.apple.com>', "Your receipt from Apple.", (11, 16, 20, 30),
         f"{T}\nOrder ID: MTEST7Q2KX\nTEST Notely Pro (FICTIONAL) Monthly 4,99 €\nTotal 4,99 €\nReport a problem: https://reportaproblem.apple.com/?s=test\n",
         html=f"<html><body><p>{T}</p><table><tr><td>Order ID:</td><td>MTEST7Q2KX</td></tr><tr><td>TEST Notely Pro (FICTIONAL) Monthly</td>"
              '<td>4,99 €</td></tr><tr><td><b>TOTAL</b></td><td><b>4,99 €</b></td></tr></table><a href="https://reportaproblem.apple.com/?s=test">Report</a></body></html>')
    mail(out, "F_google", "INBOX", '"Google Play" <googleplay-noreply@google.com>', "Your Google Play Order Receipt from Nov 17, 2026",
         (11, 17, 12, 0), f"{T}\nOrder number: GPA.3300-TEST-0001\nItem: TEST Scanly (FICTIONAL) Premium\nTotal: €2.99\n"
         "View in payments: https://pay.google.com/gp/w/home/activity\n")
    mail(out, "G_stripe_news", "INBOX", '"Stripe" <news@stripe.com>', "What's new in Stripe Billing — November", (11, 18, 10, 0),
         f"{T}\nNew features for subscriptions. Read more: https://stripe.com/blog/test\n", extra={"List-Unsubscribe": "<https://stripe.com/unsub>"})
    mail(out, "H_fake_stripe", "INBOX", '"Stripe Billing" <billing@stripe-receipts-test.example>', "Stripe receipt: payment failed, update card",
         (11, 19, 8, 0), f"{T}\nYour Stripe payment of €49.00 failed. Update your card now: https://stripe-receipts-test.example/login\n",
         extra={"Authentication-Results": "mx.test; dmarc=fail header.from=stripe-receipts-test.example"})
    mail(out, "I_supplier_invoice", "INBOX", '"SIA TEST Paraugs Būve" <rekini@paraugs-buve-test.example>', "Rēķins Nr. PB-2026-077",
         (11, 20, 9, 0), f"{T}\nPielikumā rēķins. Summa apmaksai EUR 121.00\n", pdf=("Rekins_PB-2026-077.pdf", f"{T}\nRekins PB-2026-077 121.00 EUR"))


CARDS = [  # posted, bought, amount, currency, (rate, fee), payee line 1, line 2, charged EUR
    ("26.09.2026", "25.09.2026", "12.00", "EUR", None, "VECTORLY.IO* TEST", "TALLINN", "12.00"),
    ("05.11.2026", "03.11.2026", "24.20", "EUR", None, "CLOUDNOTE* TEST", "DUBLIN", "24.20"),
    ("10.11.2026", "10.11.2026", "30.00", "EUR", None, "TEST VEIKALS", "RIGA", "30.00"),
    ("11.11.2026", "09.11.2026", "20.00", "USD", ("1.085000", "0.46"), "PIXELFORGE TEST", "SAN FRANCISCO", "18.89"),
    ("13.11.2026", "12.11.2026", "15.00", "EUR", None, "PADDLE.NET* FORMWISE", "LONDON", "15.00"),
    ("16.11.2026", "14.11.2026", "9.00", "USD", ("1.090000", "0.21"), "LEMSQZY* ICONKIT", "NEW YORK", "8.47"),
    ("18.11.2026", "16.11.2026", "4.99", "EUR", None, "APPLE.COM/", "BILL CORK", "4.99"),
    ("19.11.2026", "17.11.2026", "2.99", "EUR", None, "GOOGLE*TEST SCANLY", "DUBLIN", "2.99"),
    ("19.11.2026", "17.11.2026", "6.48", "USD", ("1.160000", "0.16"), "NAME-CHEAPTEST.COM*", "XTEST1 85034 PHOENIX", "5.75"),
]


def build_csv(out):
    """CSV export: amounts in EUR only, so only the EUR card payments are in it (as most bank CSV exports)."""
    d = os.path.join(out, "statements_csv")
    os.makedirs(d, exist_ok=True)
    rows = ["Date;Counterparty;Amount;Details;D/K"]
    for _, buy, amt, cur, _, l1, l2, _ in CARDS:
        if cur == "EUR":
            rows.append(f"{buy};{l1} {l2};-{amt};card payment {T};D")
    rows.append(f"12.11.2026;SIA TEST Paraugs Būve;121.00;Rēķins PB-2026-077 {T};D")  # a transfer, not a card payment
    with open(os.path.join(d, "statement.csv"), "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")


def build_pdf(out):
    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        return False
    lines = ["Account statement", "01.09.2026 - 20.11.2026", f"{T} BANK STATEMENT · NOT REAL", "Demo SIA (TEST · FICTIONAL)",
             f"IBAN: {IBAN[:4]} {IBAN[4:8]} {IBAN[8:12]} {IBAN[12:16]} {IBAN[16:20]} {IBAN[20:]}", "Debit Credit", "EUR 01.09.2026 Opening balance 900.00"]
    for n, (post, buy, amt, cur, fx, l1, l2, eur) in enumerate(CARDS):
        arch = f"2026{post[3:5]}{post[:2]}{n:08d}"
        lines.append(post)
        if fx:
            lines += [f"{arch} CTX PIRKUMS 535549******0000 {buy} {amt} {cur} VALUTAS KURSS", f"{fx[0]}, KONVERTACIJAS MAKSA {fx[1]} EUR ({300000 + n}) {l1}"]
        else:
            lines += [f"{arch} CTX PIRKUMS 535549******0000 {buy} {amt} {cur} ({300000 + n}) {l1}"]
        lines += [l2, eur]
    lines.append("20.11.2026 Closing balance 777.52")
    d = os.path.join(out, "statements_pdf")
    os.makedirs(d, exist_ok=True)
    c = canvas.Canvas(os.path.join(d, "statement.pdf"))
    c.setFont("Helvetica", 9)
    y = 800
    for ln in lines:
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 9)
            y = 800
        c.drawString(40, y, ln)
        y -= 13
    c.save()
    return True


def main(out):
    build_mail(out)
    build_csv(out)
    build_pdf(out)
    return out


if __name__ == "__main__":
    print("fixtures →", main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "_built")))
