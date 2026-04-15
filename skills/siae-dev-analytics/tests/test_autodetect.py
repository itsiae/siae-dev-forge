"""Test per autodetect_sources.py — TDD first."""
from unittest.mock import patch, MagicMock
import pytest

# L'import si risolve via sys.path in conftest.py (vedi Step 4).
# Fallisce con ModuleNotFoundError finché Step 3 non è completato — atteso in TDD RED.
import autodetect_sources as ad


def test_github_authenticated_returns_true():
    """gh auth status OK → github=True."""
    with patch("subprocess.run") as mock:
        mock.return_value = MagicMock(returncode=0, stdout="Logged in to github.com")
        result = ad.check_gh_auth()
    assert result is True


def test_github_not_authenticated_returns_false():
    """gh auth status KO → github=False."""
    with patch("subprocess.run") as mock:
        mock.return_value = MagicMock(returncode=1, stdout="")
        result = ad.check_gh_auth()
    assert result is False


def test_s3_bucket_accessible_returns_true():
    """boto3 head_bucket OK → s3=True."""
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.head_bucket.return_value = {}
        mock_client.return_value = mock_s3
        result = ad.check_s3_prefix("siae-devforge-telemetry", "devforge-logs/")
    assert result is True


def test_s3_bucket_no_creds_returns_false():
    """boto3 NoCredentials → s3=False."""
    with patch("boto3.client") as mock_client:
        mock_client.side_effect = Exception("NoCredentialsError")
        result = ad.check_s3_prefix("siae-devforge-telemetry", "devforge-logs/")
    assert result is False


def test_mode_full_all_sources_available():
    """github + s3_devforge + s3_blend → FULL."""
    report = ad.SourceReport(github=True, s3_devforge=True, s3_blend=True)
    assert report.mode() == "FULL"


def test_mode_hybrid_s3_partial():
    """github + s3_devforge senza s3_blend → HYBRID."""
    report = ad.SourceReport(github=True, s3_devforge=True, s3_blend=False)
    assert report.mode() == "HYBRID"


def test_mode_github_only_no_s3():
    """github ok, nessun s3 → GITHUB-ONLY."""
    report = ad.SourceReport(github=True, s3_devforge=False, s3_blend=False)
    assert report.mode() == "GITHUB-ONLY"


def test_mode_s3_blend_only_without_devforge_is_github_only():
    """github + s3_blend SENZA s3_devforge → GITHUB-ONLY.

    Senza telemetry events (s3_devforge) non c'è accuracy superior su Q4
    verification_rate. Avere solo blend-usage non giustifica HYBRID.
    """
    report = ad.SourceReport(github=True, s3_devforge=False, s3_blend=True)
    assert report.mode() == "GITHUB-ONLY"


def test_mode_abort_no_github():
    """github mancante → ABORT."""
    report = ad.SourceReport(github=False, s3_devforge=False, s3_blend=False)
    assert report.mode() == "ABORT"


def test_autodetect_aborts_without_github():
    """autodetect() solleva RuntimeError se github mancante."""
    with patch.object(ad, "check_gh_auth", return_value=False):
        with pytest.raises(RuntimeError, match="GitHub CLI not authenticated"):
            ad.autodetect(abort_on_no_github=True)


def test_autodetect_returns_report_full_mode():
    """autodetect() con tutti disponibili → report FULL."""
    with patch.object(ad, "check_gh_auth", return_value=True), \
         patch.object(ad, "check_s3_prefix", return_value=True):
        report = ad.autodetect()
    assert report.mode() == "FULL"
    assert report.github is True
    assert report.s3_devforge is True
    assert report.s3_blend is True
