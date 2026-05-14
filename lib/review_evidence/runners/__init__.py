"""Runner framework + auto-load OSS adapters."""
from lib.review_evidence.runners._registry import (  # noqa: F401
    Runner,
    applicable,
    register,
    registry,
)

# Auto-register OSS adapters at module import time (parallels collectors pattern).
from lib.review_evidence.runners import bandit  # noqa: F401,E402
from lib.review_evidence.runners import gitleaks  # noqa: F401,E402
from lib.review_evidence.runners import pip_audit  # noqa: F401,E402
from lib.review_evidence.runners import npm_audit  # noqa: F401,E402
from lib.review_evidence.runners import eslint_security  # noqa: F401,E402
from lib.review_evidence.runners import mvn_deps  # noqa: F401,E402
from lib.review_evidence.runners import tfsec  # noqa: F401,E402
from lib.review_evidence.runners import checkov  # noqa: F401,E402
from lib.review_evidence.runners import vulture  # noqa: F401,E402
from lib.review_evidence.runners import pyright  # noqa: F401,E402
from lib.review_evidence.runners import ts_unused_exports  # noqa: F401,E402
from lib.review_evidence.runners import spotbugs  # noqa: F401,E402
from lib.review_evidence.runners import swiftlint  # noqa: F401,E402
from lib.review_evidence.runners import detekt  # noqa: F401,E402
from lib.review_evidence.runners import ktlint  # noqa: F401,E402
from lib.review_evidence.runners import cfn_lint  # noqa: F401,E402
