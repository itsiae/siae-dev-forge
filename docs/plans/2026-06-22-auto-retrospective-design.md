# Design — Auto-retrospective (forge-retrospect)

> **Data:** 2026-06-22 · **Fase SDLC:** 2. Design · **Tipo:** Feature nuova · **Complessità:** Media-Alta
> **Origine:** integrazione delle ottimizzazioni di [headroom](https://github.com/chopratejas/headroom) (Apache 2.0) in DevForge — port di `headroom learn` (failure learning).
> **Branch:** `feat/auto-retrospective` (da `main`)

## 1. Contesto e problema

Obiettivo utente: integrare da headroom le ottimizzazioni che danno **riduzione tempi**. Tra i candidati emersi (memory `project_headroom_steal_candidates`), il valore più alto e *compound* è l'**auto-retrospective**: chiudere automaticamente il loop "non ripetere gli stessi errori", allineato al North Star zero-bug (`project_north_star_zero_bug_jul2026`).

Oggi DevForge ha la skill manuale `siae-retrospective` (skills/siae-retrospective/SKILL.md) ma richiede trigger umano e non fa mining automatico dei fallimenti. `headroom learn` fa esattamente questo: legge i transcript di sessione, classifica i fallimenti, e propone correzioni a `CLAUDE.md`/memory.

**Materia prima:** il **transcript JSONL nativo di Claude Code** (`~/.claude/projects/<hash>/*.jsonl`), che il SessionEnd hook riceve come `transcript_path` su stdin. Contiene ogni tool call + output/errore — più ricco della telemetria DevForge (sparsa). Sorgente secondaria: telemetria DevForge (`~/.claude/devforge-activity.jsonl`, vedi `lib/logger.sh:5`) per segnali specifici (`gate_bypassed`, test fail).

## 2. Vincolo determinante (intake)

L'hook `SessionEnd` esiste **già** ed è in uso (registrato in `hooks/hooks.json:146`, comando `session-end` a `:152`, **timeout 10s** a `:153`; script `hooks/session-end`, 6741B — legge stdin a `:27-31`, guard at-most-once a `:39`, già usa `python3` per token/adoption a `:71`). Quindi: **nessun rischio compatibilità versione** (la versione installata lo supporta già) e la mia è una **modifica additiva** a un hook esistente, non un hook nuovo.

Il vincolo determinante è il **timeout 10s**, già condiviso con `token-collector.py` + `adoption-analyzer.py`: una chiamata LLM di mining eccede il budget → **l'LLM non può girare dentro l'hook**, e anche lo stadio DETECT deve restare leggero (bounded). Questo scarta l'esecuzione sincrona e guida l'architettura.

## 3. Approcci valutati (ADR)

| Approccio | LLM dove | Pro | Contro | Esito |
|-----------|----------|-----|--------|-------|
| A2-detached | `claude -p` in background dal SessionEnd | mining automatico | processo detached fragile; costo LLM per-sessione; concorrenza con nuova sessione | scartato |
| **A2-onDemand** ⭐ | **inline nella skill (sessione viva)** | **nessun subprocess, nessun costo per-sessione, scritture su memory con human-in-the-loop = sicuro** | richiede 1 keystroke utente (mitigato da nudge) | **scelto** |
| batch-S3 (team) | job offline su S3 aggregato | lezioni team-wide cross-developer | build grande; scope question producer↔consumer | follow-on (§9) |

**Decisione:** A2-onDemand. Il SessionEnd fa solo *detect+stage* veloce (no LLM, ≤2s); il mining LLM avviene quando l'utente lancia la skill nella sessione viva (Claude analizza inline). Rispetta il budget 10s ed è il più sicuro per scritture su `CLAUDE.md`.

## 4. Architettura (4 stadi, LLM solo allo stadio 3)

```
1. DETECT   hooks/session-end (additivo, dopo il guard :39, prima dell'echo finale; ≤2s, no LLM, bounded):
            legge transcript_path da stdin → classifier taxonomy su tool_result (cap ultimi N eventi)
            → conta error tool-result + retry ripetuti (+ segnali DevForge gate_bypassed/test fail)
            → se failures ≥ soglia O pattern ripetuto: scrive staging record LEGGERO
              ~/.claude/devforge-state/retro-pending/<devforge_session_id>.json
              (conteggi + categorie top + transcript_path — NON il digest completo, che è costoso)
2. NUDGE    SessionStart successivo: se retro-pending/ non vuoto E sentinel ~/.claude/.devforge-retro-reminded
            assente → 1 riga additionalContext + imposta il sentinel (nudge ≤1 per sessione)
            "⚠️ N fallimenti ripetuti nella sessione scorsa → /forge-retrospect per estrarre lezioni (o --dismiss)"
            [Il sentinel è GIA' azzerato a ogni session-start da hooks/session-start:475 → il nudge si ripresenta
             la sessione dopo se il record è ancora pendente, finché --apply/--dismiss non lo consuma]
3. MINE     skill /forge-retrospect (on-demand): Claude INLINE costruisce il digest dal transcript_path (digest.py)
            → classifica lezioni in context_file_rules (CLAUDE.md, fatti stabili) vs memory_file_rules (memory/, preferenze)
            → ogni lezione ha evidence_count ≥ 2 + impatto stimato → propone DIFF (dry-run, MAI scrive)
4. APPLY    --apply esplicito → writer marker-section → scrive dentro <!-- devforge:retro:start/end -->
            (replace-by-heading + carry-forward), idempotente, mai tocca sezioni umane → consuma il record
   DISMISS  /forge-retrospect --dismiss → rimuove il record pending senza applicare nulla (chiude il nudge)
```

## 5. Componenti (File)

| File | Ruolo | Origine |
|------|-------|---------|
| `lib/retro/classifier.py` | `is_error_content()` + `classify_error()` (14 categorie) | port headroom `_shared.py`, Apache-2.0 attribution |
| `lib/retro/digest.py` | costruisce digest compresso del transcript, cap 40k char — invocato in **MINE** (skill, no budget 10s), NON nell'hook | pattern headroom `analyzer.py` |
| `lib/retro/writer.py` | merge marker-section + dry-run/apply + parse-prior + carry-forward | port headroom `writer.py` |
| `lib/retro/scan.py` | orchestratore **DETECT light**: legge transcript (cap ultimi N eventi), applica classifier, scrive record leggero (conteggi+categorie+path, NO digest) | nuovo |
| `hooks/session-end` | aggiunge chiamata a `scan.py` **dopo il guard `:39`, prima dell'echo finale** (degrada se python assente, exit 0 sempre) | modifica additiva a hook esistente |
| `hooks/session-start` | aggiunge il nudge se retro-pending non vuoto e sentinel `.devforge-retro-reminded` assente; poi imposta il sentinel (fast, no LLM). Il `rm` del sentinel è **già** presente a `session-start:475` | modifica additiva |
| `skills/forge-retrospect/SKILL.md` | orchestra stadi 3-4; riusa la cornice analitica di `siae-retrospective` (no duplicazione) | nuovo |
| `NOTICE` (repo) | attribuzione Apache-2.0 headroom per i file portati | modifica |

**Soglia DETECT (concreta):** staging scritto se `error_tool_results ≥ 3` **OPPURE** stesso `(tool, error_category)` ripetuto ≥ 2 volte nella sessione. Sotto soglia → nessun record, nessun nudge.

**Target lezioni (scope MVP = personale):** fatti stabili → sezione marker in `~/.claude/CLAUDE.md`; preferenze evolutive → nuovo file in `~/.claude/projects/<hash>/memory/` + pointer in `MEMORY.md` (convenzione memory esistente).

## 6. Flusso dati

```
transcript JSONL (Claude Code) + devforge-activity.jsonl
        │  SessionEnd (DETECT, no LLM, ≤2s)
        ▼
retro-pending/<sid>.json (staging LEGGERO: conteggi + categorie + transcript_path, NO digest)
        │  SessionStart (NUDGE, fast)
        ▼
utente lancia /forge-retrospect
        │  MINE (Claude inline) → proposta lezioni (dry-run diff)
        ▼
utente --apply → writer marker-section → CLAUDE.md / memory/  (idempotente)
        │
        └─ staging record consumato/rimosso
```

## 7. Gestione errori / sicurezza

- **Mai bloccare il session-end:** lo stadio DETECT è best-effort, exit 0 sempre. Bounded (cap eventi) per stare nel **budget 10s condiviso** con `token-collector.py`+`adoption-analyzer.py` già presenti. Mitigazione overflow: `scan.py` è invocato **per ultimo** nella catena session-end (dopo token+adoption+flush); se il budget è già quasi esaurito degrada a skip ed esce 0 (mai supera il timeout dell'hook).
- **Python assente:** scan skip con warn one-shot via sentinel file (stesso pattern della telemetria, `lib/logger.sh:87-90` — `.devforge-no-python-warned`).
- **transcript_path:** preso da stdin dell'hook (input standard SessionEnd di Claude Code). Fallback se assente: deriva da `cwd` → `~/.claude/projects/<hash>`; se nemmeno questo → skip.
- **session_id staging:** il filename del record usa il **DevForge session id** (`~/.claude/.devforge-session-id`, già gestito da `devforge_init_session`). La concorrenza multi-tab eredita il guard at-most-once dell'hook (`session-end:39`).
- **Compatibilità versione:** nessun rischio — SessionEnd è **già** registrato e in uso (vedi §2).
- **Transcript illeggibile / formato cambiato:** parsing difensivo, salta righe non parseabili, degrada a skip.
- **Nessuna scrittura senza `--apply`:** MINE è dry-run; APPLY è esplicito; DISMISS rimuove il record senza scrivere.
- **Apply idempotente:** marker-section; re-apply non duplica; sezioni umane mai sovrascritte.
- **Privacy:** scope personale, nessun dato lascia la macchina; il transcript resta locale.

## 8. Testing

- **Unit:** `classifier` (ogni categoria su input noti), `digest` (cap budget rispettato), `writer` (merge/carry-forward/dry-run/idempotenza), `scan` (soglia: 2 errori → no record, 3 → record; cap eventi rispettato), DISMISS (rimuove record senza scrivere su CLAUDE.md/memory).
- **Integration:** fixture transcript JSONL sintetico → `scan.py` → assert staging record leggero + conteggi corretti; scan su transcript da 500 eventi completa < 2s.
- **Probe (compression-only, steal #8):** dato un transcript con fallimenti noti, le lezioni proposte referenziano quei fallimenti reali (substring probe, no LLM judge).
- **No-regression:** suite hook esistente invariata; `siae-retrospective` manuale non modificata.

## 9. Scope e non-goals

- **In scope (MVP):** stadi 1-4, scope personale, port classifier/digest/writer, skill + nudge.
- **Non-goals (follow-on):** promozione team-wide cross-developer via S3 → `rules/` condivise (Approccio 3, batch-S3); aggiunta di nuovi event-type alla telemetria (il transcript nativo basta); auto-apply senza conferma.

## 10. Stima

**6 SP (Umano) / 3 SP (Augmented).** Driver: port 3 moduli python (basso, codice esistente headroom) + skill orchestratrice + 2 modifiche hook additive + test.

## 11. Criteri di accettazione

1. Scan completa < 2s su transcript da 500 eventi e **mai** blocca il session-end (exit 0; rientra nel budget 10s condiviso con token-collector/adoption).
2. Staging scritto solo se ≥3 error tool-result o pattern `(tool,category)` ripetuto ≥2; record **leggero** (conteggi+categorie+transcript_path, senza digest).
3. Nudge mostrato **≤1 volta per sessione** (guardia sentinel `.devforge-retro-reminded`, azzerato da `session-start:475`); si ripresenta la sessione dopo se il record è ancora pendente. Il record è consumato **solo** da `--apply` (applica + rimuove) o `--dismiss` (rimuove senza scrivere). Un'invocazione dry-run NON consuma il record.
4. `/forge-retrospect` produce un diff dry-run; **nessun** file scritto senza `--apply`.
5. Lezioni applicate dentro marker-section; re-apply idempotente; sezioni umane intatte.
6. Ambiente python-less: scan degrada pulito con warn one-shot, nessun errore all'utente.
7. `NOTICE` contiene l'attribuzione Apache-2.0 headroom per i file portati.
8. `siae-retrospective` manuale invariata (no-regression).

## File
Manifest esaustivo (sezione strutturata, header non numerato, per spec-drift detection):
- `lib/retro/scan.py` · `lib/retro/classifier.py` · `lib/retro/digest.py` · `lib/retro/writer.py` · `lib/retro/nudge.py` · `lib/retro/__init__.py` — package retrospettiva (port headroom)
- `hooks/session-end` — DETECT scan (additivo)
- `hooks/session-start` — NUDGE (additivo, riconciliato sopra python3_banner)
- `skills/forge-retrospect/SKILL.md` — skill MINE/APPLY/DISMISS
- `commands/forge-retrospect.md` — comando
- `tests/test_retro_classifier.py` · `tests/test_retro_digest.py` · `tests/test_retro_writer.py` · `tests/test_retro_scan.py` · `tests/test_retro_nudge.py` · `tests/test_retro_notice.py` · `tests/test_retro_session_end_hook.py` · `tests/test_retro_session_start_nudge.py` · `tests/test_retro_skill_structure.py` · `tests/integration/test_retro_e2e.py` — 36 test
- `CHANGELOG.md` — entry 1.100.0
- `.claude-plugin/plugin.json` · `.claude-plugin/marketplace.json` — bump versione + count
- `NOTICE` — attribuzione Apache-2.0 headroom
