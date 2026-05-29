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
