"""Test per IcebergGlueJob (libs/custom_classes.py)."""
import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from libs.custom_classes import IcebergGlueJob  # noqa: E402


@pytest.fixture
def setup_iceberg_args(patch_glue_args, monkeypatch):
    """Patch sys.argv + getResolvedOptions per istanziare IcebergGlueJob."""
    def _setup(environment="dev", warehouse="s3://test-warehouse/"):
        patch_glue_args({
            "iceberg_job_catalog_warehouse": warehouse,
            "environment": environment,
        })
        # Cambia CWD per evitare di leggere un app_conf.json fortuito.
        monkeypatch.chdir(Path(__file__).parent)
        return environment, warehouse

    return _setup


def test_init_dev_env_prefix(setup_iceberg_args):
    setup_iceberg_args(environment="dev")
    job = IcebergGlueJob()
    assert job.env_prefix == "dev_"


def test_init_prod_env_prefix_empty(setup_iceberg_args):
    setup_iceberg_args(environment="prod")
    job = IcebergGlueJob()
    assert job.env_prefix == ""


def test_iceberg_config_keys_present(setup_iceberg_args):
    _, warehouse = setup_iceberg_args(environment="qa", warehouse="s3://qa-wh/")
    job = IcebergGlueJob()
    conf = dict(job.conf.getAll())
    assert conf["spark.sql.catalog.job_catalog.warehouse"] == warehouse
    assert conf["spark.sql.catalog.job_catalog"] == "org.apache.iceberg.spark.SparkCatalog"
    assert conf["spark.sql.catalog.job_catalog.catalog-impl"] == "org.apache.iceberg.aws.glue.GlueCatalog"
    assert conf["spark.sql.catalog.job_catalog.io-impl"] == "org.apache.iceberg.aws.s3.S3FileIO"
    assert conf["spark.sql.extensions"] == "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
    assert conf["spark.sql.sources.partitionOverwriteMode"] == "dynamic"
    assert conf["spark.sql.iceberg.handle-timestamp-without-timezone"] == "true"
    assert conf["spark.sql.parquet.mergeSchema"] == "true"


def test_custom_spark_config_keys(setup_iceberg_args):
    setup_iceberg_args()
    job = IcebergGlueJob()
    job.custom_spark_config()
    conf = dict(job.conf.getAll())
    assert conf["spark.shuffle.file.buffer"] == "64k"
    assert conf["spark.serializer"] == "org.apache.spark.serializer.KryoSerializer"
    assert conf["spark.cleaner.periodicGC.interval"] == "15min"
    assert conf["spark.sql.adaptive.forceOptimizeSkewedJoin"] == "true"
    assert conf["spark.sql.broadcastTimeout"] == "600"


def test_set_spark_configs_from_file(setup_iceberg_args, tmp_path, monkeypatch):
    setup_iceberg_args()
    conf_file = tmp_path / "app_conf.json"
    conf_file.write_text(json.dumps({
        "spark_configs": {
            "spark.sql.parquet.filterPushdown": "true",
            "spark.cleaner.periodicGC.interval": "10min",
        }
    }))
    monkeypatch.chdir(tmp_path)
    job = IcebergGlueJob()
    job.set_spark_configs("app_conf.json")
    conf = dict(job.conf.getAll())
    assert conf["spark.sql.parquet.filterPushdown"] == "true"
    assert conf["spark.cleaner.periodicGC.interval"] == "10min"


def test_set_spark_configs_file_not_found(setup_iceberg_args, capsys):
    setup_iceberg_args()
    job = IcebergGlueJob()
    job.set_spark_configs("missing_file.json")
    captured = capsys.readouterr()
    assert "not found" in captured.out.lower()


def test_set_spark_configs_malformed_json(setup_iceberg_args, tmp_path, monkeypatch, capsys):
    setup_iceberg_args()
    bad = tmp_path / "bad.json"
    bad.write_text("{not-json")
    monkeypatch.chdir(tmp_path)
    job = IcebergGlueJob()
    job.set_spark_configs("bad.json")
    captured = capsys.readouterr()
    assert "error decoding json" in captured.out.lower()
