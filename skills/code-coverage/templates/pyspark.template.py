"""
Use this template for: PySpark / Databricks / Delta Lake data pipelines.
Requires: pytest, pytest-cov, chispa, pyspark.
SparkSession uses local[*] master — never connects to a real cluster.

Replace all {{PLACEHOLDER}} tokens before use.
"""

import pytest
from unittest.mock import MagicMock, patch
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import {{SCHEMA_TYPES}}
from chispa import assert_df_equality

from {{MODULE_IMPORT_PATH}} import {{transform_function}}, {{ClassName}}


# ─── Session Fixture (scope=session for performance) ─────────────────────────

@pytest.fixture(scope="session")
def spark() -> SparkSession:
    """Local SparkSession for unit tests — never uses a real cluster."""
    return (
        SparkSession.builder
        .master("local[*]")
        .appName("{{module_name}}_tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


# ─── Schema Fixtures ──────────────────────────────────────────────────────────

INPUT_SCHEMA = {{INPUT_SCHEMA}}   # e.g. StructType([StructField("id", StringType(), True), ...])
OUTPUT_SCHEMA = {{OUTPUT_SCHEMA}}


# ─── Tests for {{transform_function}} ────────────────────────────────────────

class Test{{TransformFunctionName}}:

    def test_happy_path_transforms_correctly(self, spark: SparkSession) -> None:
        """Happy path: standard input produces expected output DataFrame."""
        # Arrange
        input_data = {{HAPPY_PATH_INPUT_DATA}}
        expected_data = {{EXPECTED_OUTPUT_DATA}}

        input_df = spark.createDataFrame(input_data, schema=INPUT_SCHEMA)
        expected_df = spark.createDataFrame(expected_data, schema=OUTPUT_SCHEMA)

        # Act
        result_df = {{transform_function}}(spark, input_df)

        # Assert
        assert_df_equality(result_df, expected_df, ignore_row_order=True)

    def test_handles_empty_dataframe(self, spark: SparkSession) -> None:
        """Edge case 1: empty input produces empty output with correct schema."""
        # Arrange
        input_df = spark.createDataFrame([], schema=INPUT_SCHEMA)

        # Act
        result_df = {{transform_function}}(spark, input_df)

        # Assert
        assert result_df.count() == 0
        assert set(result_df.columns) == set(OUTPUT_SCHEMA.fieldNames())

    def test_handles_null_values_in_{{nullable_column}}(self, spark: SparkSession) -> None:
        """Edge case 2: null in {{nullable_column}} is handled gracefully."""
        # Arrange
        input_data = {{NULL_INPUT_DATA}}
        input_df = spark.createDataFrame(input_data, schema=INPUT_SCHEMA)

        # Act
        result_df = {{transform_function}}(spark, input_df)

        # Assert
        null_count = result_df.filter(result_df["{{nullable_column}}"].isNull()).count()
        assert null_count == {{EXPECTED_NULL_COUNT}}

    def test_raises_for_missing_required_column(self, spark: SparkSession) -> None:
        """Negative path: missing required column raises AnalysisException."""
        from pyspark.sql.utils import AnalysisException
        # Arrange — schema missing required column
        broken_df = spark.createDataFrame({{BROKEN_INPUT_DATA}})

        # Act & Assert
        with pytest.raises((AnalysisException, ValueError)):
            {{transform_function}}(spark, broken_df)

    def test_deduplication(self, spark: SparkSession) -> None:
        """Edge case: duplicate rows are deduplicated correctly."""
        # Arrange
        input_data = {{DUPLICATE_INPUT_DATA}}
        input_df = spark.createDataFrame(input_data, schema=INPUT_SCHEMA)

        # Act
        result_df = {{transform_function}}(spark, input_df)

        # Assert
        assert result_df.count() == {{EXPECTED_DEDUP_COUNT}}
        assert result_df.distinct().count() == result_df.count()


# ─── Tests for {{ClassName}} (class-based pipeline) ──────────────────────────

class Test{{ClassName}}:

    @pytest.fixture
    def pipeline(self, spark: SparkSession) -> {{ClassName}}:
        return {{ClassName}}(spark=spark, {{CONSTRUCTOR_PARAMS}})

    def test_run_happy_path(self, pipeline: {{ClassName}}, spark: SparkSession) -> None:
        """Happy path: run() produces expected output."""
        # Arrange
        input_df = spark.createDataFrame({{HAPPY_PATH_INPUT_DATA}}, schema=INPUT_SCHEMA)
        expected_df = spark.createDataFrame({{EXPECTED_OUTPUT_DATA}}, schema=OUTPUT_SCHEMA)

        # Act
        result_df = pipeline.run(input_df)

        # Assert
        assert_df_equality(result_df, expected_df, ignore_row_order=True)

    def test_run_with_empty_input(self, pipeline: {{ClassName}}, spark: SparkSession) -> None:
        """Edge case: empty input does not crash, returns empty DataFrame."""
        # Arrange
        empty_df = spark.createDataFrame([], schema=INPUT_SCHEMA)

        # Act
        result_df = pipeline.run(empty_df)

        # Assert
        assert result_df.count() == 0
