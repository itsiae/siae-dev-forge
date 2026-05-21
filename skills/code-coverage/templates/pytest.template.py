"""
PYTEST TEMPLATE — Mock pattern rationale
====================================================================
mocker.patch('module.path.symbol') sostituisce il simbolo nel namespace
del CALLER (NON dove definito). Per metodi su classi: patch.object(cls, 'method').
Per async: usa AsyncMock dal modulo unittest.mock (mocker.patch ritorna MagicMock di default).
Verify export shape FIRST: python -c "import module; print(dir(module))"
====================================================================

Use this template for: FastAPI, Flask, Django, Celery, boto3, generic Python services.
Requires: pytest, pytest-cov, pytest-asyncio, pytest-mock.

Replace all {{PLACEHOLDER}} tokens before use.

C1 fix — Placeholder cleanup (HIGH severity)
====================================================================
La riga `from {{MODULE_IMPORT_PATH}} import {{ClassName}}, {{function_name}}`
produce sintassi invalida se uno dei due placeholder è vuoto. Dopo la
sostituzione, eseguire `clean_template_placeholders` di
`lib/template-cache.sh` che:
  - splitta la import list su `,`, scarta simboli vuoti
  - rimuove la riga intera se la import list resta vuota
====================================================================
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Any

# IMPORT_VARIANT: cleanup_template_placeholders normalizza simboli vuoti.
from {{MODULE_IMPORT_PATH}} import {{ClassName}}, {{function_name}}


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def {{dep_fixture_name}}() -> MagicMock:
    """Mock for {{DepClassName}}."""
    mock = MagicMock(spec={{DepClassName}})
    mock.{{dep_method}}.return_value = {{DEP_DEFAULT_RETURN}}
    return mock


@pytest.fixture
def {{instance_fixture_name}}({{dep_fixture_name}}: MagicMock) -> {{ClassName}}:
    """Fresh {{ClassName}} instance with injected mock dependency."""
    return {{ClassName}}({{dep_fixture_name}})


# ─── Tests for {{function_name}} ──────────────────────────────────────────────

class Test{{FunctionName}}:

    def test_{{happy_path_name}}(self, mocker: Any) -> None:
        """Happy path: {{HAPPY_PATH_DESCRIPTION}}."""
        # Arrange
        mock_dep = mocker.patch("{{MODULE_IMPORT_PATH}}.{{dep_name}}")
        mock_dep.return_value = {{DEP_RETURN_VALUE}}
        input_data = {{HAPPY_PATH_INPUT}}

        # Act
        result = {{function_name}}(input_data)

        # Assert
        assert result == {{EXPECTED_OUTPUT}}
        mock_dep.assert_called_once_with({{DEP_EXPECTED_ARG}})

    def test_{{edge_case_1_name}}_with_empty_input(self, mocker: Any) -> None:
        """Edge case 1: {{EDGE_CASE_1_DESCRIPTION}}."""
        # Arrange
        mock_dep = mocker.patch("{{MODULE_IMPORT_PATH}}.{{dep_name}}")
        mock_dep.return_value = {{EDGE_CASE_1_DEP_RETURN}}

        # Act
        result = {{function_name}}({{EDGE_CASE_1_INPUT}})

        # Assert
        assert result == {{EDGE_CASE_1_EXPECTED}}

    def test_{{edge_case_2_name}}_at_boundary(self, mocker: Any) -> None:
        """Edge case 2: {{EDGE_CASE_2_DESCRIPTION}}."""
        # Arrange
        boundary_input = {{EDGE_CASE_2_INPUT}}

        # Act
        result = {{function_name}}(boundary_input)

        # Assert
        assert result is not None
        assert result == {{EDGE_CASE_2_EXPECTED}}

    def test_raises_{{error_type_lower}}_for_invalid_input(self) -> None:
        """Negative path: {{NEGATIVE_CONDITION}}."""
        # Arrange
        invalid_input = {{INVALID_INPUT}}

        # Act & Assert
        with pytest.raises({{ErrorType}}, match="{{ERROR_MESSAGE_REGEX}}"):
            {{function_name}}(invalid_input)


# ─── Tests for {{ClassName}} ──────────────────────────────────────────────────

class Test{{ClassName}}:

    def test_{{method_name}}_happy_path(
        self,
        {{instance_fixture_name}}: {{ClassName}},
        {{dep_fixture_name}}: MagicMock,
    ) -> None:
        """Happy path: {{HAPPY_PATH_DESCRIPTION}}."""
        # Arrange
        {{dep_fixture_name}}.{{dep_method}}.return_value = {{DEP_RETURN_VALUE}}
        input_data = {{HAPPY_PATH_INPUT}}

        # Act
        result = {{instance_fixture_name}}.{{method_name}}(input_data)

        # Assert
        assert result == {{EXPECTED_OUTPUT}}
        {{dep_fixture_name}}.{{dep_method}}.assert_called_once_with({{DEP_EXPECTED_ARG}})

    def test_{{method_name}}_returns_default_for_none(
        self, {{instance_fixture_name}}: {{ClassName}}
    ) -> None:
        """Edge case: None input returns default value."""
        # Arrange + Act
        result = {{instance_fixture_name}}.{{method_name}}(None)
        # Assert
        assert result == {{DEFAULT_EXPECTED}}

    def test_{{method_name}}_handles_max_input(
        self, {{instance_fixture_name}}: {{ClassName}}
    ) -> None:
        """Edge case: maximum boundary input."""
        # Arrange
        max_input = {{MAX_BOUNDARY_INPUT}}
        # Act
        result = {{instance_fixture_name}}.{{method_name}}(max_input)
        # Assert
        assert result is not None

    def test_{{method_name}}_raises_for_invalid(
        self, {{instance_fixture_name}}: {{ClassName}}
    ) -> None:
        """Negative path: invalid input raises {{ErrorType}}."""
        # Arrange + Act + Assert
        with pytest.raises({{ErrorType}}):
            {{instance_fixture_name}}.{{method_name}}({{INVALID_INPUT}})


# ─── Async tests (use when function is async) ─────────────────────────────────

class Test{{AsyncClassName}}:

    @pytest.mark.asyncio
    async def test_{{async_method_name}}_happy_path(self, mocker: Any) -> None:
        """Async happy path."""
        # Arrange
        mock_dep = mocker.patch("{{MODULE_IMPORT_PATH}}.{{async_dep_name}}", new_callable=AsyncMock)
        mock_dep.return_value = {{DEP_RETURN_VALUE}}
        instance = {{AsyncClassName}}()

        # Act
        result = await instance.{{async_method_name}}({{HAPPY_PATH_INPUT}})

        # Assert
        assert result == {{EXPECTED_OUTPUT}}
        mock_dep.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_{{async_method_name}}_propagates_exception(self, mocker: Any) -> None:
        """Negative path: dependency failure propagates."""
        # Arrange
        mock_dep = mocker.patch("{{MODULE_IMPORT_PATH}}.{{async_dep_name}}", new_callable=AsyncMock)
        mock_dep.side_effect = {{ErrorType}}("{{ERROR_MESSAGE}}")

        instance = {{AsyncClassName}}()

        # Act & Assert
        with pytest.raises({{ErrorType}}, match="{{ERROR_MESSAGE_REGEX}}"):
            await instance.{{async_method_name}}({{HAPPY_PATH_INPUT}})
