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
