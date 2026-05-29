import scan_private_methods as sp


def test_finds_private_methods():
    src = (
        "export class LocaleDao {\n"
        "  public searchLocali() { return 1 }\n"
        "  private mapLocale(row: Row) { return row.x ?? '' }\n"
        "  private async manipolaLocale(x) { if (x) return 1; return 2 }\n"
        "}\n"
    )
    methods = sp.scan(src)
    names = [m["name"] for m in methods]
    assert "mapLocale" in names
    assert "manipolaLocale" in names
    assert "searchLocali" not in names  # public escluso


def test_no_private_methods():
    assert sp.scan("export class A { public foo() {} }") == []
