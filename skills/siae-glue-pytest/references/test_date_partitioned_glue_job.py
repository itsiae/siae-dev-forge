"""Test per DatePartitionedGlueJob (libs/custom_classes.py)."""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from libs.custom_classes import DatePartitionedGlueJob  # noqa: E402


def _make_job(patch_glue_args, start="1735689600", end="1735776000", force="0"):
    """Helper: istanzia DatePartitionedGlueJob con args."""
    patch_glue_args({
        "last_silver_update_time": start,
        "next_silver_update_time": end,
        "force_no_window": force,
    })
    return DatePartitionedGlueJob()


# ---------------- _parse_timestamp ----------------

def test_parse_timestamp_epoch_int(patch_glue_args):
    job = _make_job(patch_glue_args, start="1735689600", end="1735776000")
    assert job.start_commit_time == datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert job.end_commit_time == datetime(2025, 1, 2, 0, 0, tzinfo=timezone.utc)


def test_parse_timestamp_iso8601_with_z(patch_glue_args):
    job = _make_job(
        patch_glue_args,
        start="2025-03-15T10:30:00Z",
        end="2025-03-15T12:30:00Z",
    )
    assert job.start_commit_time == datetime(2025, 3, 15, 10, 30, tzinfo=timezone.utc)
    assert job.end_commit_time == datetime(2025, 3, 15, 12, 30, tzinfo=timezone.utc)


def test_parse_timestamp_invalid_raises(patch_glue_args):
    with pytest.raises(ValueError, match="Unable to parse"):
        _make_job(patch_glue_args, start="not-a-date", end="also-bad")


# ---------------- __init__ flags ----------------

def test_force_no_window_overrides(patch_glue_args):
    job = _make_job(patch_glue_args, start="-1", end="-1", force="1")
    assert job.start_commit_time.year == 1970
    assert job.end_commit_time.year == 3000


def test_force_no_window_partition_condition_is_wildcard(patch_glue_args):
    # force_no_window=1 -> finestra 1970..3000 -> anni diversi -> "1=1"
    job = _make_job(patch_glue_args, start="-1", end="-1", force="1")
    assert job.create_partition_condition() == "1=1"


def test_missing_window_raises_runtime(patch_glue_args):
    with pytest.raises(RuntimeError, match="Iceberg Delta Job Initialization Error"):
        _make_job(patch_glue_args, start="-1", end="1735776000", force="0")


# ---------------- create_partition_condition ----------------

def test_partition_different_years(patch_glue_args):
    # 2024-12-31 -> 2025-01-02
    job = _make_job(patch_glue_args, start="1735603200", end="1735776000")
    assert job.create_partition_condition() == "1=1"


def test_partition_same_year_different_month(patch_glue_args):
    # 2025-01-31 -> 2025-02-01
    job = _make_job(patch_glue_args, start="1738281600", end="1738368000")
    assert job.create_partition_condition() == "year = '2025'"


def test_partition_same_year_month_different_day(patch_glue_args):
    # 2025-03-01 -> 2025-03-02
    job = _make_job(patch_glue_args, start="1740787200", end="1740873600")
    assert job.create_partition_condition() == "year = '2025' AND month = '3'"


def test_partition_same_day(patch_glue_args):
    # 2025-06-15 00:00:00 -> 2025-06-15 23:00:00
    job = _make_job(patch_glue_args, start="1749945600", end="1750028400")
    assert job.create_partition_condition() == "year = '2025' AND month = '6' AND day = '15'"


def test_partition_with_sql_label(patch_glue_args):
    job = _make_job(patch_glue_args, start="1749945600", end="1750028400")
    cond = job.create_partition_condition(sql_label="s")
    assert cond == "s.year = '2025' AND s.month = '6' AND s.day = '15'"


# ---------------- get_incremental_dataframe ----------------

def test_get_incremental_dataframe_happy(spark, patch_glue_args):
    job = _make_job(patch_glue_args, start="1749945600", end="1750028400")
    data = [
        ("k1", "2025-06-15 10:00:00", 2025, 6, 15),  # inside
        ("k2", "2025-06-15 23:30:00", 2025, 6, 15),  # outside (>= end)
        ("k3", "2025-06-14 10:00:00", 2025, 6, 14),  # different day partition
    ]
    df = spark.createDataFrame(data, ["pk", "commit_time", "year", "month", "day"])
    result = job.get_incremental_dataframe(spark, df).collect()
    pks = sorted(r["pk"] for r in result)
    assert pks == ["k1"]


def test_get_incremental_dataframe_missing_column_raises(spark, patch_glue_args):
    job = _make_job(patch_glue_args, start="1749945600", end="1750028400")
    df = spark.createDataFrame([("k1",)], ["pk"])
    with pytest.raises(TypeError, match="Missing mandatory column"):
        job.get_incremental_dataframe(spark, df)


def test_get_incremental_dataframe_empty_df(spark, patch_glue_args):
    # Schema corretto ma zero righe: edge case frequente nei job incrementali
    # (finestra senza dati). Deve restituire un DataFrame vuoto, non sollevare.
    job = _make_job(patch_glue_args, start="1749945600", end="1750028400")
    df = spark.createDataFrame(
        [], "pk string, commit_time string, year int, month int, day int"
    )
    result = job.get_incremental_dataframe(spark, df).collect()
    assert result == []


# ---------------- get_delta_incremental_df ----------------

def test_get_delta_incremental_df_single_pk(spark, patch_glue_args):
    job = _make_job(patch_glue_args, start="1749945600", end="1750028400")
    data = [
        ("k1", "2025-06-15 10:00:00", 1, 2025, 6, 15),
        ("k1", "2025-06-15 11:00:00", 2, 2025, 6, 15),  # piu' recente, vince
        ("k2", "2025-06-15 09:00:00", 5, 2025, 6, 15),
    ]
    df = spark.createDataFrame(
        data, ["pk", "last_commit_time", "last_transact_id", "year", "month", "day"]
    )
    result = job.get_delta_incremental_df(spark, df, ["pk"]).collect()
    rows = sorted((r["pk"], r["last_transact_id"]) for r in result)
    assert rows == [("k1", 2), ("k2", 5)]


def test_get_delta_incremental_df_multi_pk(spark, patch_glue_args):
    job = _make_job(patch_glue_args, start="1749945600", end="1750028400")
    data = [
        ("a", "x", "2025-06-15 10:00:00", 1, 2025, 6, 15),
        ("a", "x", "2025-06-15 11:00:00", 2, 2025, 6, 15),  # vince
        ("a", "y", "2025-06-15 09:00:00", 3, 2025, 6, 15),  # diversa combo pk
    ]
    df = spark.createDataFrame(
        data, ["k1", "k2", "last_commit_time", "last_transact_id", "year", "month", "day"]
    )
    result = job.get_delta_incremental_df(spark, df, ["k1", "k2"]).collect()
    triples = sorted((r["k1"], r["k2"], r["last_transact_id"]) for r in result)
    assert triples == [("a", "x", 2), ("a", "y", 3)]


def test_get_delta_incremental_df_missing_column_raises(spark, patch_glue_args):
    job = _make_job(patch_glue_args, start="1749945600", end="1750028400")
    df = spark.createDataFrame([("k1",)], ["pk"])
    with pytest.raises(TypeError, match="Missing mandatory columns"):
        job.get_delta_incremental_df(spark, df, ["pk"])


def test_get_delta_incremental_df_empty_pk_raises(spark, patch_glue_args):
    job = _make_job(patch_glue_args, start="1749945600", end="1750028400")
    df = spark.createDataFrame(
        [("k", "2025-06-15", 1, 2025, 6, 15)],
        ["pk", "last_commit_time", "last_transact_id", "year", "month", "day"],
    )
    with pytest.raises(ValueError, match="Silver primary key list cannot be empty"):
        job.get_delta_incremental_df(spark, df, [])


def test_get_delta_incremental_df_dedup_only_in_window(spark, patch_glue_args):
    job = _make_job(patch_glue_args, start="1749945600", end="1750028400")
    data = [
        ("k1", "2025-06-15 10:00:00", 1, 2025, 6, 15),  # in window
        ("k1", "2025-06-14 10:00:00", 2, 2025, 6, 14),  # fuori partition
    ]
    df = spark.createDataFrame(
        data, ["pk", "last_commit_time", "last_transact_id", "year", "month", "day"]
    )
    result = job.get_delta_incremental_df(spark, df, ["pk"]).collect()
    assert len(result) == 1
    assert result[0]["last_transact_id"] == 1
