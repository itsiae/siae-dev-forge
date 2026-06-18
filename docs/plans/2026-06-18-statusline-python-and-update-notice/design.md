# Design — Status line: avviso python3 mancante + notifica aggiornamento plugin

**Data:** 2026-06-18
**Autore:** Lorenzo De Tomasi (con Claude Code)
**Complessità:** Media (2 feature, 2-3 file)
**Stato:** In attesa approvazione

## Contesto

La status line DevForge (`statusline/devforge-statusline.sh`, bash puro) è cablata in
`~/.claude/settings.json:320` come `bash .../devforge-statusline.sh` e gira dalla cache
del plugin (`.../siae-devforge/siae-devforge/<VERSION>/`).

Due gap di osservabilità per l'utente:

1. **python3 mancante** — usato per token-stats (statusline.sh:115) e per il path
   zero-loss della telemetria (`lib/logger.sh:87-97`). Quando assente, l'unico segnale
   è un warning su **stderr** (`logger.sh:83`) che NON compare nella status line.
   Inoltre il marker `~/.claude/.devforge-no-python-warned` è scritto **solo** sotto
   `DEVFORGE_FORCE_BASH_FALLBACK` (logger.sh:79), quindi inaffidabile come segnale.
   Risultato: l'utente vede token/telemetria degradati senza sapere perché.

2. **Aggiornamento plugin** — quando Claude Code aggiorna il plugin (nuova dir versionata
   in cache) non c'è alcun segnale visibile. L'utente non sa di star girando una versione
   diversa da quella della sessione precedente.

## Decisioni architetturali (ADR)

- **ADR-1 — Rilevazione python3 LIVE, non via marker.** La status line si ri-renderizza
  ad ogni update: `command -v python3` diretto è il segnale più robusto e resta visibile
  finché Python non è installato. Il marker esistente è pensato per dedup stderr one-shot,
  non copre il caso reale → scartato.

- **ADR-2 — Notifica aggiornamento = "versione cambiata", non "update disponibile".**
  Confrontare la versione locale con il marketplace remoto richiederebbe una chiamata di
  rete ad ogni render → inadatto a una status line. Si rileva invece il cambio di versione
  rispetto all'ultima vista (no rete, leggero). Assunzione confermata dall'utente
  ("procediamo").

- **ADR-3 — Detect+ack in session-start, display in statusline.** Il cambio versione si
  rileva UNA volta per sessione nel hook `session-start` (no race, pure-local), che scrive
  un flag session-scoped. La status line lo legge e mostra l'avviso per tutta la sessione
  post-update; si azzera naturalmente alla sessione successiva (nuova `DEVFORGE_SESSION_DIR`).
  Pattern idiomatico DevForge (hooks scrivono stato, statusline legge). Riusa il fatto
  già verificato che la statusline e il hook risolvono la stessa `DEVFORGE_SESSION_DIR`
  (token-stats.json funziona).

## Feature 1 — Avviso python3 mancante

**File:** `statusline/devforge-statusline.sh` (sezione warning riga 2, ~riga 262)

```bash
if ! command -v python3 >/dev/null 2>&1; then
  WARN_STR="${WARN_STR:+$WARN_STR }$(printf '%b🐍 python3 assente — installalo per token/telemetria%b' "$YELLOW" "$RESET")"
fi
```

- Colore giallo, coerente con gli altri warning.
- Additivo a `WARN_STR`: zero impatto sul rendering esistente.

## Feature 2 — Notifica aggiornamento plugin

**File A:** `hooks/session-start` — la chiamata `_devforge_detect_plugin_update >/dev/null 2>&1 || true`
va inserita **dopo** il `mkdir` di `DEVFORGE_SESSION_DIR` (riga ~28) e **prima** del blocco
`cat <<EOF` che emette `additional_context` (riga ~296). Redirect `>/dev/null 2>&1` per coerenza
difensiva con gli altri call pre-JSON della sezione (WARN-2 fix).

```bash
# Rileva cambio versione plugin (pure-local, no rete)
_devforge_detect_plugin_update() {
  local current last_seen_file last_seen
  current="$(basename "$PLUGIN_ROOT")"
  # In dev (repo non versionato in cache) basename non è semver → fallback plugin.json
  if ! printf '%s' "$current" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+'; then
    if command -v jq >/dev/null 2>&1 && [ -f "${PLUGIN_ROOT}/.claude-plugin/plugin.json" ]; then
      current="$(jq -r '.version // empty' "${PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null)"
    fi
  fi
  # WARN-1 fix: se dopo il fallback current NON è ancora semver (dev-mode senza jq) →
  # versione non determinabile → skip silenzioso (evita di scrivere "siae-dev-forge" in last_seen)
  if ! printf '%s' "$current" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+'; then
    return 0
  fi
  [ -z "$current" ] && return 0   # difesa ulteriore
  last_seen_file="${HOME}/.claude/.devforge-plugin-version"
  last_seen=""
  [ -f "$last_seen_file" ] && IFS= read -r last_seen < "$last_seen_file" 2>/dev/null || true
  if [ -z "$last_seen" ]; then
    printf '%s' "$current" > "$last_seen_file" 2>/dev/null || true   # prima installazione: nessun avviso
    return 0
  fi
  if [ "$last_seen" != "$current" ]; then
    printf '%s' "$current" > "${DEVFORGE_SESSION_DIR}/.plugin-updated" 2>/dev/null || true
    printf '%s' "$current" > "$last_seen_file" 2>/dev/null || true
  fi
}
_devforge_detect_plugin_update || true
```

**File B:** `statusline/devforge-statusline.sh` (lettura flag + display)

```bash
PLUGIN_UPDATED_VER=""
if [ -n "${DEVFORGE_SESSION_DIR:-}" ] && [ -f "${DEVFORGE_SESSION_DIR}/.plugin-updated" ]; then
  read -r PLUGIN_UPDATED_VER < "${DEVFORGE_SESSION_DIR}/.plugin-updated" 2>/dev/null || true
fi
# sanitize (printf %b)
PLUGIN_UPDATED_VER="${PLUGIN_UPDATED_VER//[^0-9a-zA-Z.\-]/}"
if [ -n "$PLUGIN_UPDATED_VER" ]; then
  WARN_STR="${WARN_STR:+$WARN_STR }$(printf '%b🆙 DevForge aggiornato a v%s%b' "$GREEN" "$PLUGIN_UPDATED_VER" "$RESET")"
fi
```

- Avviso verde (evento positivo), persiste per tutta la sessione post-update.

## Criteri di accettazione

**Feature 1**
1. `python3` assente dal PATH → riga 2 mostra "🐍 python3 assente — installalo per token/telemetria"
2. `python3` presente → nessun messaggio aggiuntivo (no-regression)
3. Script non va in errore (`set -euo pipefail`) in entrambi i casi

**Feature 2**
4. Prima installazione (nessun `.devforge-plugin-version`) → scrive versione, NESSUN avviso
5. Versione invariata tra sessioni → nessun avviso
6. Versione cambiata → riga 2 mostra "🆙 DevForge aggiornato a vX.Y.Z" per tutta la sessione
7. Versione non determinabile (dev mode senza semver/jq) → skip silenzioso, nessun errore
8. `session-start` non regredisce (resta sotto `set -euo pipefail`, detection guardata con `|| true`, no chiamate di rete)

## Testing

- `tests/.../test_statusline_python_warning.sh` — invoca lo script con PATH senza python3 → grep messaggio; caso positivo → assenza messaggio.
- `tests/.../test_statusline_plugin_update.sh` — crea flag `.plugin-updated` in una `DEVFORGE_SESSION_DIR` fittizia → grep avviso; assenza flag → nessun avviso.
- `tests/.../test_session_start_plugin_update.sh` — first-run (no last-seen) → scrive file, no flag; versione diversa → scrive flag + aggiorna last-seen; versione uguale → nessun flag.

## Stima SP

- Feature 1: Umano ~1 · Augmented ~0.5
- Feature 2: Umano ~2 · Augmented ~1
- **Totale: Umano ~3 · Augmented ~1.5**

## Out of scope

- Auto-install di Python (roadmap citata in `logger.sh:68`).
- Notifica "update disponibile" da marketplace remoto (richiede rete, vedi ADR-2).
- Allineamento drift `plugin.json` (1.90.2) vs cache (1.91.0) — issue separata
  ([[project_plugin_version_dual_source]]).
