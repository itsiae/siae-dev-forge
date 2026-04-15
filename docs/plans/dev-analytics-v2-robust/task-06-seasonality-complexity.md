# Task 06 — F3 Seasonality + Complexity

**Goal:** Festività IT + complexity-adjusted KPI + stale branch cleanup scan.
**AC coperti:** NF28-NF30 seasonality, complexity weight
**Dipendenze:** Task 01, 04
**Effort:** ~50 min
**Test nuovi:** 8

## File coinvolti

- `scripts/seasonality.py` — festività IT + working days
- `scripts/compute_kpis.py` — adjust throughput con seasonality
- `tests/test_seasonality.py` — 8 test

## Step 1 — seasonality.py

```python
"""Festività IT + working days calculation."""
from __future__ import annotations
from datetime import date, timedelta


def easter_date(year: int) -> date:
    """Gauss algorithm Easter Sunday."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def italian_holidays(year: int) -> set[date]:
    """Italian national holidays for year."""
    easter = easter_date(year)
    return {
        date(year, 1, 1),   # Capodanno
        date(year, 1, 6),   # Epifania
        easter,             # Pasqua
        easter + timedelta(days=1),  # Pasquetta
        date(year, 4, 25),  # Liberazione
        date(year, 5, 1),   # Lavoro
        date(year, 6, 2),   # Repubblica
        date(year, 8, 15),  # Ferragosto
        date(year, 11, 1),  # Ognissanti
        date(year, 12, 8),  # Immacolata
        date(year, 12, 25), # Natale
        date(year, 12, 26), # Santo Stefano
    }


def working_days_in_window(since: str, until: str) -> int:
    """Count working days (no weekends, no IT holidays) in window."""
    from datetime import datetime
    start = datetime.fromisoformat(since).date()
    end = datetime.fromisoformat(until).date()
    if end < start:
        return 0
    days = set()
    year_holidays: dict[int, set[date]] = {}
    current = start
    while current <= end:
        year = current.year
        if year not in year_holidays:
            year_holidays[year] = italian_holidays(year)
        if current.weekday() < 5 and current not in year_holidays[year]:
            days.add(current)
        current += timedelta(days=1)
    return len(days)


def seasonality_adj(since: str, until: str) -> float:
    """Correction factor: working_days / total_days. ≤1.0."""
    from datetime import datetime
    start = datetime.fromisoformat(since).date()
    end = datetime.fromisoformat(until).date()
    total_days = max((end - start).days + 1, 1)
    return working_days_in_window(since, until) / total_days
```

## Step 2 — Test (8)

```python
from datetime import date
import seasonality as s


def test_easter_2026():
    assert s.easter_date(2026) == date(2026, 4, 5)  # Pasqua 2026

def test_italian_holidays_2026_count():
    h = s.italian_holidays(2026)
    assert len(h) == 12

def test_christmas_in_holidays():
    h = s.italian_holidays(2026)
    assert date(2026, 12, 25) in h

def test_working_days_normal_week():
    # 5 giorni feriali lun-ven
    assert s.working_days_in_window("2026-03-02", "2026-03-06") == 5

def test_working_days_excludes_weekend():
    # sab-dom
    assert s.working_days_in_window("2026-03-07", "2026-03-08") == 0

def test_working_days_excludes_holiday():
    # 25 aprile venerdì 2026 (Liberazione)
    assert s.working_days_in_window("2026-04-25", "2026-04-25") == 0

def test_seasonality_adj_august_heavy_holidays():
    # 01-31 ago: Ferragosto + weekends
    adj = s.seasonality_adj("2026-08-01", "2026-08-31")
    assert 0.5 <= adj <= 0.75  # ~20 working days / 31 total

def test_seasonality_adj_invalid_window_returns_zero():
    # end < start
    assert s.working_days_in_window("2026-03-31", "2026-03-01") == 0
```

## Verify

```bash
PYTHONPATH=skills/siae-dev-analytics/scripts python3 -m pytest skills/siae-dev-analytics/tests/test_seasonality.py -v
```

Output: `8 passed`.

## Criteri accettazione

- [ ] Easter algorithm corretto 2026
- [ ] 12 festività IT enumerated
- [ ] working_days esclude weekends + holidays
- [ ] seasonality_adj usato in ROI v2 (task-10)
