"""
Fixture e setup globale per i test del modulo glue-jobs.

- Stub di `awsglue.*` via sys.modules: necessario perche' awsglue non e' un
  pacchetto pip installabile, esiste solo nel runtime AWS Glue. Lo stub permette
  l'import dei job e della lib custom_classes senza errori.
- Fixture `spark` scope=session: SparkSession locale per testare logica DataFrame.
"""
import sys
import types
from unittest.mock import MagicMock

import pytest

# Storage globale per i valori restituiti dallo stub di getResolvedOptions.
# La fixture `patch_glue_args` mutua questo dict; lo stub e' una closure che
# lo legge ad ogni chiamata, cosi' qualsiasi modulo che ha gia' bindato
# `from awsglue.utils import getResolvedOptions` vede i valori aggiornati.
_GLUE_ARGS: dict = {}


def _stub_awsglue() -> None:
    """Pre-popola sys.modules con stub MagicMock per i package awsglue."""
    if "awsglue" in sys.modules:
        return

    awsglue = types.ModuleType("awsglue")
    awsglue_utils = types.ModuleType("awsglue.utils")
    awsglue_context = types.ModuleType("awsglue.context")
    awsglue_transforms = types.ModuleType("awsglue.transforms")
    awsglue_job = types.ModuleType("awsglue.job")
    awsglue_dynamicframe = types.ModuleType("awsglue.dynamicframe")

    def _get_resolved_options(argv, keys):
        return {k: _GLUE_ARGS.get(k, "") for k in keys}

    awsglue_utils.getResolvedOptions = _get_resolved_options
    awsglue_context.GlueContext = MagicMock(name="GlueContext")
    awsglue_job.Job = MagicMock(name="Job")
    awsglue_dynamicframe.DynamicFrame = MagicMock(name="DynamicFrame")
    awsglue_transforms.ApplyMapping = MagicMock(name="ApplyMapping")
    awsglue_transforms.DropFields = MagicMock(name="DropFields")
    awsglue_transforms.SelectFields = MagicMock(name="SelectFields")
    awsglue_transforms.ResolveChoice = MagicMock(name="ResolveChoice")

    sys.modules["awsglue"] = awsglue
    sys.modules["awsglue.utils"] = awsglue_utils
    sys.modules["awsglue.context"] = awsglue_context
    sys.modules["awsglue.transforms"] = awsglue_transforms
    sys.modules["awsglue.job"] = awsglue_job
    sys.modules["awsglue.dynamicframe"] = awsglue_dynamicframe

    # Attacca i submoduli come attributi del package parent: necessario per
    # supportare `import awsglue; awsglue.utils.getResolvedOptions(...)`.
    awsglue.utils = awsglue_utils
    awsglue.context = awsglue_context
    awsglue.transforms = awsglue_transforms
    awsglue.job = awsglue_job
    awsglue.dynamicframe = awsglue_dynamicframe


_stub_awsglue()


@pytest.fixture(scope="session")
def spark():
    """SparkSession locale condivisa fra tutti i test della sessione."""
    import os

    # Allinea worker e driver Python: previene PYTHON_VERSION_MISMATCH quando
    # nel PATH coesistono piu' interpreti minor (es. 3.13 e 3.14).
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

    from pyspark.sql import SparkSession

    session = (
        SparkSession.builder
        .master("local[2]")
        .appName("test-glue-codifica")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        # Fix bind su macOS / runner: forza localhost esplicito per il driver.
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture
def patch_glue_args():
    """
    Imposta i valori che il stub di getResolvedOptions restituira' durante il
    test corrente. Funziona anche se i moduli sotto test hanno gia' bindato
    `from awsglue.utils import getResolvedOptions` (lo stub e' una closure che
    legge dal dict globale `_GLUE_ARGS`).
    """
    def _patch(values: dict):
        _GLUE_ARGS.clear()
        _GLUE_ARGS.update(values)
        return values

    yield _patch
    _GLUE_ARGS.clear()
