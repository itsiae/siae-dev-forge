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
# v1.58+ — mutation testing adapters (advisory, opt-in via DEVFORGE_MUTATION_ENABLED)
from lib.review_evidence.runners import pit  # noqa: F401,E402
from lib.review_evidence.runners import mutmut  # noqa: F401,E402
from lib.review_evidence.runners import stryker  # noqa: F401,E402
