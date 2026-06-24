# Design — SIAE Global Rules: fonte unica versionata + iniezione session-start

- **Data:** 2026-06-24
- **Autore:** Lorenzo De Tomasi (+ DevForge)
- **Topic:** `siae-global-rules-injection`
- **Tipo:** config/wiring (Medio)
- **Branch:** da creare via `siae-git-workflow` post-approvazione

## 1. Contesto e problema

L'utente ha un set di "Claude Code — Global Rules" SIAE (scope control, interaction style,
data handling CSV, conventions dev/qa/prod, CI/CD GitHub Environments, workspace synced-paths,
network corporate). Oggi vivono solo nella `~/.claude/CLAUDE.md` personale di chi le ha scritte:
**non sono distribuite al team** e **non sono attive in ogni sessione**.

Vincolo utente 1 — *"va linkata con qualcosa"*: non un file orfano, ma agganciato a un
meccanismo attivo.
Vincolo utente 2 — *"devo essere allineate, valuta sempre allineamento"*: niente drift.
**Decisione utente (AskUserQuestion):** allineamento = **single source of truth nel repo**.
Vincolo dalle regole stesse — *"Do NOT over-scope, start minimal"*.

## 2. Punto di link (il "qualcosa")

`hooks/session-start:305` assembla il blocco `<EXTREMELY_IMPORTANT>` iniettato in OGNI sessione:

```
session_context = version_status + branching + using-devforge/SKILL.md + skill_catalog + global_memory_section
```

`global_memory_section` (righe 273-303) legge `~/.claude/devforge-global-memory/*.md` →
**per-macchina, NON versionato** → inadatto a distribuire regole team. Serve un nuovo path
"file-versionato-nel-repo → iniezione".

## 3. Approcci valutati

| # | Approccio | Pro | Contro | Compl. |
|---|-----------|-----|--------|--------|
| **A** ✅ | File reference versionato + nuova sezione in session-start (mirror del read di `using-devforge/SKILL.md` a riga 210) | Single source of truth (scelta utente); versionato → distribuito al team; concern separato dal backbone skill; testabile; fail-safe se file manca | +~8 righe nel hook a piu' alto blast radius (mitigato da test) | Bassa |
| B | Inline regole dentro `using-devforge/SKILL.md` | Zero modifica hook | Diluisce il backbone di attivazione skill; SKILL.md e' anche caricabile via Skill tool → doppio load; mescola due concern; "inline" e' l'opposto di "link" | Min |
| C | Riusare il loop global-memory puntandolo al repo | Riusa codice | global-memory e' per-macchina/non-versionato + guard anti-symlink; piegarlo mescola memoria personale e regole team | Media |

**Scelto: A.** Coincide con la scelta utente (fonte unica + linkata), minimale, rispecchia il
pattern di read esistente, mantiene le regole come artefatto distribuibile pulito.

## 4. Design (Approccio A)

### 4.1 Fonte unica versionata
Nuovo file: **`skills/using-devforge/reference/siae-global-rules.md`**
- Co-locato col backbone di sessione (session-start legge gia' da `skills/using-devforge/`).
- Versionato nel plugin → arriva a tutti i dev SIAE all'update.
- Contenuto = le Global Rules fornite, con 3 normalizzazioni per la distribuzione team:
  1. **Rimuovere il nome account `gh` personale** (`federicoarcangeli`): per-persona, non team.
     Tenere "gh autenticato in keychain, scope repo/workflow/gist".
  2. **Workspace:** "OneDrive-synced paths" → "synced paths (OneDrive/iCloud)" — SIAE usa entrambi.
  3. **Dedup verso skill (no duplicazione divergente):** topic con owner-skill rimandano alla skill
     invece di ri-spiegare il workflow:
     - git HTTPS-not-SSH → fatto ambientale always-on + *"workflow completo: `siae-git-workflow`"*.
     - 5 GitHub Environment vars → tabella reference + *"sync/verifica: `siae-github-env-sync`"*.
  Tutto il resto (proxy `10.255.1.241:8080`, `set_proxy`, env dev/qa/prod, scope/interaction/CSV)
  resta verbatim: sono guardrail ambientali always-on, non task-triggered come le skill.
- **Checklist anti-leak pre-commit (WARN-4):** prima del commit, `grep -nE '@|federicoarcangeli|/Users/|OneDrive|[0-9]{1,3}(\.[0-9]{1,3}){3}'` sul file e validare a mano ogni match: l'unico IP ammesso e' il proxy `10.255.1.241`; nessuna email/username/path-macchina/nome-persona deve restare. (= verifica operativa di AC6.)

### 4.2 Link (session-start)
Dopo `${branching_section}` (riga ~271), mirror del pattern read+escape esistente:
```bash
# Read SIAE global operational rules (single source of truth, versioned).
global_rules_content=$(cat "${PLUGIN_ROOT}/skills/using-devforge/reference/siae-global-rules.md" 2>/dev/null || echo "")
global_rules_section=""
if [ -n "$global_rules_content" ]; then
    global_rules_escaped=$(escape_for_json "$global_rules_content")
    global_rules_section="\\n\\n**SIAE Global Rules (operational guardrails — sempre attive):**\\n\\n${global_rules_escaped}"
fi
```
Inserire `${global_rules_section}` in `session_context` **subito dopo `${branching_section}`**
(guardrail in alto = massima visibilita'), prima dell'intro using-devforge.

**ATTENZIONE (WARN-1):** non basta aggiungere le 6 righe di calcolo — va modificata anche la
stringa literal di riga 305, altrimenti la feature e' no-op silenzioso. Riga 305 risultante:
```bash
session_context="<EXTREMELY_IMPORTANT>\nHai siae-devforge.\n\n${version_status_escaped}${branching_section}${global_rules_section}\n\n**Below is the content of your 'siae-devforge:using-devforge' meta-skill...:**\n\n${using_devforge_escaped}${catalog_section}${global_memory_section}\n</EXTREMELY_IMPORTANT>"
```
(il prefisso `\\n\\n` e' gia' dentro `${global_rules_section}`, coerente con `catalog_section`/`global_memory_section`).

**Nota redirect (WARN-1b):** lo snippet usa `2>/dev/null` (NON `2>&1` come riga 210): per un file
opzionale e' la scelta corretta — un errore di lettura non deve finire iniettato nel contesto.

### 4.3 Allineamento (per costruzione + guardia)
- **Per costruzione:** una sola fonte; session-start la legge LIVE ogni sessione (non snapshot) → zero drift testuale.
- **Valutazione continua:** test di guardia (sotto) asserisce che la sezione e' iniettata; se il
  file sparisce/rinomina, il test FALLISCE → drift del link catturato in CI.
- **Fail-safe:** file mancante → sezione vuota → iniezione resta JSON valido (no brick).

## 5. Errori / edge
- File mancante o vuoto → `global_rules_section=""` → nessun impatto su JSON (fail-safe).
- Contenuto con caratteri JSON-pericolosi → passa per `escape_for_json` (= `devforge_sanitize_json_str`), identico a using-devforge.
- Cap dimensione: file tenuto < ~4 KB (ben sotto soglie di troncamento payload); no read parziale necessaria.

## 6. Testing
Nuovo `tests/hooks/test_session_start_global_rules.sh` (mirror di `test_session_start_enforcement_off.sh`):
- **(A) Strutturale (hard):** grep nel hook → legge il path `siae-global-rules.md`, escapa, guarded (`if [ -n ... ]`), best-effort (`2>/dev/null`), `global_rules_section` referenziato in `session_context`.
- **(B) Funzionale (tollerante):** run sandbox `HOME=mktemp` → `STDOUT` contiene `additional_context` E un sentinel univoco delle regole (es. `SIAE Global Rules`) E resta JSON valido (`python3 -m json.tool` o `jq` se disponibile, altrimenti skip).
- **(C) Negativo/fail-safe:** rinominando temporaneamente il file la sezione sparisce ma `additional_context` resta presente e JSON valido.
- **(D) Anti-leak (WARN-2, copre AC3+AC6):** assert che il file versionato NON contenga pattern per-persona/segreti — `! grep -qE 'federicoarcangeli|@siae\.it|@gmail|/Users/|OneDrive[^/]|[0-9]{1,3}(\.[0-9]{1,3}){3}'` con whitelist esplicita del solo proxy `10.255.1.241`.
- **Registrazione OBBLIGATORIA (WARN-3):** `tests/run-all.sh` usa registrazione ESPLICITA per i test hook (non glob); aggiungere `test_session_start_global_rules.sh` accanto a `test_session_start_enforcement_off.sh`.

## 7. Criteri di accettazione
1. Esiste `skills/using-devforge/reference/siae-global-rules.md` con le 7 sezioni di regole (normalizzate §4.1).
2. `session-start` legge quel file e inietta `**SIAE Global Rules ...**` nel blocco `<EXTREMELY_IMPORTANT>`.
3. Nessuna duplicazione divergente: git/GitHub-env rimandano alle rispettive skill.
4. File mancante → session-start resta JSON valido (fail-safe verificato dal test).
5. `tests/hooks/test_session_start_global_rules.sh` PASS; nessuna regressione sugli altri test session-start.
6. Nessun segreto / nome-persona / path-macchina-specifico nel file versionato.

## 8. Out of scope (anti-over-scope)
- NESSUN sistema di config/feature-flag per le regole.
- NESSUN drift-checker runtime (proxy reachability, gh env vars live): scelta utente = single-source, non realta'-runtime.
- NESSUNA modifica a `using-devforge/SKILL.md` (concern separato).
- NESSUN sync bidirezionale con `~/.claude/CLAUDE.md` personale.

## 9. Stima
- SP (Umano): 3 · SP (Augmented): 1
- File toccati: +2 nuovi (`skills/using-devforge/reference/siae-global-rules.md`, `tests/hooks/test_session_start_global_rules.sh`), ~8 righe in `hooks/session-start`, +1 riga in `tests/run-all.sh`, bump versione in `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` (allineati, vedi memoria [[project_plugin_version_dual_source]]) + CHANGELOG.
