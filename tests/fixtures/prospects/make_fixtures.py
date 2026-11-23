# -*- coding: utf-8 -*-
"""TEST · FICTIONAL - procurement results and register rows for tests/test_prospects.py.
All companies, buyers and reg. numbers (40000000xxx) are invented; the column names are the real EIS / UR ones."""
import csv
import os
import sys


def main(out):
    os.makedirs(out, exist_ok=True)
    # -*- coding: utf-8 -*-
    COLS = ("Iepirkuma_ID,Iepirkuma_nosaukums,Iepirkuma_identifikacijas_numurs,Pasutitaja_nosaukums,Pasutitaja_registracijas_numurs,"
            "Pasutitaja_registracijas_numura_veids,Pasutitaja_PVS_ID,Augstak_stavosa_organizacija,Iepirkuma_statuss,Regulejosais_tiesibu_akts,"
            "Proceduras_veids,Hipersaite_EIS_kura_pieejams_zinojums,Hipersaite_uz_IUB_publikaciju,Ir_dalijums_dalas,Iepirkuma_dalas_nr,"
            "Iepirkuma_dalas_nosaukums,Iepirkuma_dalas_statuss,Uzvaretaja_nosaukums,Uzvaretaja_registracijas_numurs,"
            "Uzvaretaja_registracijas_numura_veids,Uzvaretaja_valsts,Liguma_dok_veids,Noslegta_liguma_dok_ID,Saistita_liguma_ID,"
            "Aktuala_liguma_summa,Aktuala_liguma_summas_valuta,Sakotneja_liguma_summa,Sakotneja_liguma_summas_valuta,Liguma_izpildes_termins,"
            "Liguma_izpilde_no,Liguma_izpilde_lidz,Ligums_ir_vispariga_vienosanas,Liguma_dok_noslegsanas_datums,"
            "Liguma_dok_publicesanas_datums,Izbeigsanas_datums,Izbeigsanas_iemesls").split(",")
    def row(i, name, win, reg, eur, signed, till="2027-03-31", country="LVA", part="", ended="", buyer="Paraugu novada pašvaldība (TEST)"):
        d = dict.fromkeys(COLS, "")
        d.update(Iepirkuma_ID=str(i), Iepirkuma_nosaukums=name, Pasutitaja_nosaukums=buyer, Iepirkuma_statuss="Līgums noslēgts",
                 Hipersaite_EIS_kura_pieejams_zinojums=f"https://www.eis.gov.lv/EKEIS/Supplier/Procurement/{i}",
                 Iepirkuma_dalas_nosaukums=part, Uzvaretaja_nosaukums=win, Uzvaretaja_registracijas_numurs=reg,
                 Uzvaretaja_valsts=country, Aktuala_liguma_summa=str(eur), Aktuala_liguma_summas_valuta="EUR",
                 Liguma_izpilde_lidz=till, Liguma_dok_noslegsanas_datums=signed, Izbeigsanas_datums=ended)
        return [d[c] for c in COLS]
    R = [
     row(1, "Skolas sanmezglu remontdarbi (TEST)", "SIA \"Flīzētājs Demo\" (TEST)", "40000000001", 84500, "2026-11-10"),
     row(2, "Bērnudārza ēkas pārbūve (TEST)", "SIA \"Paraugbūve\" (TEST)", "40000000002", 640000, "2026-09-02"),
     row(3, "Būvprojekta izstrāde un autoruzraudzība (TEST)", "SIA \"Projekts Demo\" (TEST)", "40000000003", 45000, "2026-11-01"),
     row(4, "Ielas pārbūve (TEST)", "SIA \"Lielbūve Demo\" (TEST)", "40000000004", 9800000, "2026-10-15"),
     row(5, "Ielas seguma atjaunošana (TEST)", "SIA \"Lielbūve Demo\" (TEST)", "40000000004", 4200000, "2026-08-01"),
     row(6, "Kāpņu telpu kosmētiskais remonts (TEST)", "UAB \"Demo statyba\" (TEST)", "300000001", 30000, "2026-11-05", country="LTU"),
     row(7, "Biroja papīra piegāde (TEST)", "SIA \"Papīrs Demo\" (TEST)", "40000000005", 15000, "2026-11-12"),
     row(8, "Fasādes siltināšana (TEST)", "SIA \"Stopa Demo\" (TEST)", "40000000006", 120000, "2026-10-20"),
     row(9, "Sporta zāles grīdas atjaunošana (TEST)", "SIA \"Likvidēta Demo\" (TEST)", "40000000007", 55000, "2026-11-02"),
     row(10, "Dzīvojamās ēkas remonts (TEST)", "SIA \"Vecs līgums Demo\" (TEST)", "40000000008", 70000, "2026-01-15"),
     row(11, "Mazs remonts (TEST)", "SIA \"Sīkums Demo\" (TEST)", "40000000009", 4000, "2026-11-11"),
     row(12, "Ēkas jumta remonts (TEST)", "SIA \"Lauzts Demo\" (TEST)", "40000000010", 90000, "2026-10-01", ended="2026-11-01"),
     row(13, "Telpu remontdarbi (TEST)", "SIA \"Jau grāmatā Demo\" (TEST)", "40000000011", 50000, "2026-11-03"),
     row(14, "Ēkas fasādes remonts (TEST)", "SIA \"Labākais Demo\" (TEST)", "40000000099", 60000, "2026-11-04"),
     row(15, "Hostelis =HYPERLINK(\"http://x\") iekštelpu apdare (TEST)", "SIA \"Formula Demo\" (TEST)", "40000000012", 22000, "02.11.2026"),
    ]
    with open(os.path.join(out, "eis_2026.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL); w.writerow(COLS); w.writerows(R)
    UR = ["regcode", "sepa", "name", "name_before_quotes", "name_in_quotes", "name_after_quotes", "without_quotes", "regtype",
          "regtype_text", "type", "type_text", "registered", "terminated", "closed", "address", "index", "addressid", "region", "city", "atvk"]
    def ur(reg, reg_d, city, term=""):
        d = dict.fromkeys(UR, ""); d.update(regcode=reg, type="SIA", type_text="Sabiedrība ar ierobežotu atbildību",
                                           registered=reg_d, terminated=term, city=city, address=f"Testa iela 1, {city}"); return [d[c] for c in UR]
    with open(os.path.join(out, "register.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(UR)
        w.writerows([ur("40000000001", "2021-03-01", "Rīga"), ur("40000000002", "2009-05-05", "Valmiera"),
                     ur("40000000004", "1995-01-01", "Rīga"), ur("40000000006", "2022-06-01", "Mārupe"),
                     ur("40000000007", "2019-01-01", "Rīga", term="2026-10-01"), ur("40000000012", "2024-01-01", "Rīga"),
                     ur("40000000099", "2023-01-01", "Rīga"), ur("40000000098", "2020-01-01", "Rīga")])
    return os.path.join(out, "eis_2026.csv"), os.path.join(out, "register.csv")


if __name__ == "__main__":
    print(main(sys.argv[1] if len(sys.argv) > 1 else "prospects_fixtures"))
