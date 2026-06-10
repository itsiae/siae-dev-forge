"""Test integrazione Node.js fallback — siae-test-data."""
import subprocess
import sys
import os
import json
import time
import pytest

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts'))


def _node(*args, timeout=10):
    return subprocess.run(
        ['node', 'generate_profiles.js', *args],
        cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=timeout,
    )


@pytest.fixture(scope='session', autouse=True)
def require_node():
    r = subprocess.run(['node', '--version'], capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip('node non disponibile')


# ─── Task 01 — Scaffold ──────────────────────────────────────────────────────

class TestScaffold:
    def test_file_esiste_e_richiede_senza_errori(self):
        r = subprocess.run(
            ['node', '-e',
             "const m=require('./generate_profiles.js');"
             "console.log(typeof m.loadRef + ',' + typeof m.parseArgs)"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'function,function'

    def test_loadref_carica_nomi_italiani(self):
        r = subprocess.run(
            ['node', '-e',
             "const {loadRef}=require('./generate_profiles.js');"
             "const d=loadRef('nomi_italiani.json');"
             "console.log(Array.isArray(d.nomi_maschili))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'true'
