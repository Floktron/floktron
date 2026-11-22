#!/usr/bin/env python3
"""Generates FICTIONAL supplier documents + a fictional bank statement for testing the
invoices -> accounting step of FLOKTRON.

Every company, registration number, IBAN and amount here is invented. Each PDF carries a
"TEST · FICTIONAL COMPANY" banner. Languages: LV, EN, DE, ES, LT, ET, RU, CZ (scanned image).
Traps on purpose: a forwarded duplicate, a delivery note (not an invoice), an unpaid invoice
with a same-amount payment to a different shop, a proforma without a final invoice.

Run:  python3 tests/fixtures/invoices/make_fixtures.py tests/fixtures/invoices      (needs: node + playwright (chromium), pillow, pdftoppm)
"""
import os, shutil, subprocess, sys, random
import json, tempfile
from PIL import Image, ImageFilter

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)))
BUYER = dict(name="FLOKTRON Demo SIA (fictional)", reg="40000000099", vat="LV40000000099",
             addr="Parauga iela 1, Rīga, LV-1001, Latvija", iban="LV80BANK0000435195001")

CSS = """@page{size:A4;margin:16mm}body{font:10.5pt/1.4 Inter,DejaVu Sans,sans-serif;color:#222}
.ban{border:2px dashed #c53030;color:#c53030;font-weight:700;text-align:center;padding:4px;margin-bottom:12px;letter-spacing:.5px}
h1{font-size:18pt;margin:0 0 4px}.row{display:flex;justify-content:space-between;gap:24px}.box{border:1px solid #bbb;padding:8px 10px;flex:1}
table{width:100%;border-collapse:collapse;margin-top:14px}th,td{border-bottom:1px solid #ccc;padding:5px;text-align:left}th{background:#f1f1f1}
td.r,th.r{text-align:right}.tot{margin-left:auto;width:55%;margin-top:10px}.tot td{border:0;padding:2px 5px}.tot tr:last-child td{font-weight:700;border-top:2px solid #333}
.small{font-size:8.5pt;color:#555;margin-top:18px}"""

def page(title, banner, seller, buyer_lbl, meta, head, rows, totals, foot):
    meta_html = "".join(f"<div>{k}: <b>{v}</b></div>" for k, v in meta)
    th = "".join(f'<th class="{"r" if i >= 2 else ""}">{h}</th>' for i, h in enumerate(head))
    tr = "".join("<tr>" + "".join(f'<td class="{"r" if i >= 2 else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    tt = "".join(f'<tr><td>{k}</td><td class="r">{v}</td></tr>' for k, v in totals)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="ban">{banner}</div><div class="row"><div><h1>{title}</h1>{meta_html}</div></div>
<div class="row" style="margin-top:12px"><div class="box">{seller}</div><div class="box"><b>{buyer_lbl}</b><br>{BUYER['name']}<br>{BUYER['addr']}<br>Reg. {BUYER['reg']} · VAT {BUYER['vat']}</div></div>
<table><tr>{th}</tr>{tr}</table><table class="tot">{tt}</table><div class="small">{foot}</div></body></html>"""

B = "TEST · FICTIONAL COMPANY · NOT A REAL DOCUMENT"
DOCS = {
 "Paraugs Reagenti/Rekins_PR-2026-118.pdf": page("Rēķins Nr. PR-2026/118", B + " · TESTS",
   "<b>SIA Paraugs Reaģenti (TESTS)</b><br>Reģ. Nr. 40000000001 · PVN LV40000000001<br>Testa iela 5, Rīga<br>Konts: LV11BANK0000000000001",
   "Maksātājs", [("Datums", "03.11.2026"), ("Apmaksas termiņš", "17.11.2026"), ("Apmaksas veids", "pārskaitījums")],
   ["Nosaukums", "Mv.", "Daudz.", "Cena", "Summa"], [["Reaģents A-1 (testa prece)", "kg", "10", "12.00", "120.00"]],
   [("Kopā bez PVN", "120.00"), ("PVN 21%", "25.20"), ("Summa apmaksai, EUR", "145.20")], "Rēķins sagatavots elektroniski un ir derīgs bez paraksta."),
 "Northwind Polymers/INV-50731.pdf": page("INVOICE INV-50731", B,
   "<b>Northwind Polymers Ltd (FICTIONAL)</b><br>Unit 0, Example Park, Cork, Ireland<br>VAT IE0000000TE<br>IBAN IE00BANK00000000000000",
   "Bill to", [("Invoice date", "14 Oct 2026"), ("Due date", "28 Oct 2026"), ("Terms", "Net 14, bank transfer")],
   ["Description", "Unit", "Qty", "Price", "Amount"], [["Test polymer P-7 (sample)", "kg", "20", "15.00", "300.00"]],
   [("Subtotal", "€300.00"), ("VAT 0% — reverse charge, Art. 196 Directive 2006/112/EC", "€0.00"), ("Total due", "€300.00")], "Please quote INV-50731 with your payment."),
 "Musterchemie/Rechnung_2026-0457.pdf": page("Rechnung Nr. 2026-0457", B + " · TESTFIRMA",
   "<b>Musterchemie GmbH (TESTFIRMA)</b><br>Beispielstraße 1, 10115 Berlin<br>USt-IdNr. DE000000000<br>IBAN DE00 0000 0000 0000 0000 00",
   "Rechnungsempfänger", [("Rechnungsdatum", "20.10.2026"), ("Zahlungsziel", "03.11.2026"), ("Zahlungsart", "Überweisung")],
   ["Bezeichnung", "Einheit", "Menge", "Einzelpreis", "Gesamt"], [["Testchemikalie M-3", "Stk", "4", "20,00 €", "80,00 €"]],
   [("Nettobetrag", "80,00 €"), ("zzgl. MwSt. 19 %", "15,20 €"), ("Rechnungsbetrag", "95,20 €")], "Bitte überweisen Sie den Betrag unter Angabe der Rechnungsnummer."),
 "Musterchemie/Lieferschein_LS-8812.pdf": page("Lieferschein LS-8812", B + " · TESTFIRMA",
   "<b>Musterchemie GmbH (TESTFIRMA)</b><br>Beispielstraße 1, 10115 Berlin", "Lieferadresse",
   [("Datum", "22.10.2026"), ("Zu Rechnung", "2026-0457")], ["Bezeichnung", "Einheit", "Menge", "", ""], [["Testchemikalie M-3", "Stk", "4", "", ""]],
   [("Packstücke", "1")], "Lieferschein — keine Rechnung. Preise siehe Rechnung."),
 "Quimicas Ficticias/Proforma_PF-2026-0089.pdf": page("FACTURA PROFORMA PF-2026-0089", B + " · PRUEBA",
   "<b>Químicas Ficticias S.L. (PRUEBA)</b><br>Calle Ejemplo 1, 28000 Madrid<br>CIF ESB00000000<br>IBAN ES00 0000 0000 0000 0000 0000",
   "Cliente", [("Fecha", "02/10/2026"), ("Forma de pago", "Transferencia bancaria (por adelantado)"), ("Pedido", "77120")],
   ["Producto", "Ud.", "Cant.", "Precio", "Total"], [["Producto de prueba Q-2", "kg", "5", "10,00 €", "50,00 €"]],
   [("Base imponible", "50,00 €"), ("IVA 21 %", "10,50 €"), ("Total", "60,50 €")], "Proforma: no es una factura. La factura definitiva se emite tras el envío."),
 "Bandomoji Prekyba/PVM_BP-00231.pdf": page("PVM SĄSKAITA FAKTŪRA Serija BP Nr. 00231", B + " · TESTAS",
   "<b>UAB Bandomoji Prekyba (TESTAS)</b><br>Pavyzdžio g. 1, Vilnius<br>Įm. kodas 300000000 · PVM LT000000000017",
   "Pirkėjas", [("Data", "2026-11-05"), ("Apmokėjimas", "apmokėta kortele")],
   ["Prekė", "Mato vnt.", "Kiekis", "Kaina", "Suma"], [["Bandomoji prekė L-4", "vnt", "1", "24,79", "24,79"]],
   [("Suma be PVM", "24,79 €"), ("PVM 21 %", "5,21 €"), ("Iš viso", "30,00 €")], "Apmokėta. Ačiū!"),
 "Naidis Keemia/Ettemaksuarve_7781.pdf": page("ETTEMAKSUARVE nr 7781", B + " · TEST",
   "<b>Näidis Keemia OÜ (TEST)</b><br>Näidise 1, Tallinn<br>Reg. 10000000 · KMKR EE000000000<br>IBAN EE00 0000 0000 0000 0000",
   "Maksja", [("Kuupäev", "10.11.2026"), ("Maksetähtaeg", "14.11.2026"), ("Viitenumber", "7781")],
   ["Toode", "Ühik", "Kogus", "Hind", "Summa"], [["Testtoode E-5", "kg", "2", "20,00", "40,00"]],
   [("Summa km-ta", "40,00 €"), ("Käibemaks 24%", "9,60 €"), ("Tasuda", "49,60 €")], "Ettemaksuarve. Palume märkida maksekorraldusele arve number."),
 "Demo Kimija/Schet_D-0042.pdf": page("СЧЁТ № Д-0042 от 15.11.2026", B + " · ТЕСТ, ВЫМЫШЛЕННАЯ КОМПАНИЯ",
   "<b>SIA Demo Ķīmija (ТЕСТ)</b><br>Рег. № 40000000002 · НДС LV40000000002<br>ул. Примерная 2, Рига<br>Счёт: LV22BANK0000000000002",
   "Плательщик", [("Дата", "15.11.2026"), ("Оплатить до", "01.12.2026"), ("Способ оплаты", "банковский перевод")],
   ["Наименование", "Ед.", "Кол-во", "Цена", "Сумма"], [["Тестовый реагент Д-9", "кг", "10", "20,00", "200,00"]],
   [("Итого без НДС", "200,00"), ("НДС 21%", "42,00"), ("Всего к оплате, EUR", "242,00")], "Счёт составлен электронно и действителен без подписи."),
 "Vzorova Chemie/scan_faktura.pdf": page("FAKTURA – DAŇOVÝ DOKLAD č. 2026110", B + " · TEST",
   "<b>Vzorová Chemie s.r.o. (TEST)</b><br>Ukázková 1, 110 00 Praha<br>IČ 00000000 · DIČ CZ00000000<br>IBAN CZ00 0000 0000 0000 0000 0000",
   "Odběratel", [("Datum vystavení", "08.10.2026"), ("Datum splatnosti", "22.10.2026"), ("Variabilní symbol", "2026110")],
   ["Označení", "MJ", "Množství", "Cena", "Celkem"], [["Zkušební látka V-6", "kg", "15", "10,00", "150,00"]],
   [("Základ", "150,00 EUR"), ("DPH 0 % — přenesení daňové povinnosti", "0,00 EUR"), ("Celkem k úhradě", "150,00 EUR")], "Při platbě uveďte variabilní symbol."),
}

TX = [  # date, counterparty line, code, amount, details   (fictional statement, bank PDF layout (Swedbank-style))
 ("05.10.2026", "QUIMICAS FICTICIAS SL ES0000000000000000000000", "IZP", "60.50", "PROFORMA PF-2026-0089"),
 ("21.10.2026", "VZOROVA CHEMIE SRO CZ0000000000000000000000", "IZP", "150.00", "VS 2026110"),
 ("25.10.2026", None, "CTX", "95.20", "RIMI HIPERMARKETS RIGA"),
 ("27.10.2026", "NORTHWIND POLYMERS LTD IE00BANK00000000000000", "IZP", "300.00", "INV-50731"),
 ("05.11.2026", None, "CTX", "30.00", "UAB BANDOMOJI PREKYBA VILNIUS"),
 ("11.11.2026", "NAIDIS KEEMIA OU EE000000000000000000", "IZP", "49.60", "Arve 7781"),
 ("12.11.2026", "SIA PARAUGS REAGENTI LV11BANK0000000000001", "PRV", "145.20", "Rēķins PR-2026/118"),
]

def statement_html():
    lines = ["Account statement", "01.10.2026 - 20.11.2026", "TEST · FICTIONAL BANK STATEMENT · NOT REAL",
             f"{BUYER['name']} Reg.No: {BUYER['reg']}", "IBAN: LV80 BANK 0000 4351 9500 1", "Trx.date", "Debit Credit", "EUR  01.10.2026 Opening balance 2000.00"]
    for i, (d, cp, code, amt, det) in enumerate(TX):
        arch = f"2026{d[3:5]}{d[:2]}{i:08d}"
        if code == "CTX":
            lines += [f"{d}     ", f"{arch} CTX PIRKUMS 535549******0000 {d} {amt} EUR ({100000+i}) {det.split()[0]}", " ".join(det.split()[1:]), amt]
        else:
            lines += [f"{d}  {cp}  ", f"{arch} {code}  BANKLV22  {amt}", det]
            lines += [f"{d}  Bank AS   ", f"{arch} KOM Komisija par maksājuma uzdevumu 0.21"]
    lines.append("20.11.2026 Closing balance 1168.45")
    body = "".join(f"<div>{l}</div>" for l in lines)
    return f'<!doctype html><html><head><meta charset="utf-8"><style>@page{{size:A4;margin:14mm}}body{{font:10pt/1.5 "DejaVu Sans Mono",monospace;white-space:pre}}</style></head><body>{body}</body></html>'

def main():
    for sub in ("docs", "statements_pdf"):
        shutil.rmtree(os.path.join(OUT, sub), ignore_errors=True)
    jobs = []
    tmpd = tempfile.mkdtemp()
    for i, (rel, html) in enumerate([("docs/" + k, v) for k, v in DOCS.items()] + [("statements_pdf/statement_2026-10_11.pdf", statement_html())]):
        path = os.path.join(OUT, rel); os.makedirs(os.path.dirname(path), exist_ok=True)
        h = os.path.join(tmpd, f"{i}.html"); open(h, "w", encoding="utf-8").write(html); jobs.append([h, path])
    js = ("const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage();"
          "for(const [h,o] of JSON.parse(process.argv[1])){await p.goto('file://'+h);await p.pdf({path:o,format:'A4',printBackground:true});}"
          "await b.close();})();")
    subprocess.run(["node", "-e", js, json.dumps(jobs)], check=True)
    shutil.rmtree(tmpd)
    # the CZ invoice becomes a "scan": raster, grey, slightly rotated, noisy, no text layer
    sc = os.path.join(OUT, "docs/Vzorova Chemie/scan_faktura.pdf"); tmp = sc[:-4]
    subprocess.run(["pdftoppm", "-r", "110", "-gray", "-png", "-singlefile", sc, tmp], check=True)
    im = Image.open(tmp + ".png").convert("L").rotate(1.3, expand=True, fillcolor=245).filter(ImageFilter.GaussianBlur(0.6))
    random.seed(7); px = im.load()
    for _ in range(int(im.size[0] * im.size[1] * 0.004)):
        px[random.randrange(im.size[0]), random.randrange(im.size[1])] = random.randint(120, 200)
    im.save(sc, "PDF", resolution=110); os.remove(tmp + ".png")
    # trap: the same LV invoice forwarded again under another name
    shutil.copy(os.path.join(OUT, "docs/Paraugs Reagenti/Rekins_PR-2026-118.pdf"), os.path.join(OUT, "docs/Paraugs Reagenti/FW_ Rekins PR-2026-118 (1).pdf"))
    for r, _, fs in os.walk(os.path.join(OUT, "docs")):
        for f in sorted(fs):
            print(os.path.relpath(os.path.join(r, f), OUT))

if __name__ == "__main__":
    main()
