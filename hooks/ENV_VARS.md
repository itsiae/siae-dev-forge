# DevForge Hooks — Environment Variables

Reference for all environment variables that control hook behaviour.
Bypass vars are tracked and log `*_abuse_suspected` when used >= 5 times
in a single UTC day (3× for `DEVFORGE_FORCE_STOP`).

## Global

| Env var | Default | Introduced | Description |
|---|---|---|---|
| `DEVFORGE_ENFORCEMENT_OFF` | `0` | v1.45 | Disable **all** gates. Exit `{}` on every invocation. |
| `DEVFORGE_USE_SESSION_SCOPE` | `0` | **v1.47 (PR #2)** | Rollback switch. Restores session-scoped enforcement for every task-scoped gate (tdd, brainstorming, stop, pre-commit, pr-blind-review, plan-gate-write). Set for an entire shell if task-scope enforcement misbehaves. |

## Per-gate bypass (tracked)

| Env var | Default | Gate | Abuse threshold | Notes |
|---|---|---|---|---|
| `DEVFORGE_SKIP_BRAINSTORMING` | `0` | brainstorming-gate | 5 / day | Emits `brainstorming_bypass_abuse_suspected` on threshold. |
| `DEVFORGE_SKIP_GIT_GATE` | `0` | pre-commit (git-workflow check) | 5 / day | Emergency bypass introduced to unblock users affected by the session-skills reset bug. |
| `DEVFORGE_SKIP_RETRO_GATE` | `0` | stop-gate (retrospective) | — | For non-interactive CI/agent sessions. |
| `DEVFORGE_SKIP_BLIND_REVIEW` | `0` | pr-blind-review-gate | 5 / day | **v1.47 NEW.** Allows `gh pr create` / `gh pr edit` without siae-blind-review validation. |
| `DEVFORGE_FORCE_STOP` | `0` | stop-gate (verification) | **3 / day** | **v1.47 NEW.** Explicit replacement for the old 2-block auto-escape (ADR-006). Lower threshold because Stop is high-impact. |

## Scope / feature flags

| Env var | Default | Gate | Description |
|---|---|---|---|
| `DEVFORGE_BASH_TDD` | `0` | tdd-gate (via file-taxonomy) | **v1.47 NEW.** Opt-in TDD gating for `.sh` / `.bash` files. Deny-by-default keeps DevForge's own hooks from locking themselves. |

## Removed in v1.47 (PR #2)

| Env var | Why removed |
|---|---|
| `DEVFORGE_W2_DEFAULT` | Replaced by always-on enforcement (ADR-006). Old `W2_DEFAULT=0` was a no-op that diluted the gate to zero effect. |
| `DEVFORGE_ENFORCEMENT_STRICT` | Superseded by always-on enforcement. Reading it is now ignored. |

## Rollout and rollback

Task-scoped enforcement (ADR-001) runs in dual-write mode: every hook still
reads the legacy `~/.claude/.devforge-session-skills` in addition to the
task-keyed ledger at `~/.claude/.devforge-task-skills/<task_id>/`.

- Per-gate rollback: set `DEVFORGE_USE_SESSION_SCOPE=1` in the shell that
  exhibits the problem. The gate will skip the task-id layer entirely and
  behave identically to v1.46.
- Global rollback: `DEVFORGE_ENFORCEMENT_OFF=1` (pre-existing).
- Hard revert: `git revert <PR #2 merge commit>`.

## Abuse-tracking data files

These files are rewritten atomically by the hooks; they are safe to delete
to reset counters.

| File | Written by | Purpose |
|---|---|---|
| `~/.claude/.devforge-bypass-count` | brainstorming-gate | Daily bypass counter |
| `~/.claude/.devforge-git-gate-bypass-count` | pre-commit | Daily bypass counter |
| `~/.claude/.devforge-blind-review-bypass-count` | pr-blind-review-gate | Daily bypass counter |
| `~/.claude/.devforge-force-stop-count` | stop-gate | Daily force-stop counter |

## Plugin root resolution

| Env var | Source | Description |
|---|---|---|
| `CLAUDE_PLUGIN_ROOT` | Iniettata da Claude Code nell'env del processo hook | Path assoluto della directory installata del plugin (es. `~/.claude/plugins/cache/siae-devforge/siae-devforge/<version>`). Da NON valorizzare nel plugin: e' responsabilita' dell'harness. |

### Convenzione quoting in `hooks.json`

Il pattern canonico per riferire `${CLAUDE_PLUGIN_ROOT}` in `hooks.json` usa double-quotes JSON-escaped:

**JSON source** (sorgente con escape):

```json
"command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start"
```

**Stringa ricevuta da bash dopo parse JSON dall'harness**:

```
bash "${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" session-start
```

Le double-quote (escaped come `\"` nel JSON source) sono **necessarie** per consentire a bash di espandere `${CLAUDE_PLUGIN_ROOT}` iniettata dall'harness. Single quotes bloccherebbero l'espansione e l'hook fallisce con `bash: ${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd: No such file or directory`.

Regola enforced da `tests/hooks/hooks-json-var-expansion.test.sh`.
