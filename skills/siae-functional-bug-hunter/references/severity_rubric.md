# Severity rubric

Every finding emitted in `qa_report.json` / `qa_report.md` is assigned
exactly one severity tier from the unified taxonomy below. The
assignment cites **the row id** of the rubric in the
`severity_rubric_row` field (this citation is mandatory — phase 7
rejects findings that do not cite a row).

**Inter-rater agreement target**: Cohen's κ ≥ 0.7 between two
independent reviewers on the golden set in `../eval/golden_set/`. The
calibration loop in `lifecycle_playbook.md` is responsible for keeping
this number above 0.7 quarter over quarter.

## Unified taxonomy — SEV-N

There is **one** taxonomy: `SEV-1` / `SEV-2` / `SEV-3` / `SEV-4`. This is
the only set of values that appears in `qa_report.json:findings[].severity`
(per the JSON Schema in `qa_report_json_schema.md`) and in the
`SubagentResult.Finding.severity` field (per `subagent_contract.md`).

| SEV  | Definizione operativa | SLA risposta |
|------|-----------------------|--------------|
| SEV-1 | Data loss, auth bypass, sicurezza; blocca release | Immediato |
| SEV-2 | Funzionalità core non disponibile per >10% utenti; workaround assente | 24h |
| SEV-3 | Degradazione funzionalità, workaround possibile ma oneroso | 72h |
| SEV-4 | UX degradata, edge case, nessun impatto su flusso critico | Next sprint |

A finding NEVER occupies more than one tier. When two rows could apply,
the **higher tier wins** (SEV-1 > SEV-2 > SEV-3 > SEV-4).

## Decision rows

The row id has the form `R-SEV<n>-<NN>`. Phase 7 cites this id verbatim.

### SEV-1

| Row id | Trigger |
|---|---|
| R-SEV1-01 | Persisted user data is overwritten without the user's action OR is lost on retry. |
| R-SEV1-02 | A user can authenticate as another user OR access a resource explicitly owned by another user, and > 10% of users are exposed (e.g. shared signed URL, predictable session id, missing tenant scoping). |
| R-SEV1-03 | A financial side effect (charge, refund, payout) is duplicated OR omitted due to retry / partial failure; > 10% of transactions affected. |
| R-SEV1-04 | An IaC change removes a route / permission / queue that breaks a production user journey for > 10% of users. |
| R-SEV1-05 | Database state becomes inconsistent across tables that must commit together; recovery requires manual intervention. |

### SEV-2

| Row id | Trigger |
|---|---|
| R-SEV2-01 | A documented user workflow is blocked on the happy path; user can use a manual workaround (page reload, retry, alternate endpoint). |
| R-SEV2-02 | Authorization is inverted on a specific resource type; > 1% of users affected. |
| R-SEV2-03 | A side effect is duplicated under retry / double-click; manual reconciliation is possible. |
| R-SEV2-04 | Sensitive data leakage (stack trace with internal hostnames, another user's email in an error response) on a path that real users can reach. |
| R-SEV2-05 | A scheduled job double-fires OR misses a scheduled run, producing user-visible inconsistency. |
| R-SEV2-06 | A long-running operation overwrites user input made concurrently (loss of edit). |
| R-SEV2-07 | TOCTOU on authorization: permissions verified once at start of a multi-step flow are not re-checked mid-flow; revoked tokens still complete the action. |

### SEV-3

| Row id | Trigger |
|---|---|
| R-SEV3-01 | Pagination skips or duplicates items at page boundaries (cursor drift on non-totally-ordered sort). |
| R-SEV3-02 | Timezone display is wrong for users outside the server's TZ. |
| R-SEV3-03 | Locale formatting (currency, date, number) inverted between display and persisted value. |
| R-SEV3-04 | A 500 / unhandled exception on an edge input (empty, null, large) that a real user can submit. |
| R-SEV3-05 | UI shows success state but the server rejected the action; reconciliation requires reload. |
| R-SEV3-06 | Feature flag mismatch shows a button that doesn't work. |
| R-SEV3-07 | Broken back-button loses unsaved form data. |
| R-SEV3-08 | Race window on infrequent shared state (e.g. concurrent admin actions). |
| R-SEV3-09 | Cache staleness: write endpoint does not invalidate CDN / Redis / Service Worker layer; users see obsolete data until TTL expires. |
| R-SEV3-10 | DST scheduler skip: cron expression on local-time hour that does not exist on DST transition day; the job is silently skipped. |

### SEV-4

| Row id | Trigger |
|---|---|
| R-SEV4-01 | Cosmetic glitch (overflow, alignment, color, copy) that does not block a workflow. |
| R-SEV4-02 | An edge case in a rarely-used administrative path (frequency < 0.01%). |
| R-SEV4-03 | A log line truncates user-visible information that is also available in the UI. |
| R-SEV4-04 | An accessibility / i18n gap that does not block a workflow (note: accessibility audits are out of scope; this row only applies when the gap is discovered incidentally during functional analysis). |

## Severity assignment algorithm (phase 7)

For each surviving hypothesis after phase 6, phase 7 executes the
following deterministic procedure:

1. Compute the **functional manifestation tier** from the bug-pattern
   row (BP-XYZ has a `severity_hint`).
2. Compute the **user-base modifier**:
   - If the entry point is on a critical path (per the SKILL.md
     definition), keep tier or **escalate by one** if the data class
     is financial / auth / PII.
   - If the entry point is rarely reached (no caller signal in the
     dependency closure, gated by an admin role, behind a feature
     flag that is off in default config), **demote by one** unless
     the tier is already SEV-4.
3. Pick the lowest-numbered (highest priority) row whose **Trigger**
   text matches the functional manifestation.
4. Set `severity = row.tier`, `severity_rubric_row = row.id`.

When no row matches, phase 7 MUST NOT emit a sentinel "rubric gap" row.
Instead, the finding stays in `hypotheses.json` with status
`needs_rubric_extension` and is surfaced in `open_questions.md`. The
rubric is then extended in `references/severity_rubric.md` (minor semver
bump) and the run is re-executed. This eliminates the previous catch-all
escape hatch (the legacy SEV-3 wildcard row in v1.0.x) that was
historically abused as a dumping ground for unclassified findings.

## Worked examples

### Example 1

- Bug-pattern: BP-014 (double-submit) on `POST /v1/payments`.
- Functional manifestation: user is charged twice on double-click.
- Entry point is critical path (payment flow).
- Data class is financial → escalate one tier from `severity_hint = SEV-2`.
- BUT R-SEV1-03 requires > 10% of transactions affected; evidence shows
  the issue is reachable from a publicly-exposed button but only triggers
  on actual double-clicks (< 10% in practice) → cap at R-SEV2-03.
- **Result**: `severity = SEV-2`, `severity_rubric_row = R-SEV2-03`.

### Example 2

- Bug-pattern: BP-008 (timezone-locale-bug) on a calendar view.
- Functional manifestation: users outside CET see Sunday events on
  Monday.
- Entry point is `ui-screen`, frequently reached.
- **Result**: `severity = SEV-3`, `severity_rubric_row = R-SEV3-02`.

### Example 3

- Bug-pattern: BP-001 (input-validation-gap) on an admin-only endpoint
  for renaming a tenant.
- Functional manifestation: admin can submit a 10 000-char name; UI
  shows truncated value; persisted value is full length.
- Entry point is admin-only (rarely reached) → demote one tier from
  SEV-2.
- **Result**: `severity = SEV-3`, `severity_rubric_row = R-SEV3-04`.

## Sentinel anti-patterns

These three examples teach what NOT to do. They are the most frequent
classification errors observed in the golden set and are the primary
levers for keeping κ ≥ 0.7.

### Anti-pattern A — escalating UX glitch to SEV-2

**Wrong**: a missing button label is classified `SEV-2 / R-SEV2-01`
because "the workflow is blocked" (the tester could not find the button).

**Correct**: this is a cosmetic glitch → `SEV-4 / R-SEV4-01`. The button
still works when clicked via keyboard; the workflow is not blocked, only
the discovery is impaired.

### Anti-pattern B — demoting auth bypass on rare path

**Wrong**: a tenant-isolation bypass on an admin-only endpoint is
classified `SEV-3 / R-SEV3-08` ("race window on infrequent shared
state") because admins rarely use it.

**Correct**: auth bypass is `SEV-1 / R-SEV1-02` regardless of frequency.
The rarity modifier in step 2 of the algorithm explicitly does NOT
apply when the data class is auth — that is a hard floor.

### Anti-pattern C — using "other" category for known patterns

**Wrong**: a webhook handler that does not deduplicate events is
classified with category `other` and SEV-3 because the reviewer did not
recognize the pattern.

**Correct**: this is `category = webhook-replay`, pattern `BP-019`, and
severity follows the BP-019 mapping (typically SEV-2 unless the
downstream side effect is financial, in which case SEV-1). Choosing
`other` is a signal that pattern recognition failed; the reviewer must
revisit the bug pattern catalog before classifying.

## Calibration

The κ ≥ 0.7 target is monitored quarterly via `../eval/metrics.md`. When
κ drops below 0.7, the lifecycle playbook triggers a rubric review:
ambiguous rows are split, conflicting rows are merged, and the golden
set is re-labelled. Rubric changes are a **minor** semver bump unless
they reclassify existing findings (then **major**).

### Escalation Rule — moduli sensibili (floor SEV-2)

I moduli che toccano i seguenti domini hanno severity minima automatica
SEV-2 — non possono essere declassati senza approvazione esplicita:

| Dominio              | Segnali nel codice                                             |
|----------------------|----------------------------------------------------------------|
| Diritti d'autore     | `diritti`, `royalty`, `compenso`, `ripartizione`, `quota`     |
| Mandati              | `mandato`, `mandante`, `rappresentanza`, `delega`              |
| Dati finanziari      | `iban`, `bonifico`, `fattura`, `quietanza`, `saldo`            |
| PII / dati personali | `cf`, `codice_fiscale`, `pii`, `gdpr`, `anagrafica`            |

### Exit Codes — Strict Mode

Attivato da `--strict` o `FBH_STRICT=1`. Gestisce anche il run.lock
(`.fbh/run.lock`) per prevenire esecuzioni concorrenti.

| Code | Condizione                                          |
|------|-----------------------------------------------------|
| `0`  | Nessun finding SEV-1 o SEV-2                        |
| `1`  | Almeno 1 finding SEV-1, zero SEV-2                  |
| `2`  | Almeno 1 finding SEV-2 (indipendentemente da SEV-1) |

In modalità non-strict il processo termina sempre con `0`.
