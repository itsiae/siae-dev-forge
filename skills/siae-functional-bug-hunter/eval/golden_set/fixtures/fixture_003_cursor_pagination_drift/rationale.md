# Rationale — fixture_003_cursor_pagination_drift

**Pattern**: BP-021 (cursor-pagination-instability).

**Severity choice — SEV-3 (not SEV-2)**: skipped or duplicated orders
are a correctness bug but only manifest when `created_at` collisions
exist (uncommon for orders created interactively, common for batch
imports). The end-user observes a recoverable inconsistency on
infrequent paths → SEV-3 / R-SEV3-01. Escalates to SEV-2 only if the
missed record class is auth-relevant (e.g. permission revocations) or
financial reconciliation runs over this endpoint.

**Edge cases accepted**:
- If created_at has microsecond resolution AND orders are never created
  in batches, the collision is too rare to manifest reliably; still a
  finding (the bug is in the query shape), but mark reproduction_rate
  as `<80%-needs-harness`.
- If the query already uses ORDER BY created_at DESC, id DESC: not a
  finding.
