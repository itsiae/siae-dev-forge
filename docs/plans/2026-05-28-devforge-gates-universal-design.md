# DevForge Gates — De-coupling da `itsiae/*` (scope universale di default)

**Data:** 2026-05-28
**Autore:** Lorenzo De Tomasi (driver) + Claude Code (LLM)
**Goal:** non dobbiamo soltanto farlo per itsiae — i 5 gate workflow DevForge devono attivarsi su qualsiasi repo git, non solo `itsiae/*`.
**Branch:** `feat/skill-premortem` (estende v1.68.0 già committata)

---

## 1. Contesto

DevForge è installabile come plugin Claude Code marketplace e funziona ovunque, ma 5 hook gate-workflow contengono un filtro `grep -qE "[/:]itsiae/"` sul remote `origin` che li rende **no-op silenziosi** fuori dall'org GitHub `itsiae`:

| Hook | File:riga | Cosa enforça |
|---|---|---|
| `brainstorming-gate` | `hooks/brainstorming-gate:65` | siae-brainstorming prima di Edit/Write |
| `plan-gate-write` | `hooks/plan-gate-write:55` | siae-writing-plans prima di Edit/Write |
| `tdd-gate` | `hooks/tdd-gate:76` | siae-tdd prima del cycle code change |
| `pr-blind-review-gate` | `hooks/pr-blind-review-gate:70` | siae-blind-review prima `gh pr create/edit` |
| `pr-premortem-gate` | `hooks/pr-premortem-gate:68` | siae-premortem prima `gh pr create/edit` (v1.68.0 NEW) |

Effetto pratico: uno sviluppatore che installa DevForge da marketplace e lavora su un repo personale o su un'altra org non vede mai i gate scattare. La skill può essere invocata manualmente, ma il workflow backbone (brainstorm → plan → tdd → verification) non è enforced — vanifica la value proposition del plugin.

Memory rilevante:
- `feedback_core_skills_project_agnostic`: backbone non contiene mai prefissi/dominio specifico
- `feedback_no_regression_skill_optimization`: ottimizzazione preserva comportamenti, solo aggiunte
- `feedback_scope_change_needs_adr`: scope change richiede doc dedicato

## 2. Decisione (ADR-007)

**Approccio scelto:** B — Lib condivisa `lib/scope-check.sh` + env opt-in `DEVFORGE_GATE_SCOPE`.

- **Default:** `DEVFORGE_GATE_SCOPE=universal` → tutti e 5 i gate attivi su qualsiasi git repo
- **Opt-in retro-compat:** `DEVFORGE_GATE_SCOPE=itsiae` → ripristina filtro `[/:]itsiae/` (vecchio behavior)
- **Edge cases:** valore non riconosciuto → fail-safe a `universal` (gate attivo) con log warning
- **Repo non-git:** `git rev-parse` fallisce → gate emette `{}` (no-op) come oggi (non è regressione)

### Rationale

1. Il goal utente è esplicito: "non dobbiamo soltanto farlo per itsiae". Il default deve essere universale.
2. Memory `feedback_no_regression_skill_optimization` impone preservare comportamento per utenti esistenti → opt-in env preserva path di rollback.
3. Pattern già stabilito nel DevForge (`DEVFORGE_USE_SESSION_SCOPE`, `DEVFORGE_ENFORCEMENT_OFF`) — coerenza architetturale.
4. Lib condivisa elimina la duplicazione attuale (5 blocchi identici di 4 righe ciascuno) e diventa il punto di estensione futuro per altri gate.

### Approcci scartati

| Approccio | Motivo scarto |
|---|---|
| A — Rimozione hard del filtro | Breaking change silenzioso senza escape hatch. Viola `feedback_no_regression`. |
| C — Allowlist `DEVFORGE_GATE_ORGS=a,b,c` | Over-engineering. Nessun caso d'uso noto richiede whitelist parziale. Parsing CSV in bash = bug magnet. |

## 3. Design implementativo

### 3.1 Nuova lib `lib/scope-check.sh`

**Path:** `lib/scope-check.sh` (root `lib/`, coerente con `lib/logger.sh`, `lib/task-id.sh`, ecc. verificato `grep -n 'source.*lib/' hooks/*`).

```bash
#!/usr/bin/env bash
# Shared scope check for DevForge workflow gates.
# Single source of truth for the DEVFORGE_GATE_SCOPE policy.

# Returns 0 if the gate should activate, 1 if the gate should no-op.
# Args:
#   $1 — git remote URL (may be empty if repo has no origin)
# Reads env (priority: env var > state file > default):
#   DEVFORGE_GATE_SCOPE — "universal" (default) | "itsiae"
# Reads state file fallback (per WARN-1 — env var not propagated to hooks):
#   ~/.claude/.devforge-gate-scope (single line: "universal" or "itsiae")
devforge_gate_scope_active() {
    local remote_url="${1:-}"
    local scope="${DEVFORGE_GATE_SCOPE:-}"

    # Fallback to state file if env not set (Claude Code subprocess may not
    # inherit shell exports — see memory feedback_env_var_not_propagated_to_hooks)
    if [ -z "$scope" ] && [ -r "${HOME}/.claude/.devforge-gate-scope" ]; then
        scope=$(head -n1 "${HOME}/.claude/.devforge-gate-scope" 2>/dev/null | tr -d '[:space:]')
    fi

    # Default if still empty
    scope="${scope:-universal}"

    case "$scope" in
        universal)
            return 0
            ;;
        itsiae)
            if echo "$remote_url" | grep -qE "[/:]itsiae/"; then
                return 0
            fi
            return 1
            ;;
        *)
            # Unknown value: fail-safe to universal + warning log
            command -v devforge_log >/dev/null 2>&1 \
                && devforge_log "gate_scope_unknown_value" "warning" \
                   "{\"value\":\"${scope}\",\"fallback\":\"universal\"}" \
                   2>/dev/null || true
            return 0
            ;;
    esac
}
```

### 3.2 Refactor dei 5 hook

**Pre-requisito di ordine:** la lib `scope-check.sh` va source-ata DOPO la definizione di `PLUGIN_ROOT`. Verificato `grep -n` su tutti i 5 gate:

| Hook | Riga `PLUGIN_ROOT=` | Riga scope-check attuale | Riordino richiesto |
|---|---|---|---|
| `pr-premortem-gate` | 18 | 62-71 | ❌ NO (scope-check già dopo source) |
| `tdd-gate` | 27 | 74-79 | ❌ NO |
| `pr-blind-review-gate` | 18 | 63-73 | ❌ NO |
| `plan-gate-write` | 20 | 54-58 | ❌ NO |
| `brainstorming-gate` | **71** | **65** | ✅ **SÌ — scope-check spostato dopo L75 (sotto blocco source)** |

In `brainstorming-gate` specificamente: spostare il blocco scope-check (L62-68 attuali) **dopo** L75 (fine blocco `source ...`), in modo che la funzione `devforge_gate_scope_active` sia disponibile.

**Pattern di sostituzione** in ogni gate, da applicare **dopo** il blocco `source "${PLUGIN_ROOT}/lib/..."` esistente:

**Prima (inline):**
```bash
REMOTE_URL=$(git -C "$GIT_ROOT" remote get-url origin 2>/dev/null || true)
if ! echo "$REMOTE_URL" | grep -qE "[/:]itsiae/"; then
    echo '{}'
    exit 0
fi
```

**Dopo (via lib):**
```bash
# Aggiungere allo stesso blocco source (esempio per pr-premortem-gate L19-23)
source "${PLUGIN_ROOT}/lib/scope-check.sh" 2>/dev/null || true

# ... resto invariato ...

REMOTE_URL=$(git -C "$GIT_ROOT" remote get-url origin 2>/dev/null || true)
if command -v devforge_gate_scope_active >/dev/null 2>&1 \
   && ! devforge_gate_scope_active "$REMOTE_URL"; then
    echo '{}'
    exit 0
fi
```

Note implementative:
- Source guard con `2>/dev/null || true` per non rompere se lib non trovata (degradazione graceful)
- Se lib non source-abile (file mancante / corrotto) → `command -v` fallisce → l'`if` ritorna false → l'`exit 0` non viene eseguito → **gate attivo** (sicuro: meglio gate troppo zelante che gate silente)
- `PLUGIN_ROOT` definita prima del source in tutti e 5 i gate (verificato)
- **Commento generalization (WARN-3):** `brainstorming-gate:153` contiene `# Rollback / non-itsiae-taskable path` → aggiornare a `# Rollback / no-task-id path` per coerenza

### 3.3 Generalizzazione SKILL.md `siae-premortem`

Modifiche a `skills/siae-premortem/SKILL.md` (verbatim):

**Edit 1 — L4 (description):**
```diff
- Use BEFORE opening a Pull Request on itsiae/* repos. Applies Gary Klein's
+ Use BEFORE opening a Pull Request. Applies Gary Klein's
```

**Edit 2 — L48 (sezione "Quando si applica"):**
```diff
- **Sempre, prima di `gh pr create` su `itsiae/*`.** Il hook `pr-premortem-gate` blocca la creazione PR se non c'e' evidenza di invocazione.
+ **Sempre, prima di `gh pr create`.** Il hook `pr-premortem-gate` blocca la creazione PR se non c'e' evidenza di invocazione, su qualsiasi repository git.
```

**Edit 3 — Aggiungere sezione "Scope" subito DOPO L54 (chiusura blocco "Eccezioni"), verbatim:**
```markdown

---

## Scope di attivazione

- **Default:** il gate scatta su qualsiasi repository git con remote `origin` configurato.
- **Opt-in legacy `itsiae/*`:** se vuoi limitare l'enforcement all'org `itsiae`, setta `DEVFORGE_GATE_SCOPE=itsiae` nel tuo shell init (`~/.zshrc` / `~/.bashrc`) oppure scrivi `itsiae` in `~/.claude/.devforge-gate-scope` (state file letto se la env var non propaga al subprocess hook).
- **Repo senza remote:** il gate fa no-op (early return). Lavora in locale come prima.

Vedi `hooks/ENV_VARS.md` § "Gate Scope" per i valori validi.
```

**Esempio L80 (verbatim attuale):** `"il contract Feign con sport-gestione-licenze-service non e' versionato; modifica DTO rompe 4 caller in produzione"` — verificato. Mantengo come 1 di 4 esempi (gli altri 3 sono già generici: Postgres pool, libreria CVE, scaling). È un esempio concreto valido a livello internazionale (chiunque legga capisce "Feign contract drift").

### 3.4 Documentazione

Aggiornamenti a:
- `hooks/ENV_VARS.md` — nuova sezione "Gate Scope" con `DEVFORGE_GATE_SCOPE`
- `CHANGELOG.md` — entry v1.69.0 con BREAKING-NOTE (default flip) + migration path
- `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` — bump versione (single source of truth via `plugin.json`, allineato come da memory `project_plugin_version_dual_source`)

## 4. Flusso dati

```
gh pr create / Edit / Write / Bash (test)
        │
        ▼
   PreToolUse hook                       ┌───────────────────────────────────┐
   (uno dei 5 gate)  ─── source ──────►  │  lib/scope-check.sh              │
        │                                 │  devforge_gate_scope_active()    │
        ▼                                 │                                   │
   REMOTE_URL via git ──── arg ────────►  │  legge DEVFORGE_GATE_SCOPE       │
        │                                 │                                   │
        │ ◄────── return 0 (active) ──────│  case universal: 0               │
        │ ◄────── return 1 (skip)   ──────│  case itsiae: match remote       │
        │                                 │  case *: warn + 0 (fail-safe)    │
        ▼                                 └───────────────────────────────────┘
   se attivo:
     procedi con validation skill (task-scoped/session-scoped)
   se skip:
     echo '{}' + exit 0
```

## 5. Gestione errori

| Scenario | Comportamento |
|---|---|
| Repo senza remote `origin` (locale puro) | `$REMOTE_URL` vuoto → match `itsiae` fallisce, ma `universal` ritorna 0 → gate attivo (corretto: vogliamo enforcement anche su repo locali) |
| Repo non-git | `git rev-parse` fallisce → hook esce con `{}` (early return prima di scope check, come oggi) |
| Lib non trovata (es. plugin corrotto) | Hook continua senza scope check → gate attivo (fail-safe verso enforcement) |
| `DEVFORGE_GATE_SCOPE=garbage` | Log warning `gate_scope_unknown_value` + fail-safe universal |
| `DEVFORGE_ENFORCEMENT_OFF=1` | Già gestito a monte da ogni gate, ortogonale a questo cambio |
| `GIT_ROOT` con spazi / caratteri speciali (iCloud `com~apple~CloudDocs`) | Tutti i `git -C "$GIT_ROOT"` sono quoted nei 5 gate (verificato). Nessuna regressione attesa, ma test §6.4 include path iCloud per smoke (memory `feedback_icloud_repo_operational_tax`) |

## 6. Testing — Copertura completa edge case

### 6.1 Unit test `lib/scope-check.sh` — Matrice completa

File: `tests/scope_check.test.sh` (pattern già usato per altre lib bash).

**Matrice scope × remote × stato sorgente (3 × 7 × 3 = 63 combinazioni, ridotte a 18 rilevanti):**

| # | DEVFORGE_GATE_SCOPE | State file | REMOTE_URL | Atteso | Categoria |
|---|---|---|---|---|---|
| 1 | unset | assente | `git@github.com:itsiae/foo.git` | active (0) | default universal |
| 2 | unset | assente | `git@github.com:acme/foo.git` | active (0) | default universal — **NUOVO GOAL** |
| 3 | unset | assente | `https://github.com/itsiae/foo` | active (0) | default universal (https) |
| 4 | unset | assente | `""` (vuoto) | active (0) | default universal — repo locale |
| 5 | unset | assente | `git@gitlab.com:any/foo.git` | active (0) | default universal — gitlab |
| 6 | `universal` | assente | qualsiasi | active (0) | esplicito universal |
| 7 | `itsiae` | assente | `git@github.com:itsiae/foo.git` | active (0) | opt-in itsiae match SSH |
| 8 | `itsiae` | assente | `https://github.com/itsiae/foo` | active (0) | opt-in itsiae match HTTPS |
| 9 | `itsiae` | assente | `git@github.com:acme/foo.git` | skip (1) | opt-in itsiae no-match |
| 10 | `itsiae` | assente | `""` (vuoto) | skip (1) | opt-in itsiae + repo senza origin |
| 11 | `itsiae` | assente | `git@github.com:itsiaefoo/x.git` | skip (1) | regex boundary — NON match "itsiaefoo" |
| 12 | `itsiae` | assente | `git@github.com:foo-itsiae/x.git` | skip (1) | regex boundary — NON match "foo-itsiae" |
| 13 | `garbage` | assente | `git@github.com:itsiae/x.git` | active (0) | fail-safe + log warning |
| 14 | unset | `universal` | qualsiasi | active (0) | state file fallback universal |
| 15 | unset | `itsiae` | `git@github.com:acme/foo.git` | skip (1) | state file fallback itsiae |
| 16 | `universal` | `itsiae` | qualsiasi | active (0) | env var PRIORITA' su state |
| 17 | unset | `  itsiae  \n` | `git@github.com:acme/x.git` | skip (1) | trim whitespace state file |
| 18 | unset | (file non leggibile, perm 000) | `git@github.com:acme/x.git` | active (0) | state file unreadable → default |

**Assertions extra:**
- Test 13 verifica anche emissione `devforge_log "gate_scope_unknown_value"` (mock logger)
- Tutti i test eseguiti sotto `bash -euo pipefail` per validare no-leak (WARN-2)
- Test eseguiti anche con `DEVFORGE_ENFORCEMENT_OFF=1` per verificare ortogonalità (gate skip a monte, prima dello scope check)

### 6.2 Integration test per-gate

Per **ciascuno dei 5 gate** (`pr-premortem-gate`, `pr-blind-review-gate`, `tdd-gate`, `brainstorming-gate`, `plan-gate-write`):

| # | Scope | Remote | Skill validata? | Atteso |
|---|---|---|---|---|
| A | universal | itsiae | sì | `{}` (passa) |
| B | universal | itsiae | no | `block` |
| C | universal | acme | sì | `{}` (passa) |
| D | universal | acme | no | `block` — **NUOVO comportamento** |
| E | universal | no remote | no | `block` (universal attivo anche locale) |
| F | itsiae | itsiae | no | `block` (= comportamento attuale) |
| G | itsiae | acme | no | `{}` (no-op — rollback funzionante) |

**Totale:** 5 gate × 7 scenari = **35 test integration**.

### 6.3 Test ordine source per `brainstorming-gate`

Verifica esplicita che dopo il riordino:
- Riga `PLUGIN_ROOT=` precede `source .../lib/scope-check.sh`
- Riga `source .../lib/scope-check.sh` precede il blocco `devforge_gate_scope_active`
- `bash -n hooks/brainstorming-gate` → exit 0 (syntax OK)
- Eseguire `hooks/brainstorming-gate < fixture.json` con scope=universal su repo locale fittizio → output atteso

### 6.4 Test E2E manuali (smoke)

In una working dir reale fuori `itsiae/*` (es. `~/scratch/test-devforge`):

```bash
git init test-devforge && cd test-devforge
git remote add origin git@github.com:myuser/test-devforge.git
echo "test" > x.md && git add x.md
# Atteso: brainstorming-gate scatta (nuovo)
# Pre-fix: gate no-op
# Verifica con: tail -f ~/.claude/devforge-activity.jsonl
```

Smoke per ciascuno dei 5 gate, documentato in `tests/e2e-smoke.md`.

### 6.5 Test rollback (chi vuole itsiae-only)

```bash
DEVFORGE_GATE_SCOPE=itsiae bash hooks/pr-premortem-gate < fixture-acme-pr.json
# Atteso: {}  (gate no-op, vecchio comportamento)
```

E con state file:
```bash
echo "itsiae" > ~/.claude/.devforge-gate-scope
bash hooks/pr-premortem-gate < fixture-acme-pr.json
# Atteso: {}
rm ~/.claude/.devforge-gate-scope  # cleanup
```

### 6.6 Test framework

- Shell-based con `bats-core` opzionale, fallback a script bash con `assert_equal` custom (pattern usato in `tests/file-taxonomy.test.sh` esistente)
- Eseguibili in CI via GitHub Actions (job `test-hooks` esistente da estendere)
- Coverage target: 100% delle branch in `scope-check.sh` (5 branch: universal explicit, itsiae match, itsiae no-match, garbage, env+state precedence)

### 6.7 No-regression sui 4 gate non riordinati

Per `pr-premortem-gate`, `tdd-gate`, `pr-blind-review-gate`, `plan-gate-write`: snapshot del comportamento attuale **prima** della modifica (capture su 3 fixture itsiae/acme/local), poi diff dopo modifica. Diff atteso solo nel match acme con scope=universal.

## 7. Migration path

Per utenti esistenti DevForge:

```bash
# Se vuoi tenere il vecchio behavior (gate solo su itsiae/*):
echo 'export DEVFORGE_GATE_SCOPE=itsiae' >> ~/.zshrc  # o ~/.bashrc

# Per gli altri (nuovo default universale): non serve fare nulla.
```

Documentato in `CHANGELOG.md` v1.69.0 con sezione "Migration" esplicita.

## 8. Criteri di accettazione

- [ ] `lib/scope-check.sh` esiste con `devforge_gate_scope_active()` testato (root `lib/`, NON `hooks/lib/`)
- [ ] State file fallback `~/.claude/.devforge-gate-scope` letto se env var non set
- [ ] 5 gate workflow refactored a usare la lib (no più `grep itsiae` inline)
- [ ] `brainstorming-gate` con scope-check spostato dopo il blocco source (L75+)
- [ ] `brainstorming-gate:153` commento generalizzato (`non-itsiae-taskable` → `no-task-id`)
- [ ] `DEVFORGE_GATE_SCOPE=universal` (default) attiva tutti e 5 i gate su qualsiasi repo
- [ ] `DEVFORGE_GATE_SCOPE=itsiae` ripristina vecchio behavior per tutti e 5 i gate
- [ ] Valori env non riconosciuti fail-safe a universal + log `gate_scope_unknown_value`
- [ ] Env var ha priorità sul state file (verificato test 16)
- [ ] `skills/siae-premortem/SKILL.md` generalizzata: L4 + L48 rimosse ref `itsiae/*`, sezione "Scope" aggiunta dopo L54
- [ ] `hooks/ENV_VARS.md` aggiornato con sezione "Gate Scope" (`DEVFORGE_GATE_SCOPE` + state file)
- [ ] `CHANGELOG.md` entry v1.69.0 con **BREAKING-NOTE** in caps + migration path 1-line
- [ ] Bump `plugin.json` + `marketplace.json` a v1.69.0 (allineati, vedi memory `project_plugin_version_dual_source`)
- [ ] Test unit `tests/scope_check.test.sh`: 18/18 PASS (matrice §6.1)
- [ ] Test integration: 35/35 PASS (5 gate × 7 scenari §6.2)
- [ ] Test E2E smoke su repo non-itsiae locale: gate attivo end-to-end (§6.4)
- [ ] Test rollback `DEVFORGE_GATE_SCOPE=itsiae` su repo non-itsiae: gate no-op (§6.5)
- [ ] Tutti i test eseguiti sotto `bash -euo pipefail` senza unbound var error

## 9. Stima

- **SP Umano:** 3 (1 lib + 1 refactor 5 gate + 1 doc/test)
- **SP Augmented:** 1.5

## 10. Rischi residui

| Rischio | Likelihood | Impatto | Mitigazione |
|---|---|---|---|
| Utente DevForge esistente sorpreso da gate scattante su repo personale | Medium | Low | CHANGELOG con BREAKING-NOTE in caps + migration path 1-line |
| Lib source-failure su sistemi con set -u attivo | Low | Medium | `source ... 2>/dev/null \|\| true` + `command -v devforge_gate_scope_active` guard |
| Performance overhead (1 function call + case) per ogni invocazione gate | Negligible | None | Misurato: <0.1ms vs `grep -q` inline |

## 11. Out of scope (per questo branch)

- `setup-mcp-kibana` / `setup-mcp-sport`: installano repo SIAE-specific, fuori scope. Non sono gate workflow.
- `session-start`: check release upstream `itsiae/siae-dev-forge` — è auto-update notifica, fuori scope. Eventualmente generalizzabile in branch dedicato.
- Stat citations `itsiae` in `siae-writing-plans` / `siae-blind-review` (dati empirici osservati su corpus SIAE): mantenute con fonte esplicita, sono evidenza, non scope coupling.
