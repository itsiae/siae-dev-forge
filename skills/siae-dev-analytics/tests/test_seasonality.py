"""Test seasonality.py — festività IT + working days."""
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
    # 25 aprile 2026 (Liberazione) - sabato
    # Use 1 Jan instead which is always a holiday and a Thursday in 2026
    assert s.working_days_in_window("2026-01-01", "2026-01-01") == 0


def test_seasonality_adj_august_heavy_holidays():
    # 01-31 ago: Ferragosto + weekends
    adj = s.seasonality_adj("2026-08-01", "2026-08-31")
    assert 0.5 <= adj <= 0.75  # ~20 working days / 31 total


def test_seasonality_adj_invalid_window_returns_zero():
    # end < start
    assert s.working_days_in_window("2026-03-31", "2026-03-01") == 0
