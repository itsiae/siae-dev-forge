# Rationale — fixture_004_dst_cron_skip

**Pattern**: BP-022 (dst-scheduler-skip).

**Severity choice — SEV-2 (not SEV-3)**: this job underpins financial
reconciliation, which has a compliance deadline (daily summary to
finance@). BP-022 severity hint maps daily-reconciliation cases to
SEV-2 under the "underpins a financial reconciliation or a compliance
deadline" escalation. Rubric row R-SEV2-05 ("scheduled job double-fires
OR misses a scheduled run").

**Edge cases accepted**:
- A reconcile job that only emits a Slack summary (no financial side
  effect, no compliance deadline) remains SEV-3.
- A cron expressed in UTC (e.g. `0 0 * * *` zone=UTC) is not a finding
  — no DST-skip applies.
- Quartz with `cronExpression` and `timeZone="Europe/Rome"` exhibits the
  same DST-skip; the pattern fires regardless of scheduler library.
