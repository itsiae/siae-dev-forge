import json
from io import StringIO
from unittest.mock import patch

import scan_tz_usage as st


def test_detects_intl():
    src = "const f = new Intl.DateTimeFormat('it-IT', { timeZone: 'Europe/Rome' })"
    res = st.scan(src)
    assert res["uses_tz"] is True
    assert "Intl" in res["signals"]


def test_detects_helpers():
    src = "import { getItalyOffset } from '../libs/utils'\nconst o = getItalyOffset()"
    res = st.scan(src)
    assert res["uses_tz"] is True
    assert "getItalyOffset" in res["signals"]


def test_no_tz():
    res = st.scan("const x = 1 + 2")
    assert res["uses_tz"] is False
    assert res["signals"] == []


# m6 — 3 segnali mancanti: toLocaleString, process.env.TZ, addItalyOffset
def test_detects_to_locale_string():
    src = "const s = date.toLocaleString('it-IT')"
    res = st.scan(src)
    assert res["uses_tz"] is True
    assert "toLocale" in res["signals"]


def test_detects_to_locale_date_string():
    src = "return d.toLocaleDateString()"
    res = st.scan(src)
    assert res["uses_tz"] is True
    assert "toLocale" in res["signals"]


def test_detects_to_locale_time_string():
    src = "label = val.toLocaleTimeString('it-IT')"
    res = st.scan(src)
    assert res["uses_tz"] is True
    assert "toLocale" in res["signals"]


def test_detects_process_env_tz():
    src = "process.env.TZ = 'Europe/Rome'"
    res = st.scan(src)
    assert res["uses_tz"] is True
    assert "process.env.TZ" in res["signals"]


def test_detects_add_italy_offset():
    src = "const shifted = addItalyOffset(new Date())"
    res = st.scan(src)
    assert res["uses_tz"] is True
    assert "addItalyOffset" in res["signals"]


def test_multi_signal():
    src = (
        "process.env.TZ = 'Europe/Rome'\n"
        "const f = new Intl.DateTimeFormat('it-IT')\n"
        "const s = d.toLocaleString()\n"
        "const o = getItalyOffset()\n"
        "const r = addItalyOffset(new Date())\n"
    )
    res = st.scan(src)
    assert res["uses_tz"] is True
    assert "process.env.TZ" in res["signals"]
    assert "Intl" in res["signals"]
    assert "toLocale" in res["signals"]
    assert "getItalyOffset" in res["signals"]
    assert "addItalyOffset" in res["signals"]


# m5 — argv guard: se mancano argomenti → JSON errore su stderr + exit 1
def test_main_no_args_exits_with_error():
    with patch("sys.argv", ["scan_tz_usage.py"]):
        stderr_capture = StringIO()
        with patch("sys.stderr", stderr_capture):
            try:
                st.main()
                assert False, "Expected SystemExit"
            except SystemExit as e:
                assert e.code == 1
        err_output = json.loads(stderr_capture.getvalue())
        assert "error" in err_output
