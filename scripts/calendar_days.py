# -*- coding: utf-8 -*-
"""FLOKTRON · calendar_days.py — working days with public holidays (LV, LT, EE built in) + your own days off.

config.yaml:
    company:
      country: "LV"                 # LV | LT | EE | other (only weekends)
      holidays: ["2026-12-30"]      # extra days off of the company
Moved holidays (a holiday that falls on a weekend is moved to Monday in some countries) are not
calculated — add such days to company.holidays.
"""
import datetime

FIXED = {
    "LV": ["01-01", "05-01", "05-04", "06-23", "06-24", "11-18", "12-24", "12-25", "12-26", "12-31"],
    "LT": ["01-01", "02-16", "03-11", "05-01", "06-24", "07-06", "08-15", "11-01", "11-02",
           "12-24", "12-25", "12-26"],
    "EE": ["01-01", "02-24", "05-01", "06-23", "06-24", "08-20", "12-24", "12-25", "12-26"],
}
EASTER_BASED = {  # days relative to Easter Sunday
    "LV": [-2, 0, 1],
    "LT": [0, 1],
    "EE": [-2, 0, 49],
}


def easter(year):
    """Gregorian Easter Sunday (anonymous algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(year, month, day)


def holidays(year, country="", extra=()):
    country = (country or "").upper()
    out = {datetime.date.fromisoformat(f"{year}-{md}") for md in FIXED.get(country, [])}
    e = easter(year)
    out |= {e + datetime.timedelta(days=n) for n in EASTER_BASED.get(country, [])}
    for x in extra or ():
        try:
            d = datetime.date.fromisoformat(str(x)[:10])
            if d.year == year:
                out.add(d)
        except ValueError:
            pass
    return out


def is_working(day, cfg=None):
    comp = (cfg or {}).get("company") or {}
    if day.weekday() >= 5:
        return False
    return day not in holidays(day.year, comp.get("country", ""), comp.get("holidays") or ())


def next_working(start, n=1, cfg=None):
    d = start
    while n > 0:
        d += datetime.timedelta(days=1)
        if is_working(d, cfg):
            n -= 1
    return d
