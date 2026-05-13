#!/usr/bin/env bash
set -euo pipefail

TF_DIR="infra/terraform/review-evidence-baseline"

if ! command -v terraform >/dev/null 2>&1; then
    echo "SKIP: terraform not installed"
    exit 0
fi

cd "$(git rev-parse --show-toplevel)/${TF_DIR}"

terraform init -backend=false -input=false
terraform validate
terraform fmt -check

echo "PASS: terraform module valid"
