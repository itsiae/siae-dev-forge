---
status: handover
owner: Lorenzo De Tomasi
created: 2026-06-03
target: developer-telemetry (consumer)
topic: Nuovi campi/eventi telemetria DevForge da consumare
supersedes_partial: docs/handover/2026-04-22-siae-telemetry-events.md (additivo, non sostitutivo)
---

# Handover — Nuovi dati telemetria DevForge per developer-telemetry

## Contesto

Tre PR (giugno 2026) introducono **nuovi campi e eventi RAW** su S3, tutti **additivi**
(`schema_version` resta 2; campi/eventi esistenti invariati). Il producer NON calcola
valutazioni/costi compositi: emette fatti grezzi, la derivazione vive nel consumer.

| PR | Stato | Contenuto |
|---|---|---|
| #296 | MERGED | session_end token breakdown + by_model + by_tool; skill_completed token delta |
| #297 | MERGED | session_start/user.json identity bundle |
| #302 | OPEN | session_end by_skill + by_model_tokens + pricing; eventi test_run_result + tdd_cycle; pr_merged session_tokens_cumulative |

Schema comune evento: invariato (vedi `2026-04-22-siae-telemetry-events.md`). Tutti i campi
sotto vivono in `meta` salvo dove indicato. Regola di consumo: **leggere con `.get(...)` e
default** (un evento storico non avrà i campi nuovi).

---

## 1. Nuovi EVENTI

### `test_run_result` (hook: capture-test-result)
Emesso ad ogni cattura di un comando test.
```json
"event": "test_run_result",
"meta": {
  "status": "PASS" | "FAIL",
  "exit_code": 0,            // int oppure null
  "coverage_pct": 85.7,      // number oppure null (se non estratta/non numerica)
  "framework": "pytest"      // pytest|vitest|jest|maven|gradle|go|cargo|unknown
}
```
**Uso:** disciplina di test per `actor_canonical`, coverage trend, ratio run FAIL.

### `tdd_cycle` (hook: capture-test-result)
Emesso ad ogni transizione di fase TDD.
```json
"event": "tdd_cycle",
"meta": {
  "from_phase": "RED",       // INIT|RED|GREEN|REFACTOR
  "to_phase": "GREEN",
  "elapsed_sec": 42,         // int >= 0 (tempo nella fase precedente)
  "reason": ""               // "regression" | "refactor-regression" | ""
}
```
**Uso:** durata media RED→GREEN (proxy difficoltà), tasso regressioni GREEN→RED.

---

## 2. `session_end.meta` — campi aggiunti

```json
"meta": {
  // ... campi pre-esistenti (skills_used_count, commits_count, total_tokens, output_tokens,
  //     cost_estimate_eur, model_prevalent) invariati ...

  // PR #296:
  "input_tokens": 12000,
  "cache_read_tokens": 800000,
  "cache_write_5m_tokens": 5000,
  "cache_write_1h_tokens": 0,
  "by_model": {"claude-opus-4-8": 120000, "claude-sonnet-4-6": 30000},   // total per modello
  "by_tool":  {"Bash": 42, "Read": 88, "Edit": 15, "mcp__sport-kg": 7},  // conteggio chiamate

  // PR #302:
  "by_skill": {                          // componenti per skill, SENZA cache_read (anti-inflazione)
    "siae-devforge:siae-tdd": {"output": 3100, "input": 1200, "cache_write_5m": 200, "cache_write_1h": 0}
  },
  "by_model_tokens": {                   // componenti per modello, CON cache_read (per pricing)
    "claude-opus-4-8": {"input": 12000, "output": 8000, "cache_read": 800000, "cache_write_5m": 5000, "cache_write_1h": 0}
  },
  "pricing": {                           // tariffe applicate (raw, USD/1M)
    "unit": "usd_per_1m_tokens",
    "eur_rate": 0.91,
    "by_model": {
      "claude-opus-4-8": {"input": 5.0, "output": 25.0, "cache_read": 0.50, "cache_write_5m": 6.25, "cache_write_1h": 10.0}
    }
  }
}
```

**Nota anti-inflazione (importante per il consumer):** `cache_read` è il contesto della
conversazione RILETTO ad ogni turno. NON sommarlo come "lavoro" della skill — per questo
`by_skill` lo esclude. È invece incluso in `by_model_tokens` perché ha una tariffa reale (0.1×)
necessaria al ricalcolo costo.

**Ricalcolo costo multi-vendor a valle:**
```
cost_vendor = Σ_model Σ_comp  by_model_tokens[model][comp] × vendor_rate[model][comp] / 1e6
```
`pricing.by_model` fornisce le tariffe Anthropic applicate; sostituendole con un listino vendor
si ottiene il costo sotto quella soluzione. Il `cost_estimate_eur` esistente resta la fonte
ufficiale del costo Anthropic.

---

## 3. `skill_completed.meta` — campi aggiunti (PR #296)
```json
"meta": { "skill_name": "...", "sdlc_phase": "...", "outcome": "success",
          "tokens_total_delta": 12400, "tokens_output_delta": 3100 }
```
**Uso:** token spesi mentre la skill era il contesto attivo; per `by_phase` aggrega su `sdlc_phase`.

---

## 4. `pr_merged.meta` — campo aggiunto (PR #302)
```json
"meta": { "pr_number": 302, "merge_method": "...", "total_commits": N, "delta_from_open": N,
          "session_tokens_cumulative": 4200000 }
```
**Uso:** ancora token→esito (token cumulati di sessione al merge); join con rework/review_cycles.

---

## 5. Identity bundle (PR #297) — `session_start.meta.identity` + `user.json.identity`
```json
"meta": { "project_dir": "...", "plugin_version": "...",
  "identity": {
    "git_local_email":  "f.vetrano@eng.it",
    "git_local_name":   "Francesco Vetrano",
    "git_global_email": "reply@siae.it",
    "git_global_name":  "Francesco Vetrano",
    "os_user":          "fvetrano",
    "host":             "ws-vetrano"
  }
}
```
Stesso oggetto persistito in `user.json` (cache locale per-sessione, accanto a `{raw,source,canonical}`).

**Uso (risoluzione resiliente, già mappato in `03_build_facts.py:351`, PRIORITÀ -1 graceful):**
- **Box condiviso** (`a200576`, 10 dev/1 account): `identity.git_local_email` (se valorizzata con
  email personale) disaggrega verso la persona reale, dove `actor_canonical`/`repo_root` danno
  solo il bucket collettivo.
- **Git-config errata** (caso Vetrano): `identity.git_local_email` (config locale del repo) è più
  affidabile di `actor_canonical` (config globale); `os_user` come fallback aggiuntivo a
  `repo_root_aliases`.
- Tutti i campi best-effort: stringa vuota se non disponibili. Bundle assente nelle sessioni
  pre-#297 → consumer usa la chain esistente.

---

## Punti di consumo nel codice consumer (riferimento)

- `meta` già parsato: `03_build_facts.py:375` (`meta_dict = e.get("meta") or {}`).
- Token/skill nuovi: leggere nel blocco `session_end` (`:384-388`) con `meta_dict.get(...)`.
- `identity`: `session_start.meta.identity` (S3, autorevole) o `user.json.identity` (cache locale).
- Aggancio identity per risoluzione: nuovo ramo PRIORITÀ -1 prima di `repo_root_aliases`
  (`03_build_facts.py:351`) — vedi proposta nel report di mappatura.
- Nessuna modifica richiesta alla chain di attribuzione per i campi token/skill (sono solo KPI).

## Dimensioni indipendenti (NON riconciliare token-per-token)
`by_skill` (dimensione skill, no cache_read) e `by_model_tokens` (dimensione modello, con
cache_read) sono fatti RAW su assi diversi: il consumer li usa separatamente. La loro somma NON
deve coincidere (per scopo + per cache_read). Stesso principio per `by_tool` (conteggio chiamate,
non token).
