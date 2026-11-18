# -*- coding: utf-8 -*-
"""FLOKTRON · safe_xlsx.py — keeps outside text from turning into Excel formulas.

Text from e-mail replies, news feeds, registries and web pages ends up in the .xlsx bases.
openpyxl stores any string that starts with "=" as a FORMULA, so a reply like
=HYPERLINK("http://bad.example","click") would become a live formula when the base is opened.
FLOKTRON bases have no formulas of their own, so before every save each formula cell is turned
back into plain text (a leading apostrophe is added). Imported by every script that writes a base.
"""
import openpyxl
from openpyxl.workbook.workbook import Workbook

_ORIGINAL_SAVE = Workbook.save


def defuse(wb):
    """Turn every formula cell into plain text. Returns how many cells were changed."""
    n = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if not isinstance(v, str) or not v.startswith("=") or v.strip() == "=":
                    continue  # a lone "=" is FLOKTRON's own marker ("same ray" in Routes), not a formula
                c.value = "'" + v
                c.data_type = "s"
                n += 1
    return n


def _safe_save(self, filename):
    defuse(self)
    return _ORIGINAL_SAVE(self, filename)


if getattr(Workbook.save, "__name__", "") != "_safe_save":
    Workbook.save = _safe_save
