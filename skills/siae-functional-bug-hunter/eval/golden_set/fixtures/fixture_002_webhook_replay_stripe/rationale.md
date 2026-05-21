# Rationale — fixture_002_webhook_replay_stripe

**Pattern**: BP-019 (webhook-replay-or-out-of-order).

**Severity choice — SEV-1 (not SEV-2)**: the downstream side effect is
financial (duplicate receipt + duplicate audit row), AND Stripe
documents that redelivery is normal behaviour on at-least-once
semantics, so every active customer is exposed (>10% by definition).
BP-019 severity hint maps this to SEV-1 under the "downstream financial
AND > 10% exposed" escalation. Rubric row R-SEV1-03 ("financial side
effect duplicated").

**Edge cases accepted**:
- If the audit row has an idempotent UPSERT on event.id, the second
  manifestation (duplicate audit) disappears but the receipt-email
  manifestation remains → still SEV-1.
- If the handler is purely read-only (no mailer.send, no state write),
  not a finding.
