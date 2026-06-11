"""Test integrazione Node.js fallback — siae-test-data."""
import subprocess
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


# ─── Task 02 — cfUtils CF persona fisica ────────────────────────────────────

class TestCfPersonaFisica:
    def test_cf_mario_rossi_diretto(self):
        r = subprocess.run(
            ['node', '-e',
             "const {calcolaCF}=require('./generate_profiles.js');"
             "console.log(calcolaCF('Mario','Rossi','1985-01-01','M','H501'))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'RSSMRA85A01H501Z'

    def test_cf_checksum_cognome_bianchi(self):
        r = subprocess.run(
            ['node', '-e',
             "const {calcolaCF}=require('./generate_profiles.js');"
             "console.log(calcolaCF('Alessandra','Bianchi','1990-06-15','F','F205'))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        cf = r.stdout.strip()
        assert len(cf) == 16
        assert cf[:3] == 'BNC'  # cognome Bianchi → BNC


# ─── Task 03 — pivaUtils + CF enti ──────────────────────────────────────────

class TestPivaCfEnti:
    def test_piva_checksum_nota(self):
        r = subprocess.run(
            ['node', '-e',
             "const {validaPiva}=require('./generate_profiles.js');"
             "console.log(validaPiva('00400770939'))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'true'

    def test_genera_piva_11_cifre_valida(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaPiva,validaPiva}=require('./generate_profiles.js');"
             "const p=generaPiva('RM',1234567);"
             "console.log(p.length + ',' + validaPiva(p))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == '11,true'

    def test_cf_ente11_formato_numerico(self):
        r = subprocess.run(
            ['node', '-e',
             r"const {calcolaCFEnte11}=require('./generate_profiles.js');"
             r"const cf=calcolaCFEnte11(1234567,'RM');"
             r"console.log(cf.length + ',' + /^\d{11}$/.test(cf))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == '11,true'


# ─── Task 04 — addressUtils + _pickNomeCognome ──────────────────────────────

class TestAddressNames:
    def test_indirizzo_it_coerente(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaIndirizzoIT,makePRNG}=require('./generate_profiles.js');"
             "const rng=makePRNG('t1');"
             "const a=generaIndirizzoIT('Roma',rng);"
             "console.log(a.stato + ',' + (a.cap.length===5) + ',' + !!a.via)"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'Italia,true,true'

    def test_pick_nome_cognome_italia(self):
        r = subprocess.run(
            ['node', '-e',
             "const {_pickNomeCognome,makePRNG}=require('./generate_profiles.js');"
             "const rng=makePRNG('t2');"
             "const [n,c]=_pickNomeCognome('Italia','M',rng);"
             "console.log(typeof n + ',' + typeof c)"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'string,string'


# ─── Task 05 — profileGen PRIVATO ────────────────────────────────────────────

class TestProfilePrivato:
    def test_privato_it_cf_valido(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaProfiloPrivato,makePRNG,validaCF}=require('./generate_profiles.js');"
             "const rng=makePRNG('P-IT-001');"
             "const p=generaProfiloPrivato('P-IT-001','IT','FULL',rng);"
             "const cf=p.anagrafica.codice_fiscale;"
             "console.log(cf.length + ',' + validaCF(cf))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == '16,true'

    def test_privato_light_no_indirizzo_no_contatti(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaProfiloPrivato,makePRNG}=require('./generate_profiles.js');"
             "const rng=makePRNG('P-IT-002');"
             "const p=generaProfiloPrivato('P-IT-002','IT','LIGHT',rng);"
             "console.log(!p.indirizzo + ',' + !p.contatti)"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'true,true'


# ─── Task 06 — profileGen BUSINESS ───────────────────────────────────────────

class TestProfileBusiness:
    def test_sdc_cf_uguale_piva(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaProfiloBusiness,makePRNG}=require('./generate_profiles.js');"
             "const rng=makePRNG('B-SDC-IT-001');"
             "const p=generaProfiloBusiness('B-SDC-IT-001','IT','SDC','LIGHT',rng);"
             "const sg=p.soggetto_giuridico;"
             "console.log(sg.codice_fiscale_ente === sg.partita_iva)"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'true'

    def test_sdc_rapp_legale_cf_presente(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaProfiloBusiness,makePRNG}=require('./generate_profiles.js');"
             "const rng=makePRNG('B-SDC-IT-002');"
             "const p=generaProfiloBusiness('B-SDC-IT-002','IT','SDC','LIGHT',rng);"
             "const rl=p.soggetto_giuridico.rappresentante_legale;"
             "console.log(rl.cf.length + ',' + !!rl.data_nascita)"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == '16,true'

    def test_sdc_extra_ue_rapp_legale_belfiore_z(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaProfiloBusiness,makePRNG}=require('./generate_profiles.js');"
             "const rng=makePRNG('B-SDC-EXTUE-001');"
             "const p=generaProfiloBusiness('B-SDC-EXTUE-001','EXTRA-UE','SDC','LIGHT',rng);"
             "const cf=p.soggetto_giuridico.rappresentante_legale.cf;"
             "console.log(cf.substring(11,15).startsWith('Z'))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'true'


# ─── Task 07 — formatOutput + main ───────────────────────────────────────────

class TestFormatMain:
    def test_10_privati_json(self):
        r = _node('--categorie', 'PRIVATO', '--nazionalita', 'ITA',
                  '--quantita', '10', '--formato', 'JSON', '--skip-validation')
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert len(data) == 10
        for p in data:
            assert len(p['anagrafica']['codice_fiscale']) == 16

    def test_distribuzione_ita_ue_70_30(self):
        r = _node('--categorie', 'PRIVATO', '--nazionalita', 'ITA,UE',
                  '--distribuzione', '70,30', '--quantita', '10',
                  '--formato', 'JSON', '--skip-validation')
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert len(data) == 10
        it_count = sum(1 for p in data if p['anagrafica']['stato_nascita'] == 'Italia')
        ue_count = sum(1 for p in data if p['anagrafica']['stato_nascita'] != 'Italia')
        assert it_count == 7
        assert ue_count == 3

    def test_bench_50_profili(self):
        start = time.time()
        r = _node('--categorie', 'PRIVATO', '--nazionalita', 'ITA',
                  '--quantita', '50', '--formato', 'JSON', '--skip-validation',
                  timeout=10)
        elapsed = time.time() - start
        assert r.returncode == 0, r.stderr
        assert elapsed < 2.0, f'Benchmark fallito: {elapsed:.1f}s > 2.0s'
        assert len(json.loads(r.stdout)) == 50


# ─── Guard validation (MAJOR fixes da code review) ───────────────────────────

class TestGuardValidation:
    def test_loadref_rifiuta_path_traversal(self):
        r = subprocess.run(
            ['node', '-e',
             "const {loadRef}=require('./generate_profiles.js');"
             "try{loadRef('../../../etc/passwd');process.exit(0)}"
             "catch(e){process.stderr.write(e.message);process.exit(1)}"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 1, 'loadRef avrebbe dovuto lanciare su path traversal'
        assert 'non valido' in r.stderr, f'Atteso messaggio "non valido", stderr: {r.stderr}'

    def test_distribuzione_rifiuta_somma_zero(self):
        r = subprocess.run(
            ['node', '-e',
             "const {calcolaDistribuzione}=require('./generate_profiles.js');"
             "try{calcolaDistribuzione(10,[0,0]);process.exit(0)}"
             "catch(e){process.exit(1)}"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 1, 'calcolaDistribuzione avrebbe dovuto lanciare su somma zero'

    def test_codice_data_rifiuta_data_invalida(self):
        r = subprocess.run(
            ['node', '-e',
             "const {calcolaCF}=require('./generate_profiles.js');"
             "try{calcolaCF('Mario','Rossi','not-a-date','M','H501');process.exit(0)}"
             "catch(e){process.exit(1)}"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 1, 'calcolaCF avrebbe dovuto lanciare su data invalida'
