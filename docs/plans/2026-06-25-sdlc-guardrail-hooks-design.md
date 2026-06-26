# SDLC Guardrail Hooks — Design (famiglia di 3 hook)

## 1. Contesto
Da un workflow di ricerca (obra/superpowers + AI-SDLC guardrails + inventario interno DevForge) sono emersi gap reali non coperti dai gate esistenti, su richiesta utente: migliorare allineamento, ridurre perdita di requisiti, aumentare test e sicurezza, **+ escalation su umano quando incerti/mancano dati**. Questo design aggiunge **3 hook** "che girano sotto", deterministici e fail-safe, **senza duplicare** ciò che esiste.

Mappatura categorie utente → hook:
- **(a) allineamento** + **(b) anti-perdita requisiti** → `scope-reduction-guard` (allinea piano↔design) + i gate esistenti (blind-review, spec-reviewer, premortem).
- **(c) aumento test** → **NESSUN hook nuovo**: già coperto da `tdd-gate` (blocca Write/Edit di file produzione senza siae-tdd, inclusi file nuovi) + `review-evidence` (regressione hard-floor). Un hook anti-retrofit sarebbe duplicato (YAGNI) — vedi §7.
- **(d) sicurezza proattiva** → `security-write-trigger`.
- **(e) escalation umano su incertezza** → `uncertainty-escalation` [TOP, gap senza copertura].

## 2. Coverage esistente (verificata — NON si duplica)
- Allineamento: `pr-blind-review-gate`, spec-reviewer, `pr-premortem-gate`, `plan-gate`.
- Test: `tdd-gate` (Write/Edit prod senza siae-tdd, anche file nuovi), `review-evidence`, `capture-test-result`. **Completo.**
- Sicurezza: `pr-gate` secret-scan + 16 runner OSS + `siae-security` (reattivi al PR).
- Requisiti: `brainstorming-gate`, `plan-gate(-write)`, `batch-checkpoint`.

## 3. I 3 hook

### 3.1 `uncertainty-escalation` (evento `Stop`, inserito come PRIMO elemento dell'array `Stop`, prima di `stop-gate`) — escalation-umano [TOP]
- **Trigger**: estrae l'ultimo messaggio assistant (riuso del blocco `stop-gate:61-96`, cascading `jq→node→python3` su `.messages // .transcript`, filtro role==assistant, ultimo). Conta i pattern di incertezza **FORTI e non ambigui** (`grep -ioE`): `non so`, `non sono sicuro`, `non è chiaro`, `non mi è chiaro`, `assumo che`, `sto assumendo`, `non ho abbastanza informazioni`, `non ho dati`, `TBD`, `da definire`, `unclear`, `not sure`, `I assume`, `I am not sure`. **Esclusi deliberatamente** i termini ambigui (`forse`, `dipende da`, `potrebbe essere`) perché comuni nel discorso tecnico normale (mitigazione falsi positivi, WARN-9 spec-review). Se **≥2 occorrenze** E il messaggio **non contiene `?`** → `decision:block` con messaggio che forza una domanda diretta all'utente.
- **Fail-safe**: input vuoto / nessun parser / msg non estraibile → `exit 0`. Se c'è già un `?` → `exit 0` (l'utente è già interpellato).
- **Limitazione nota**: il check `?` è sull'intero messaggio; un messaggio lungo con domanda in coda e incertezza nel mezzo passa silenziosamente. Accettato (fail-safe verso il non-bloccare).
- **Ordine**: PRIMO nell'array `Stop` in `hooks.json`, prima di `stop-gate` (così l'escalation precede il completion-claim check).

### 3.2 `scope-reduction-guard` (`PreToolUse:Write` su `docs/plans/*-plan*.md`) — anti-perdita requisiti + allineamento
- **Trigger**: alla scrittura di un piano esecutivo, legge il design doc `*-design.md` più recente. Estrae i requisiti (righe `AC-`, `- [ ]`, `Requisito`, header `## N.`). Sia `REQ_TOTAL` il numero estratto. Per ciascuno verifica con `grep -i` una keyword sostanziale nel contenuto del piano. `>30%` non tracciati → **warn** (`additionalContext`, non bloccante); `>60%` → `decision:block` con lista mancanti.
- **Edge 0-requisiti (WARN-5)**: se `REQ_TOTAL == 0` (design assente, formato non parsabile, 0 requisiti estratti) → `exit 0` silenzioso. **Nessuna divisione per zero, nessun block spurio.**
- **Fail-safe**: qualsiasi errore di parsing → `exit 0`. Soglie conservative. Precondizione: design doc segue naming `*-design.md` (già imposto da `plan-gate-write`).

### 3.3 `security-write-trigger` (`PreToolUse:Edit`/`Write` su file security-sensibili) — sicurezza proattiva
- **Trigger**: `FILE_PATH` matcha `*/auth/*`, `*/security/*`, `*/credentials/*`, `*.env*`, `*secrets*`, `*Token*`, `*Permission*`. Se `siae-security` NON risulta invocata nel task (riuso check `.devforge-session-skills` come tdd-gate) → emette **advisory** (`additionalContext`, NON blocca) che invita a invocare `siae-security`.
- **Fail-safe**: sempre `exit 0` (advisory). Il gate bloccante reale resta `pr-gate` al PR.
- **Nota friction (WARN-10)**: i glob `*Token*`/`*Permission*` possono matchare file non-credenziali (es. pagination token). Essendo advisory non-bloccante, il costo è basso; soglia rivedibile.

## 4. Errori / edge (invariante comune)
Tutti gli hook: **nessun `set -e/-u/pipefail`**; ogni ramo d'errore → `exit 0`; mai bloccare per errori tecnici. `uncertainty-escalation` può emettere `decision:block` (gate escalation); `scope-reduction-guard` blocca solo a >60%; `security-write-trigger` è sempre advisory.

## 5. Testing (un file test per hook)
- `uncertainty-escalation`: ≥2 pattern forti + no`?`→block; con`?`→pass; <2→pass; input vuoto→exit 0; pattern ambiguo singolo (`forse`)→pass (no falso positivo).
- `scope-reduction-guard`: piano completo→pass; 30-60% mancante→warn; >60%→block; **design assente→exit 0**; **design con 0 requisiti estratti→exit 0 (no div/0)**.
- `security-write-trigger`: file auth senza siae-security→advisory; con siae-security→silenzioso; file normale→silenzioso.

## 6. Criteri di accettazione
1. 3 hook registrati in `hooks.json` (1 `Stop` come primo elemento, 2 `PreToolUse`).
2. Ogni hook fail-safe: mai blocca per errore tecnico (exit 0).
3. `uncertainty-escalation` forza domanda su ≥2 pattern forti senza `?`; nessun falso positivo su pattern ambiguo singolo.
4. `scope-reduction-guard` non genera block spurio con 0 requisiti (no div/0).
5. Nessuna duplicazione di gate esistenti (test NON ri-coperto — già in tdd-gate).
6. Test PASS per ciascuno, registrati in `run-all.sh`; count `hooks-json-var-expansion` allineato (29→33).
7. Nessun segreto/PII.

## 7. Out of scope
- `ambient-tdd-retrofit-guard` **ELIMINATO**: duplica `tdd-gate`, che già blocca Write di file produzione nuovi senza `siae-tdd` (verificato nel codice, spec-review iter 1 BLOCK-1). La categoria "test" è già completa → nessun hook nuovo (YAGNI).
- `blocked-prerequisite-guard` escluso: feasibility incerta sul formato TaskUpdate via Bash.
- Nessun ML / confidence probabilistica: solo euristiche deterministiche. Nessuna configurabilità soglie via env (follow-up).

## 8. Riferimenti
- [github.com/obra/superpowers](https://github.com/obra/superpowers) (Pattern 3 scope-reduction, Pattern 5 BLOCKED escalation, Pattern 9 security audit).
- AI-SDLC guardrails: GAIE (arxiv 2606.22484), uncertainty FSM (needs_clarification / requires_human).
- KISS/YAGNI: pochi hook ad alto valore, riuso infra esistente, no duplicazione.

## File
Manifest esaustivo (sezione strutturata per spec-drift detection):
- `hooks/uncertainty-escalation` — hook Stop escalation-umano (nuovo)
- `hooks/scope-reduction-guard` — hook PreToolUse Write anti-perdita-requisiti (nuovo)
- `hooks/security-write-trigger` — hook PreToolUse Edit advisory sicurezza (nuovo)
- `hooks/hooks.json` — registrazione 3 hook (1 Stop primo, 2 PreToolUse)
- `tests/hooks/test_uncertainty_escalation.sh` — test (nuovo)
- `tests/hooks/test_scope_reduction_guard.sh` — test (nuovo)
- `tests/hooks/test_security_write_trigger.sh` — test (nuovo)
- `tests/run-all.sh` — registrazione 3 test
- `tests/hooks/hooks-json-var-expansion.test.sh` — allineamento count hook (29→33)
- `.claude-plugin/plugin.json` — bump versione 1.99.0 + count hook 27→30
- `.claude-plugin/marketplace.json` — bump versione 1.99.0 + count hook 27→30
- `CHANGELOG.md` — entry feature

## Stima
SP Umano 2.5 · Augmented 1
