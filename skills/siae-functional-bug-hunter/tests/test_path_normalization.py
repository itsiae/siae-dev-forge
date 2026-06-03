"""test_path_normalization.py — verifies the canonical form for the five
cases enumerated in references/cross_stack_bridges.md.

Run: pytest tests/test_path_normalization.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add scripts/ to sys.path so the module can be imported without packaging.
THIS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = THIS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pytest  # noqa: E402

from path_normalize import normalize_path  # noqa: E402


# Cases drawn 1:1 from references/cross_stack_bridges.md Path Normalization Rules.
CANONICAL = "/v1/users/{id}"

CASES = [
    pytest.param("/v1/users/:id",       CANONICAL, id="express-koa"),
    pytest.param("/v1/users/<id>",      CANONICAL, id="flask-untyped"),
    pytest.param("/v1/users/<id:int>",  CANONICAL, id="flask-typed"),
    pytest.param("/v1/users/{id}",      CANONICAL, id="fastapi-oas"),
    pytest.param("/v1/users/{id:int}",  CANONICAL, id="fastapi-typed"),
]


@pytest.mark.parametrize("source, expected", CASES)
def test_normalize_path_table_cases(source, expected):
    assert normalize_path(source) == expected


def test_query_string_is_stripped():
    assert normalize_path("/v1/users/{id}?expand=profile") == CANONICAL


def test_already_canonical_is_idempotent():
    assert normalize_path(CANONICAL) == CANONICAL
    # Idempotency under double-normalization
    assert normalize_path(normalize_path("/v1/users/:id")) == CANONICAL


def test_unparametrised_path_unchanged():
    assert normalize_path("/healthz") == "/healthz"


def test_multiple_params_normalized():
    assert normalize_path("/v1/orgs/<org_id>/users/:user_id") == "/v1/orgs/{org_id}/users/{user_id}"
    assert normalize_path("/v1/orgs/{org_id:uuid}/users/{user_id:int}") == "/v1/orgs/{org_id}/users/{user_id}"


def test_non_string_raises():
    with pytest.raises(TypeError):
        normalize_path(123)  # type: ignore[arg-type]
