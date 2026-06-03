# Design — Bundle identità developer raw per risoluzione resiliente a valle

**Data:** 2026-06-02
**Autore:** Lorenzo De Tomasi (+ Claude)
**Stato:** APPROVATO (via direttiva `/goal` "tutto procedi" 2026-06-02; spec-review 2 iter, 0 BLOCK)
**Complessità:** Media
**Branch base:** `main`
**Vincoli (durevoli):** SOLO dati raw ([[feedback_telemetry_raw_only_additive]]), NON cambiare il
pregresso (additivo, `schema_version` 2 invariato, eventi esistenti immutati).

**File coinvolti:**
- `lib/logger.sh` (MODIFICA — nuovo helper `devforge_identity_bundle`)
- `hooks/session-start` (MODIFICA — emette il bundle in `session_start.meta` + persiste in `user.json`)
- `tests/test_telemetry_fixes.sh` (AGGIUNTA — test bundle)

## Contesto

Obiettivo: risolvere in maniera **estremamente resiliente** i nomi degli sviluppatori. Il consumer
`developer-telemetry` fa già risoluzione deterministica robusta (chiave `last:<cognome>`, catena 5
livelli, 4 CSV alias, copertura 99.9%), ma resta vulnerabile dove **il producer emette una sola
identità già risolta** (lossy):
- **Box condiviso** (`a200576`: 10 dev su 1 account Linux) → non disambiguabile a valle.
- **Git config errata/condivisa** (caso Vetrano) → `actor_canonical` fidato ciecamente.

Oggi `hooks/session-start:27-43` usa catena **first-match** e scarta gli altri segnali; `user.json`
(`:45-50`) salva solo `{raw, source, canonical}`.

## Decisione — Emettere il BUNDLE RAW di tutti i segnali

Approcci: **(A) bundle raw multi-segnale [SCELTO]**; (B) risoluzione più furba nel producer
[scartato: lossy, viola raw-only]; (C) bundle per-evento [scartato: bloat]. Il producer emette
tutti i segnali grezzi; risoluzione a valle col massimo dell'informazione.

### Helper `devforge_identity_bundle()` (in `lib/logger.sh`)

| Campo | Fonte |
|---|---|
| `git_local_email` | `git config user.email` |
| `git_local_name` | `git config user.name` |
| `git_global_email` | `git config --global user.email` |
| `git_global_name` | `git config --global user.name` |
| `os_user` | `${USER:-$(whoami)}` |
| `host` | `hostname -s` (fallback `hostname`) |

`repo_root` NON è nel bundle (WARN-1): già top-level evento schema v2 (`logger.sh:538`).
Pseudocodice vincolante (no abort sotto `set -euo pipefail`):

```bash
devforge_identity_bundle() {
    local gle gln gge ggn osu host
    gle=$(git config user.email 2>/dev/null || true)
    gln=$(git config user.name 2>/dev/null || true)
    gge=$(git config --global user.email 2>/dev/null || true)
    ggn=$(git config --global user.name 2>/dev/null || true)
    osu="${USER:-}"; [ -z "$osu" ] && osu=$(whoami 2>/dev/null || echo "")
    host=$(hostname -s 2>/dev/null || hostname 2>/dev/null || echo "")
    printf '{"git_local_email":"%s","git_local_name":"%s","git_global_email":"%s","git_global_name":"%s","os_user":"%s","host":"%s"}' \
        "$(devforge_sanitize_json_str "$gle")" "$(devforge_sanitize_json_str "$gln")" \
        "$(devforge_sanitize_json_str "$gge")" "$(devforge_sanitize_json_str "$ggn")" \
        "$(devforge_sanitize_json_str "$osu")" "$(devforge_sanitize_json_str "$host")"
}
```

Ogni `git config` con `|| true` (non basta `2>/dev/null` sotto `set -e`). Nessuna
normalizzazione/scelta: **fatti grezzi**. Valori sanitizzati → newline interni diventano `\n`, mai
newline reali nel JSON. Output: oggetto JSON singola riga.

### Emissione (additiva)

1. **`session_start.meta`** (`session-start:274`): aggiungere `identity` = bundle (verbatim come
   valore oggetto, stesso pattern di `by_model`/`by_tool` in stop-gate). Una volta per sessione.
2. **`user.json`** (`:45-50`): aggiungere campo `identity` accanto a `{raw, source, canonical}`. La
   riga `:50` viene modificata (nuovo argv `sys.argv[5]` = stringa JSON del bundle, re-parsata con
   `json.loads`). Modifica al file di stato **locale**, NON allo schema v2 S3.
   - **python3 assente** (BLOCK-3): blocco già condizionato a `if command -v python3`; senza, no
     `user.json` (pre-esistente). `identity` in `user.json` è best-effort python3-only; la fonte
     autorevole per il consumer è `session_start.meta` su S3 (sempre emesso).
   - **bundle non-parsabile** (WARN-5): `json.loads` fallisce → `|| true` a `:50` → `user.json`
     senza `identity` (silent skip), sessione mai bloccata.

Campi per-evento esistenti (`user`/`user_raw`/`user_source`/`actor_canonical`) e catena first-match
restano **invariati** → nessun cambio al pregresso.

## Gestione errori / retrocompatibilità

- Ogni segnale best-effort: comando assente → `""`, mai crash, mai blocco session-start.
- Fuori da un repo → `git_*` vuoti, `os_user`/`host` popolati.
- `user.json` senza `identity` (sessioni pre-feature) → consumer default; campo additivo.
- `session_start.meta` additivo → consumer ignora `identity` ignoto; `schema_version` resta 2.
- Nessun evento storico riscritto; nessun campo esistente modificato.

## Privacy / sicurezza

Segnali già parzialmente emessi oggi (`user_raw` = git email). Aggiunti `git_*_name`/`os_user`/
`host` = identità lavorativa interna SIAE, coerente con lo scopo. `devforge_sanitize_json_str`
evita JSON injection su ogni valore.

## Testing

`tests/test_telemetry_fixes.sh` (AGGIUNTA):
1. `devforge_identity_bundle` in repo con git config local+global → JSON con i 6 campi, parsabile,
   **senza** `repo_root`; `os_user`/`host` non vuoti.
2. fuori da un repo (tmpdir non-git, `set -e` attivo) → bundle valido con `git_*` vuoti, helper
   exit 0 (no abort).
3. `session_start.meta` include `identity` (JSON valido) accanto a `project_dir`/`plugin_version`.
4. `user.json` include `identity` accanto a `raw`/`source`/`canonical` (se python3 presente).
5. sanitizzazione: git name con `"`/`\` E newline interno (`$'Mario\nRossi'`) → evento JSONL
   parsabile (no newline reali).
6. bundle non-parsabile al python di user.json → `user.json` senza `identity`, session-start exit 0.

## Criteri di accettazione

- [ ] AC1: `devforge_identity_bundle` → JSON con `git_local_email/name`, `git_global_email/name`,
      `os_user`, `host` (NO `repo_root`); ogni campo best-effort (`""`); helper exit 0 anche sotto
      `set -e` fuori da un repo.
- [ ] AC2: `session_start.meta` include `identity`; `project_dir`/`plugin_version` invariati.
- [ ] AC3: `user.json` include `identity` accanto a `{raw, source, canonical}` (additivo).
- [ ] AC4: campi per-evento (`user`/`user_raw`/`user_source`/`actor_canonical`) e catena first-match
      INVARIATI.
- [ ] AC5: valori sanitizzati (no JSON injection, incl. newline); fuori-repo non crasha session-start.
- [ ] AC6: additivo — `schema_version` 2; consumer/`user.json` legacy non si rompono.
- [ ] AC7: test suite bash verde (6 nuovi casi).

## Out of scope

- Risoluzione/normalizzazione lato producer (resta a valle).
- Modifica catena first-match o `actor_canonical` (pregresso invariato).
- Consumo del bundle in developer-telemetry (iniziativa separata sul consumer).

## Stima SP

| Scala | SP |
|---|---|
| Umano | 3 |
| AI-augmented | 1 |
