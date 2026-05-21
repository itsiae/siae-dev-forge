# Rationale — fixture_001_toctou_auth_revocation

**Pattern**: BP-023 (toctou-authorization-revoke).

**Severity choice — SEV-2 (not SEV-1)**: the bypass requires an admin to
revoke a token mid-flow, so it is NOT a self-service auth bypass (which
would be SEV-1 / R-SEV1-02). The revoked grant continues for the
duration of the flow (≤ minutes), affecting < 1% of users in practice,
which lands the finding at R-SEV2-07. Escalate to SEV-1 only if the
upload itself is auth-bypass-class (e.g. profile-picture upload that
also rotates the user's avatar in a tenant-scoped resource).

**Edge cases accepted**:
- Token TTL < 60 s is a partial mitigation but still matches the
  pattern (race window remains for that minute).
- Per-chunk introspection middleware closes the window; not a finding.
