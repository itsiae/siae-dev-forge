---
status: draft
owner: Lorenzo De Tomasi
created: 2026-04-22
topic: Progressive enforcement del brainstorming per adoption 3.3% → 50%+ in 30g
---

# Brainstorming Enforcement — Progressive Friction Hook

## Contesto

Dati reali 2026-04-22 (`~/Downloads/devforge-eventi-2026-04-22.csv`, 500 eventi in 15h):

- **Adoption brainstorming: 3.3%** (3 dev su 91)
- Eventi plan lifecycle: 42 totali, **tutti da un singolo dev** (lodetomasi)
- 88 dev su 91 aprono Edit/Write senza mai invocare `siae-brainstorming`
- Effetto: KPI Rosario K1/K2 statisticamente inutilizzabili (campione 3)

Root cause tecnica: `hooks/tdd-gate` blocca Edit/Write senza `siae-tdd`, ma la catena prerequisiti in `hooks/sub-skill-gate:37-45` **non richiede** `siae-tdd → siae-brainstorming`. Quindi dev invoca solo TDD e bypassa brainstorming.

## Obiettivo

Portare adoption brainstorming da 3.3% a **≥50%** in 30 giorni, **senza cliff** che rompa workflow dei power user.

## Decisioni

**D1. Approccio: Progressive Friction via nuovo hook `brainstorming-gate`.**

Stesso pattern di `tdd-gate` (PreToolUse Edit/Write, stesso matcher, stesso logger), ma con **counter per sessione** e 3 livelli escalation.

**D2. Threshold: 1 silent → 2-3 warn → 4+ hard block.**

| Edit # senza brainstorming | Comportamento | Blocca? |
|---|---|---|
| 1 | `brainstorming_nudge_soft` in JSONL, nessun UX | No |
| 2-3 | Card WARN con "continua comunque" (1-click bypass) | No (soft block) |
| ≥4 | HARD BLOCK con messaggio + env var bypass | Sì (senza env var) |

**Counter reset: sempre SID-based** (fix [WARN] reviewer — evita fragilità `session-skills`):

Il counter file usa schema `SID|N`:

```
<session-id>|<counter>
```

Reset avviene solo quando il SID cambia (nuova sessione Claude Code → `SessionStart` hook emette nuovo SID in `devforge_init_session`).

Logic:
- `siae-brainstorming` invocato → **post-skill hook** scrive `SID|0` (reset esplicito, NON via session-skills file)
- Nuovo SID (session change) → prima read del counter trova SID diverso → reset automatico a `NEW_SID|0`
- Session-skills file `git stash`/`git checkout` → **non influenza** il counter (counter legge SID, non session-skills)

Questo evita il bug documentato in `feedback_session_skills_reset.md`: session-skills si svuota su git stash → counter spurio. Con SID come anchor, il counter resta stabile.

**D3. Scope file: `.java|.ts|.tsx|.js|.jsx|.py|.vue|.go|.kt` (stesso di tdd-gate).**

- Esclusi: IaC (`.tf`, `.hcl`), docs (`.md`), config (`.yml`, `.json`), test files
- Rationale: brainstorming è per *logica di business*, non per config change (che ha altri gate)
- **Solo repo `itsiae/` su GitHub** (stesso scope di tdd-gate — evita fork/progetti personali)

**D4. Bypass: env var `DEVFORGE_SKIP_BRAINSTORMING=1` per comando + anti-abuse detection.**

Pattern `git commit --no-verify`. Richiede **intenzionalità esplicita**:

```bash
DEVFORGE_SKIP_BRAINSTORMING=1 <qualsiasi comando che triggeri Edit>
```

- Tracciato in telemetry (`brainstorming_gate_bypassed` + `reason` opzionale via env)
- NO config permanente `~/.claude/`

**Anti-abuse detection (fix [BLOCK] reviewer):**

Nulla impedisce tecnicamente `export DEVFORGE_SKIP_BRAINSTORMING=1` in `.bashrc`/`.zshrc`. Mitigazione in 3 livelli:

1. **Counter bypass file** `$HOME/.claude/.devforge-bypass-count` con schema:
   ```
   YYYY-MM-DD|count
   ```
   Incrementato ad ogni bypass. Reset giornaliero automatico (nuovo record se data diversa).

2. **Soglia anti-abuse**: se `count > 5/giorno` per lo stesso dev, emit evento `brainstorming_bypass_abuse_suspected` con `count_today` e `estimated_pattern` (es. `"always_on"` se count ≥ 10).

3. **Control Tower dashboard**: mostra top-N dev per bypass rate giornaliero come "review candidates" al tech lead. Gestione sociale, non tecnica.

Logica: il bypass è feature legittima (fix triviali), ma l'**abuso è misurabile**. Il dev che lo setta in `.bashrc` triggera l'alert automatico → intervento umano non tool.

**D5. Deploy graduale a 2 fasi.**

| Settimana | Modalità | Default |
|---|---|---|
| W1 (pilota) | `DEVFORGE_ENFORCEMENT_STRICT=1` opt-in | OFF |
| W2+ | Default ON, `DEVFORGE_ENFORCEMENT_OFF=1` opt-out emergenza | ON |

Pilota W1 coinvolge solo power user / tech lead volontari. Feedback raccolto in retrospective settimanale.

## Architettura

### Nuovo file: `hooks/brainstorming-gate`

```
PreToolUse: Edit, Write
  ↓
Estrai FILE_PATH (come tdd-gate)
  ↓
File in scope? (prod extensions, itsiae repo, no test)
  NO → echo '{}' + exit 0 (pass-through)
  ↓
Leggi session-skills: siae-brainstorming invocato?
  SÌ → reset counter + echo '{}' + exit 0
  NO → continua ↓
  ↓
Env var DEVFORGE_SKIP_BRAINSTORMING=1?
  SÌ → log `brainstorming_gate_bypassed` + echo '{}' + exit 0
  ↓
Enforcement mode attivo?
  (W1: richiede DEVFORGE_ENFORCEMENT_STRICT=1)
  (W2+: default on, disabilitato se DEVFORGE_ENFORCEMENT_OFF=1)
  NO → log soft + echo '{}' + exit 0
  ↓
Counter file: $HOME/.claude/.devforge-brainstorm-counter
Leggi N, incrementa N+1, scrivi
  ↓
switch N:
  N=1 → log "brainstorming_nudge_soft" + echo '{}' + exit 0
  N=2,3 → decision:"block" + messaggio gentile + hint bypass
  N≥4 → decision:"block" + messaggio forte + env var bypass docs
```

### File state

- `$HOME/.claude/.devforge-brainstorm-counter` — formato `SID|N` (SID-anchored, vedi D2 reset)
- `$HOME/.claude/.devforge-bypass-count` — formato `YYYY-MM-DD|count` (anti-abuse)
- `$HOME/.claude/.devforge-session-skills` — esistente (read-only per questo hook)

**Atomic write (fix [WARN] reviewer race condition):**

Counter increment usa pattern `tmp + mv` già consolidato in `post-skill`:

```bash
NEW_VALUE="${SID}|$((CURRENT_COUNT + 1))"
echo "$NEW_VALUE" > "${COUNTER_FILE}.tmp" && mv "${COUNTER_FILE}.tmp" "$COUNTER_FILE"
```

`mv` è atomic su stesso filesystem POSIX. Edit/Write paralleli possono leggere stesso N iniziale ma la scrittura finale è deterministic (ultimo mv vince). Eventuale undercount di 1 è accettabile (peggio: 1 nudge perso su 100 edit).

### Reset counter su brainstorming invocato — `post-skill` hook

Il reset counter avviene in `hooks/post-skill` (PostToolUse Skill), **non in brainstorming-gate stesso** (che è PreToolUse Edit/Write):

```bash
# Aggiunta in hooks/post-skill, dopo il blocco di registrazione session-skills
if [ "$CLEAN_SKILL_TOKEN" = "siae-brainstorming" ]; then
    CURRENT_SID=$(devforge_get_session_id)
    echo "${CURRENT_SID}|0" > "${HOME}/.claude/.devforge-brainstorm-counter.tmp" && \
      mv "${HOME}/.claude/.devforge-brainstorm-counter.tmp" "${HOME}/.claude/.devforge-brainstorm-counter"
fi
```

Rationale: il reset deve essere side-effect di "brainstorming invocato", che è visibile solo in PostToolUse Skill. Se il reset fosse in brainstorming-gate stesso, dovremmo leggere session-skills → fragile.

### Hook registration

Nuovo entry in `hooks/hooks.json`:

```json
{
  "matcher": "Edit",
  "hooks": [
    { "type": "command", "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' tdd-gate", "timeout": 5 },
    { "type": "command", "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' brainstorming-gate", "timeout": 5 }
  ]
}
```

Stesso pattern per `Write`. **Ordine**: `tdd-gate` prima (se blocca, brainstorming-gate non gira); se passa TDD, poi brainstorming-gate. Evita doppio messaggio.

## Eventi telemetria (nuovi)

| Evento | Meta | Uso Control Tower |
|---|---|---|
| `brainstorming_nudge_soft` | `{file_path, counter:1}` | Baseline "dev inizia senza brainstorm" |
| `brainstorming_gate_warn` | `{file_path, counter:2|3}` | Quanti raggiungono il warn level |
| `brainstorming_gate_blocked` | `{file_path, counter, violation:"no_brainstorm"}` | Hard block rate |
| `brainstorming_gate_bypassed` | `{file_path, reason:"env_var"|"skip_flag"}` | Dev che aggirano l'enforcement |
| `brainstorming_invoked_post_gate` | `{trigger:"nudge"|"warn"|"block"}` | Conversion: chi invoca brainstorming DOPO un nudge |

KPI consumer (Control Tower): **conversion rate** = `count(brainstorming_invoked_post_gate) / count(brainstorming_nudge_soft)` per dev. Target: 50% entro W2.

## Messaggi card

### N=2 (warn soft)

```
⚠️ DevForge Brainstorming Nudge — 2° edit senza design

Hai modificato <file> senza invocare siae-brainstorming.
I dati mostrano che skippare il design costa 3-5x rework.

Opzioni:
  1. Invoca `Skill siae-devforge:siae-brainstorming` ora (raccomandato)
  2. Continua senza → prossimo warn al 3°, block al 4°
  3. Fix triviale? Usa: DEVFORGE_SKIP_BRAINSTORMING=1 <comando>
```

### N≥4 (hard block)

```
🔴 DevForge Brainstorming Gate — BLOCCATO

4+ edit su codice produzione senza siae-brainstorming in questa sessione.
La Legge di Ferro SIAE: nessuna implementazione senza design approvato.

Sblocca:
  Skill tool → siae-devforge:siae-brainstorming (raccomandato)

Bypass emergenza (tracciato):
  DEVFORGE_SKIP_BRAINSTORMING=1 <comando successivo>

Se pensi che questo gate sia inappropriato per il tuo task,
segnalalo a #devforge-support.
```

## Error handling

- File counter non scrivibile → skip silent (non bloccare Edit per bug hook)
- `DEVFORGE_ENFORCEMENT_OFF=1` → skip immediato (escape hatch)
- Hook timeout > 5s → skip (Claude Code ignora hook con timeout superato)
- Dev su repo non-itsiae → pass-through (scope già filtrato come tdd-gate)

## Testing

File nuovo: `tests/hooks/brainstorming-gate.test.sh` con scenari:

1. File prod + no brainstorming + N=1 → log + pass
2. File prod + no brainstorming + N=2 → block warn + counter=2
3. File prod + no brainstorming + N=4 → hard block
4. File prod + `DEVFORGE_SKIP_BRAINSTORMING=1` → bypass + log_bypassed
5. File prod + `siae-brainstorming` in session → pass + counter reset
6. File docs (.md) → pass (out of scope)
7. File IaC (.tf) → pass (out of scope)
8. Repo non-itsiae → pass (out of scope)
9. `DEVFORGE_ENFORCEMENT_OFF=1` → pass immediato
10. W1 mode senza `DEVFORGE_ENFORCEMENT_STRICT=1` → solo log, no block

Mock approach: `HOME=$(mktemp -d)` + `PLUGIN_ROOT` + fixture session-skills file. Stesso pattern di `post-commit-review-sha.test.sh`.

## Criteri di accettazione

- [ ] 10/10 scenari test passano
- [ ] `tdd-gate` test esistenti restano verdi (ordering non rompe)
- [ ] `sub-skill-gate` test restano verdi (nessuna modifica a PREREQ_MAP)
- [ ] Hook sotto 500ms wall-clock anche con counter file I/O
- [ ] 5 eventi telemetry nuovi emessi correttamente
- [ ] `DEVFORGE_SKIP_BRAINSTORMING=1` sblocca sempre con tracking
- [ ] W1 rollout: enforcement attivo SOLO con `DEVFORGE_ENFORCEMENT_STRICT=1`
- [ ] W2 rollout: flip default via env var flag nel hook

## Trade-off e rischi

| Rischio | Mitigazione |
|---|---|
| Dev frustrati al N=4 → abbandonano DevForge | Bypass env var per-comando + bypass emergency off |
| Counter stateful bug → bloccato senza motivo | Counter in file con reset automatico a session change |
| Power user fanno 10+ fix triviali post-merge | Scope limitato (no IaC/docs/test) + skip flag documentato |
| Enforcement percepito come "Big Brother" | Telemetry è già attiva (non è novità). Messaggi framano come "coach", non punizione |
| Dev aggirano con sed/cat > file | Out of scope: l'enforcement è per Edit/Write tool. Se dev va direct bash → fuori perimetro Claude |

## Stima SP

**5 SP-Umano / 2 SP-Augmented** — fix review: aggiunto counter SID-anchored + anti-abuse detection + post-skill reset logic + atomic write + 2 scenari test extra (bypass abuse detection, race condition). 10+2 test totali, 5+1 eventi telemetry.

## Out of scope

- Enforcement su IaC (has own validate/plan gates)
- Enforcement su test file edit (workflow TDD già separato)
- Punishment/gamification pubblico (nome&shame dashboard)
- Block retroattivo su commit già esistenti
- Auto-invocazione skill brainstorming (agency developer = essenziale)

## Rollout timeline

| Data | Azione |
|---|---|
| 2026-04-22 | Design doc approvato, piano scritto |
| 2026-04-23 | Implementazione + test (questa sessione o subagent) |
| 2026-04-24 | Release v1.45.0 DevForge con enforcement **disabled by default** |
| 2026-04-25 | Email team: "W1 pilota — opt-in via `DEVFORGE_ENFORCEMENT_STRICT=1`" |
| 2026-05-01 | Retrospective W1: adoption delta, feedback, issue critiche |
| 2026-05-02 | Se OK → release v1.46.0 con **enforcement default ON**, `DEVFORGE_ENFORCEMENT_OFF=1` emergency opt-out |
| 2026-05-22 | Verifica target: adoption ≥ 50%? Se no → iterazione successiva (message tuning, threshold) |
