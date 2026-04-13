.PHONY: test-unit test-integration test-chaos test-acceptance test-all

# Bash unit tests — verifica logger.sh, hooks, telemetry-upload.sh integration
test-bash:
	@for t in unit/test_*.sh; do \
		echo "=== $$(basename $$t) ==="; \
		bash "$$t" || exit 1; \
	done

# Python unit tests — atomic_write.py
test-python:
	cd ../.. && python3 -m pytest tests/zero-loss/unit -x -v

# Unit tests — combined bash + python (FIX MAJOR iter-5 review: bash test ora wired)
test-unit: test-bash test-python

# Integration tests — require LocalStack via docker-compose
test-integration:
	cd integration && docker-compose up -d
	cd ../.. && python3 -m pytest tests/zero-loss/integration -x -v
	cd integration && docker-compose down

# Chaos tests — property-based, slow, nightly
test-chaos:
	cd ../.. && python3 -m pytest tests/zero-loss/chaos --hypothesis-profile=ci

# Acceptance test — post-deploy certification (requires AWS credentials)
test-acceptance:
	cd ../.. && python3 tests/zero-loss/acceptance/test_zero_loss_certification.py

test-all: test-unit test-integration test-chaos
