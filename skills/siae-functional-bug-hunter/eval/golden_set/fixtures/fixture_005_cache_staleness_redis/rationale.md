# Rationale — fixture_005_cache_staleness_redis

**Pattern**: BP-020 (cache-invalidation-staleness).

**Severity choice — SEV-3 (not SEV-2)**: stale window is bounded at
TTL=300 s (5 minutes), and the data class is profile metadata (not auth,
not financial, not PII-sensitive beyond display_name). BP-020 severity
hint maps to SEV-3 in general, and only escalates to SEV-2 when the
staleness window exceeds 5 minutes AND the data class is
auth/financial/PII. Rubric row R-SEV3-09.

**Edge cases accepted**:
- If `redis.delete(profile:{user_id})` IS called on PUT but the cache
  also lives in a CDN edge that was not purged: still a finding, but the
  TTL and surface differ; classify the same way (cache-staleness) with
  the CDN as the staleness source.
- TTL ≤ 5 s effectively closes the window; mark PARTIAL rather than
  VERIFIED.
