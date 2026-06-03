"""
Smoke test: importa ogni Glue job script per coprire il top-level.

Con awsglue.* mockato (vedi conftest.py), l'import non esegue il job ma valida
che il modulo si carichi senza errori di sintassi / dipendenze mancanti.

NOTA (W3 spec-review): questo test non valida la correttezza delle chiamate ad
awsglue (vedi design doc §7). Lo stub MagicMock fa "passare" qualsiasi chiamata.

I job fanno `from custom_classes import ...` (senza prefix `libs.`), quindi
aggiungiamo `src/libs` direttamente in sys.path per replicare il path runtime
di Glue (dove custom_classes e' caricato come libreria separata).
"""
import importlib.util
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SRC / "libs"))

# (filename, expected_class_name) per validare che lo smoke import abbia
# caricato la classe attesa, non solo "qualcosa".
JOB_SPECS = [
    ("cluster-action.py", "Cluster_action"),
    ("cluster-cache.py", "Cluster_cache"),
    ("cluster-cache-non-current.py", "Cluster_cache_non_current"),
    ("cluster-disambiguation.py", "Cluster_disambiguation"),
    ("clusters-hash.py", "Clusters_hash"),
    ("master_usage_archive.py", "MasterUsageArchive"),
    ("master-usage.py", "Master_usage"),
]

JOB_FILES = [spec[0] for spec in JOB_SPECS]


def _import_job(filename: str):
    path = SRC / filename
    assert path.exists(), f"Job script non trovato: {path}"
    mod_name = filename.replace("-", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("job_file,expected_class", JOB_SPECS)
def test_job_imports_without_error(job_file, expected_class, patch_glue_args):
    """Ogni Glue job script deve importarsi e definire la classe attesa."""
    patch_glue_args({
        "JOB_NAME": "test-job",
        "iceberg_job_catalog_warehouse": "s3://test/",
        "environment": "dev",
        "last_silver_update_time": "1735689600",
        "next_silver_update_time": "1735776000",
        "force_no_window": "1",
    })
    module = _import_job(job_file)
    # Sanity check forte: la classe attesa deve essere presente nel modulo,
    # non basta che il modulo sia non-None (dir() su MagicMock e' sempre populato).
    assert hasattr(module, expected_class), (
        f"{job_file}: classe attesa '{expected_class}' non trovata"
    )


def test_all_jobs_listed():
    """Verifica che il numero atteso di job sia presente fisicamente e viceversa."""
    actual = {p.name for p in SRC.glob("*.py")}
    expected = set(JOB_FILES)
    missing = expected - actual
    assert not missing, f"Job attesi ma non trovati: {missing}"
    # Check inverso: un nuovo job in src/ non censito in JOB_SPECS resterebbe
    # senza smoke/class test e farebbe scendere la coverage silenziosamente.
    unexpected = actual - expected
    assert not unexpected, f"Job trovati ma non censiti in JOB_SPECS: {unexpected}"
