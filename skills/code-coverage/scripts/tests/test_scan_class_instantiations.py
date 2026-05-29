import json
import sys
from io import StringIO
from unittest.mock import patch

import scan_class_instantiations as sc


def test_finds_inline_new_with_import_path():
    src = (
        "import { SpazioDao } from '../dao/SpazioDao'\n"
        "export class LocaleDao {\n"
        "  async f() {\n"
        "    const s = new SpazioDao()\n"
        "    return s.retrieveAccertamentiApp() ?? s.findById(1)\n"
        "  }\n"
        "}\n"
    )
    res = sc.scan(src)
    assert res["SpazioDao"]["import_path"] == "../dao/SpazioDao"
    assert "retrieveAccertamentiApp" in res["SpazioDao"]["methods"]
    assert "findById" in res["SpazioDao"]["methods"]


def test_excludes_builtins():
    src = "const d = new Date(); const m = new Map(); const e = new Error('x')"
    assert sc.scan(src) == {}


# M2 — alias import: import { SpazioDao as SD } from '...' + new SD()
def test_alias_import_resolves_path():
    src = (
        "import { SpazioDao as SD } from '../dao/SpazioDao'\n"
        "const s = new SD()\n"
        "s.findAll()\n"
    )
    res = sc.scan(src)
    # L'alias SD deve essere presente nel risultato con import_path corretto
    assert "SD" in res, f"Expected 'SD' key in result, got: {list(res.keys())}"
    assert res["SD"]["import_path"] == "../dao/SpazioDao", (
        f"Expected import_path '../dao/SpazioDao', got '{res['SD']['import_path']}'"
    )
    assert "findAll" in res["SD"]["methods"]


# m3 — main() deve wrappare output in {"file": ..., "classes": ...}
def test_main_output_wrapped(tmp_path):
    src_file = tmp_path / "sample.ts"
    src_file.write_text(
        "import { FooDao } from '../dao/FooDao'\nconst f = new FooDao()\n",
        encoding="utf-8",
    )
    captured = StringIO()
    with patch("sys.argv", ["scan_class_instantiations.py", str(src_file)]):
        with patch("sys.stdout", captured):
            sc.main()
    output = json.loads(captured.getvalue())
    assert "file" in output, f"Missing 'file' key in output: {output}"
    assert "classes" in output, f"Missing 'classes' key in output: {output}"
    assert output["file"] == str(src_file)
    assert "FooDao" in output["classes"]


# m5 — argv guard: se mancano argomenti → JSON errore su stderr + exit 1
def test_main_no_args_exits_with_error():
    with patch("sys.argv", ["scan_class_instantiations.py"]):
        stderr_capture = StringIO()
        with patch("sys.stderr", stderr_capture):
            try:
                sc.main()
                assert False, "Expected SystemExit"
            except SystemExit as e:
                assert e.code == 1
        err_output = json.loads(stderr_capture.getvalue())
        assert "error" in err_output
