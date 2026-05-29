import json
from io import StringIO
from unittest.mock import patch

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


# m1 — modificatori opzionali multipli: static, override, abstract, readonly
def test_private_static_method():
    src = (
        "export class MyService {\n"
        "  private static compute(x: number): number { return x * 2 }\n"
        "}\n"
    )
    methods = sp.scan(src)
    names = [m["name"] for m in methods]
    assert "compute" in names, f"Expected 'compute' in {names}"


def test_private_override_method():
    src = (
        "export class MyService {\n"
        "  private override render(): void {}\n"
        "}\n"
    )
    methods = sp.scan(src)
    names = [m["name"] for m in methods]
    assert "render" in names, f"Expected 'render' in {names}"


def test_private_abstract_method():
    src = (
        "abstract class Base {\n"
        "  private abstract process(): void\n"
        "}\n"
    )
    methods = sp.scan(src)
    names = [m["name"] for m in methods]
    assert "process" in names, f"Expected 'process' in {names}"


def test_private_static_async_method():
    src = (
        "export class Worker {\n"
        "  private static async fetchData(url: string): Promise<void> {}\n"
        "}\n"
    )
    methods = sp.scan(src)
    names = [m["name"] for m in methods]
    assert "fetchData" in names, f"Expected 'fetchData' in {names}"
    is_async = next(m["is_async"] for m in methods if m["name"] == "fetchData")
    assert is_async is True


# m5 — argv guard: se mancano argomenti → JSON errore su stderr + exit 1
def test_main_no_args_exits_with_error():
    with patch("sys.argv", ["scan_private_methods.py"]):
        stderr_capture = StringIO()
        with patch("sys.stderr", stderr_capture):
            try:
                sp.main()
                assert False, "Expected SystemExit"
            except SystemExit as e:
                assert e.code == 1
        err_output = json.loads(stderr_capture.getvalue())
        assert "error" in err_output
