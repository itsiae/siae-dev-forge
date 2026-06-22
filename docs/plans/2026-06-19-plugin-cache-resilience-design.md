# Design — Plugin Cache Resilience (sessioni attive sopravvivono all'auto-update)

**Data:** 2026-06-19 · **Autore:** Lorenzo De Tomasi · **Stato:** in review
**Goal utente (verbatim):** «verifica che con l'aggiornamento non venga mai cancellata cache, il plugin è business critical su macOS e windows deve funzionare sempre»

## Problema (verificato live)

`hooks/hooks.json` registra gli hook come `${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd <name>`.
Claude Code espande `${CLAUDE_PLUGIN_ROOT}` a `~/.claude/plugins/cache/siae-devforge/siae-devforge/<VERSION>/`
— path **versionato**, fissato a **boot** della sessione. L'auto-update **nativo** (`autoUpdate:true`
org-wide) installa la nuova versione e **rimuove la dir cache della precedente**. Ogni sessione Claude Code
**già attiva** ha gli hook ancorati al path vecchio → dopo l'update:
```
PostToolUse:Bash hook error — Plugin directory does not exist:
.../cache/siae-devforge/siae-devforge/1.91.0 (run /plugin to reinstall)
```
**Tutti** gli hook della sessione falliscono. Riprodotto live (sessione boot 1.91.0 → update 1.95.0 →
1.91.0 rimossa). Colpisce macOS **e** Windows. Business-critical.

**Non è codice nostro**: audit esaustivo v1.95.0 = ZERO cancellazioni cache da parte del plugin (il nostro
vecchio `rm -rf cache` è già stato rimosso in v1.95.0 — problema separato). La causa è il meccanismo nativo
di Claude Code. La statusline è già immune (path stabile, fix v1.95.0); gli **hook no**, perché il path è
deciso da Claude Code (`${CLAUDE_PLUGIN_ROOT}` versionato), non da noi.

Conferma architetturale: il "trampolino" (run-hook.cmd che rimbalza al clone stabile) NON aiuta — se la dir
versionata è rimossa, `run-hook.cmd` stesso sparisce e Claude Code fallisce **prima** di eseguirlo. L'unica
via sotto nostro controllo è far **riesistere** la dir versionata.

## Approccio scelto — A: compat-link auto-riparante (+ C: report upstream)

`session-start` (che gira sempre dalla versione corrente, esistente) ripristina i path delle versioni
recenti puntandoli alla corrente, così ogni nuova sessione **auto-ripara** le sessioni più vecchie.
`autoUpdate` resta `true` (obiettivo "tutti sempre l'ultima" preservato). In parallelo si apre una issue
upstream (Anthropic): l'auto-update non dovrebbe rimuovere cache di versioni potenzialmente in uso.

### Componenti

**1. `lib/plugin-cache-resilience.sh` (nuovo, sourcabile, zero side-effect al source)**
Funzione `devforge_ensure_version_compat <plugin_root>`. Pseudocodice **autoritativo** (i guard difensivi
sono requisiti, non opzionali — chiudono i CRITICI della spec-review):

```bash
devforge_ensure_version_compat() {
  local plugin_root="$1" base cur reg v target tmp
  base="$(dirname "$plugin_root")"

  # GUARD-1 (BLOCK-7): opera SOLO dentro la cache plugin Claude. Mai in path arbitrari
  # (dev da clone/worktree → PLUGIN_ROOT non versionato → niente operazioni fuori cache).
  case "$base" in
    */.claude/plugins/cache/siae-devforge/siae-devforge) : ;;
    *) return 0 ;;
  esac
  [ -d "$base" ] || return 0

  # CUR autorevole = basename(plugin_root) SOLO se semver puro E dir reale (non symlink).
  cur="$(basename "$plugin_root")"
  if ! { printf '%s' "$cur" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' && [ -d "$base/$cur" ] && [ ! -L "$base/$cur" ]; }; then
    # GUARD-2 (BLOCK-2): fallback = dir REALE (non-symlink) con versione più alta.
    # Se nessuna dir reale esiste → return 0 (mai dedurre cur da un symlink → no autoreferenza).
    cur=""
    for v in "$base"/*/; do
      v="$(basename "$v")"
      printf '%s' "$v" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' || continue
      [ -d "$base/$v" ] && [ ! -L "$base/$v" ] || continue
      { [ -z "$cur" ] || _ver_lt "$cur" "$v"; } && cur="$v"   # _ver_lt da plugin-version.sh (no sort -V)
    done
    [ -n "$cur" ] || return 0
  fi

  reg="${HOME}/.claude/.devforge-known-plugin-versions"
  grep -qxF "$cur" "$reg" 2>/dev/null || printf '%s\n' "$cur" >> "$reg" 2>/dev/null || true
  # cap ultime 10 versioni (semver) — innocuo: i symlink residui restano comunque validi
  if [ -f "$reg" ]; then
    tmp="$(grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' "$reg" 2>/dev/null | sort -t. -k1,1n -k2,2n -k3,3n -u | tail -10)"
    printf '%s\n' "$tmp" > "$reg" 2>/dev/null || true
  fi

  while IFS= read -r v; do
    [ -n "$v" ] && [ "$v" != "$cur" ] || continue
    [ -e "$base/$v/hooks/run-hook.cmd" ] && continue        # dir reale o symlink valido → MAI toccare
    if [ -d "$base/$v" ] && [ ! -L "$base/$v" ]; then
      # GUARD-3 (BLOCK-3/BLOCK-4): dir REALE (anche se incompleta/iCloud-parziale) → SKIP, mai cp-r sopra
      devforge_log "plugin_compat_skip_real_dir" "success" "{\"version\":\"$v\"}" 2>/dev/null || true
      continue
    fi
    # qui base/$v non esiste o è symlink rotto. GUARD-4 (BLOCK-5): rimuovi symlink solo se punta a un semver locale
    if [ -L "$base/$v" ]; then
      case "$(readlink "$base/$v" 2>/dev/null)" in
        [0-9]*.[0-9]*.[0-9]*) rm -f "$base/$v" 2>/dev/null || true ;;
        *) continue ;;                                       # symlink "estraneo" (dev/manuale) → non toccare
      esac
    fi
    # ricrea: symlink relativo (cur) + verifica; fallback copia ATOMICA (BLOCK-6: tmp+mv)
    if ln -s "$cur" "$base/$v" 2>/dev/null && [ -e "$base/$v/hooks/run-hook.cmd" ]; then
      :
    else
      rm -f "$base/$v" 2>/dev/null || true
      tmp="$base/.compat.$v.$$"
      rm -rf "$tmp" 2>/dev/null || true
      if cp -r "$base/$cur" "$tmp" 2>/dev/null && mv "$tmp" "$base/$v" 2>/dev/null; then :; else
        rm -rf "$tmp" 2>/dev/null || true
      fi
    fi
  done < "$reg"
  return 0
}
```
Invarianti chiave: **mai** scrivere fuori dalla cache (GUARD-1); **mai** toccare una dir reale (GUARD-3);
**mai** dedurre `cur` da un symlink (GUARD-2, evita autoreferenza); **mai** rimuovere symlink "estranei"
(GUARD-4); copia atomica tmp+mv per concorrenza/Windows (BLOCK-6); `_ver_lt` invece di `sort -V` portabile
(WARN-1); ogni write `|| true`, `return 0` sempre (best-effort sotto `set -euo pipefail`).

**2. `hooks/session-start`**
`source` di `plugin-cache-resilience.sh` **dopo** `logger.sh` e `plugin-version.sh` (dipende da `devforge_log`
e `_ver_lt`). Chiamata `devforge_ensure_version_compat "$PLUGIN_ROOT"` subito dopo i source delle lib e
prima delle attività pesanti (statusline install, setup-mcp), così la riparazione delle sessioni vecchie
avviene al più presto nel boot. Posizione esatta: subito dopo il blocco `source` (≈ riga 25), prima di `mkdir`.

**3. `tests/run-all.sh`** — sezione "Plugin Cache Resilience" (vedi Test).

### Flusso di auto-riparazione
1. Sessione A attiva (cache `1.91.0`).
2. Apro sessione B → auto-update nativo installa `1.95.0`, rimuove `1.91.0`.
3. `session-start` di B (da `1.95.0`) chiama `devforge_ensure_version_compat`: vede `1.91.0` nel registro,
   `base/1.91.0` mancante → crea `1.91.0 → 1.95.0`.
4. Sessione A: i suoi hook ritrovano `cache/.../1.91.0/hooks/run-hook.cmd` (esegue codice `1.95.0`) → tornano a funzionare.
5. Update successivo `1.96.0`: i symlink `*→1.95.0` diventano rotti → il prossimo `session-start` li ripunta a `1.96.0`.

## Limiti onesti
- **Non real-time (BLOCK-1)**: la mitigazione **non ripara la sessione che subisce la rimozione nel momento
  esatto**; ripara al primo `session-start` successivo (qualsiasi nuova sessione). Nella finestra
  update→prossimo-boot quella sessione resta degradata (hook falliscono ma Claude Code non crasha). Il fix
  reale è upstream (opzione C). Questo è esplicito e accettato.
- **Cap 10 + sessioni vecchissime (WARN-3)**: una sessione aperta da >10 update senza che parta nessuna nuova
  sessione perde la sua voce dal registro e non viene più riparata. Caso estremo (>10 release senza riavvii),
  documentato come limite noto.
- **Windows senza symlink nativi**: fallback copia atomica `cp -r`+`mv` → la dir vecchia è copia statica della
  corrente (funziona: esegue codice corrente); costo spazio mitigato dal cap a 10 versioni.

## Criteri di accettazione
- AC1: data `V` nel registro con `base/V` rimossa, dopo `devforge_ensure_version_compat` il path
  `base/V/hooks/run-hook.cmd` è risolvibile.
- AC2: una dir versione **reale** esistente (anche **incompleta**, senza `run-hook.cmd`) non viene mai
  modificata/rimossa/sovrascritta (no data loss; GUARD-3/BLOCK-3/BLOCK-4).
- AC3: un symlink **rotto** che punta a un semver locale viene ripuntato alla corrente; un symlink **estraneo**
  (target non-semver) NON viene toccato (GUARD-4/BLOCK-5).
- AC4: cross-platform — se `ln -s` non produce un path valido, fallback copia **atomica** `cp -r`+`mv`; verifica finale path esistente.
- AC5: best-effort — `base` inesistente/errori → ritorna 0, non fa abortire `session-start` (`set -euo pipefail`).
- AC6: registro dedup + cap 10 versioni (no crescita patologica).
- AC7: **GUARD path (BLOCK-7)** — se `base` non termina con `.claude/plugins/cache/siae-devforge/siae-devforge`,
  la funzione ritorna 0 senza creare nulla (mai operare in path utente arbitrari).
- AC8: **cur-derivation (BLOCK-2)** — con `base` contenente solo symlink e nessuna dir reale, la funzione
  ritorna 0 senza creare symlink autoreferenziali.
- AC9: **concorrenza (BLOCK-6)** — due invocazioni simultanee non corrompono `base/V` (copia atomica tmp+mv;
  `ln -s` idempotente con `|| true`); risultato finale sempre un path valido.
- AC10: zero regressioni sulla suite esistente.

## Test (`tests/run-all.sh` — sezione "Plugin Cache Resilience", un test per AC)
- **T1 (AC1)**: registro con `V` + `cur` reale; rimuovi `base/V`; chiama funzione → `base/V/hooks/run-hook.cmd` risolvibile.
- **T2 (AC2)**: `base/V` dir reale con `run-hook.cmd` → invariata (inode/contenuto). + variante dir reale **incompleta** (senza run-hook.cmd) → non toccata, nessun `cp -r` sopra.
- **T3 (AC3)**: symlink rotto `V→rimossa` con target semver → ripuntato a `cur`; symlink `V→/path/esterno` → NON toccato.
- **T4 (AC4)**: dopo la funzione il path esiste come symlink **oppure** copia (verifica `-e`), entrambi i rami producono `run-hook.cmd`.
- **T5 (AC5)**: `base` inesistente → rc 0, nessun errore; eseguita sotto `set -euo pipefail`.
- **T6 (AC6)**: chiamata 2× non duplica righe nel registro; registro con 12 voci → ridotto a 10 (più recenti).
- **T7 (AC7)**: `plugin_root` fuori dalla cache (es. `/tmp/clone`) → nessun file/symlink creato in quel path; rc 0.
- **T8 (AC8)**: `base` con solo symlink (nessuna dir reale) → nessun symlink autoreferenziale creato; rc 0.
- **T9 (AC9)**: due invocazioni in parallelo (`&`) sulla stessa `V` mancante → al termine `base/V` valido, nessuna dir `.compat.*` residua.

## File
- `lib/plugin-cache-resilience.sh` (nuovo) — funzione `devforge_ensure_version_compat` + GUARD-1..4.
- `hooks/session-start` — source della lib + chiamata early `devforge_ensure_version_compat "$PLUGIN_ROOT"`.
- `tests/run-all.sh` — sezione "Plugin Cache Resilience" con i test T1-T9.
- `docs/plans/2026-06-19-plugin-cache-resilience-design.md` — questo documento di design.

## Stima (SP doppia scala)
Umano: 5 · Augmented: 2. Dominio: 1 (resilienza cache). File: 3 (lib nuova, session-start, run-all.sh).

## Follow-up
- Opzione C: aprire issue upstream Anthropic (auto-update non deve rimuovere cache di versioni in uso /
  hook dovrebbero risolvere a un path stabile).
- Allineato a `project_native_autoupdate_breaks_active_sessions` e `project_autoupdate_managed_broken`.
