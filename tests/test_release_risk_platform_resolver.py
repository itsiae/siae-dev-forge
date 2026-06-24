"""REQ-13/14/15 — platform_resolver: identificazione piattaforma + path gerarchico."""
import pytest

from lib.release_risk.platform_resolver import (
    resolve_platform, release_slug, scorecard_path, PLATFORM_PREFIXES,
)


# --- REQ-13: identificazione piattaforma da nome servizio ---

@pytest.mark.parametrize("service,expected", [
    ("sport-x-service", "sport"),
    ("sport-gestione-licenze-service", "sport"),
    ("digital-channels-sport-bff", "sport"),   # prefisso più lungo → sport
    ("esb-sport-adapter", "sport"),
    ("pop-be", "pop"),
    ("pae-core", "pae"),
    ("ciam-auth", "ciam"),
    ("esb-sso-gateway", "ciam"),               # esb-sso → ciam (auth)
    ("ttpp-x-bff-service", "ttpp"),
    ("portal-apigateway-edge", "portal"),
])
def test_resolve_platform_known_prefixes(service, expected):
    assert resolve_platform(service) == expected


def test_resolve_platform_longest_prefix_wins():
    # 'digital-channels-sport-' (più lungo) NON deve essere mascherato da 'sport-'
    assert resolve_platform("digital-channels-sport-foo") == "sport"


def test_resolve_platform_fallback_first_token_no_shared_bucket():
    # servizio non mappato → primo token, NON un bucket 'unknown' condiviso (REQ-14)
    assert resolve_platform("foo-bar-service") == "foo"
    assert resolve_platform("billing-core") == "billing"
    # famiglie diverse → cartelle diverse (no aggregazione)
    assert resolve_platform("foo-a") != resolve_platform("baz-a")


def test_resolve_platform_override_wins():
    assert resolve_platform("sport-x-service", override="spa") == "spa"
    assert resolve_platform("sport-x-service", override="SPA/v2") == "spa_v2"  # / → _ (convenzione branch slug)


def test_resolve_platform_never_raises_on_garbage():
    for bad in ["", None, "   ", "///", "::::"]:
        out = resolve_platform(bad)  # type: ignore[arg-type]
        assert isinstance(out, str) and out  # sempre stringa non vuota


def test_resolve_platform_env_override_map(monkeypatch):
    monkeypatch.setenv("DEVFORGE_RELEASE_RISK_PLATFORM_MAP", "spa:spa-|sportello-;data:dwh-")
    assert resolve_platform("sportello-pratiche") == "spa"
    assert resolve_platform("dwh-etl") == "data"
    # i default restano attivi se l'env non li sovrascrive
    assert resolve_platform("sport-x") == "sport"


def test_platform_prefixes_aligned_with_known_sport():
    assert "sport" in PLATFORM_PREFIXES
    assert any(p.startswith("sport") for p in PLATFORM_PREFIXES["sport"])


# --- REQ-15: release slug + gerarchia path ---

def test_release_slug_uses_version_when_known():
    assert release_slug("sport-x-service", "2.0.0", "release/2.0.0") == "sport-x-service-2.0.0"


def test_release_slug_fallback_to_branch_when_version_unknown():
    s = release_slug("test-service", "unknown", "release/1.0.0")
    assert s == "test-service-release_1.0.0"


def test_release_slug_sanitizes_separators():
    s = release_slug("svc", None, "feature/foo:bar")
    assert "/" not in s and ":" not in s


def test_scorecard_path_is_hierarchical(tmp_path):
    path, platform = scorecard_path(tmp_path, "sport-x-service", "2.0.0", "release/2.0.0")
    assert platform == "sport"
    expected = tmp_path / "docs" / "releases" / "sport" / "sport-x-service-2.0.0" / "scorecard.md"
    assert path == expected


def test_scorecard_path_separates_platforms(tmp_path):
    p1, _ = scorecard_path(tmp_path, "sport-a", "1.0", "release/1.0")
    p2, _ = scorecard_path(tmp_path, "pop-b", "1.0", "release/1.0")
    # piattaforme diverse → sottoalberi diversi (REQ-14: no aggregazione)
    assert p1.parent.parent != p2.parent.parent
    assert "sport" in p1.parts and "pop" in p2.parts


def test_scorecard_path_honors_override(tmp_path):
    path, platform = scorecard_path(tmp_path, "sport-x", "1.0", "release/1.0", override="spa")
    assert platform == "spa"
    assert "spa" in path.parts
