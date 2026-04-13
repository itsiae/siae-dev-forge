.PHONY: test-unit test-integration test-chaos test-acceptance test-all

# Unit tests — pure python, no external dependencies, fast
test-unit:
	cd ../.. && python3 -m pytest tests/zero-loss/unit -x -v

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
