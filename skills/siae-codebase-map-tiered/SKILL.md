---
name: siae-codebase-map-tiered
description: >
  Use as REQUIRED SUB-SKILL from siae-codebase-map when --tiered flag is set.
  Generates hierarchical CLAUDE.md (L1 root + L2 package + L3 child on-demand)
  from existing docs/CODEBASE_MAP.md, following Anthropic best practices for
  large codebases (load-on-demand, anti-bloat, import @ chain). Trigger: invoked
  by siae-codebase-map Step 7a, never standalone.
---

# SIAE Codebase Map — Tiered Mode (Sub-Skill)

```
╔══════════════════════════════════════════════════════════════════╗
║   ████████╗██╗███████╗██████╗ ███████╗██████╗                   ║
║   ╚══██╔══╝██║██╔════╝██╔══██╗██╔════╝██╔══██╗                  ║
║      ██║   ██║█████╗  ██████╔╝█████╗  ██║  ██║                  ║
║      ██║   ██║██╔══╝  ██╔══██╗██╔══╝  ██║  ██║                  ║
║      ██║   ██║███████╗██║  ██║███████╗██████╔╝                  ║
║      ╚═╝   ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚═════╝                   ║
║         📚 DevForge · Hierarchical CLAUDE.md                     ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 1. Init & Setup (sub-skill)
> **Invoked by:** `siae-codebase-map` Step 7a (opt-in via `--tiered`)

**Riferimento esterno:** [How Claude Code works in large codebases](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start) (Anthropic, 14 mag 2026)

---

## Prerequisiti

- `docs/CODEBASE_MAP.md` deve esistere (generato da `siae-codebase-map` Step 1-6)
- Repository git valido (`git rev-parse --is-inside-work-tree`)

Se mancano: errore esplicito, no fallback. L'utente deve invocare `siae-codebase-map` prima (trigger: "mappa codebase").

---

## Modello a livelli (best practice Anthropic)

| Livello | Path | Caricamento | Contenuto |
|---|---|---|---|
| **L1 root** | `./CLAUDE.md` | Session start | Big picture, max 200 righe |
| **L2 package** | `./<module>/CLAUDE.md` | Session start (monorepo) | Convenzioni package, import `@../CLAUDE.md` |
| **L3 child** | `./<module>/<subdir>/CLAUDE.md` | **On-demand** | Pattern locali, solo se >=10 file + pattern distintivo |

---

## Step 1 — Read CODEBASE_MAP.md

```bash
test -f docs/CODEBASE_MAP.md || { echo "ERROR: docs/CODEBASE_MAP.md not found. Invoke siae-codebase-map first (trigger: 'mappa codebase')."; exit 1; }
```

Parse frontmatter YAML per `last_mapped`, `stack`, `total_files`.
Identifica struttura repo:
- Mono-package: 1 solo modulo → genera solo L1
- Multi-module Maven (`find . -name pom.xml -maxdepth 3`)
- Monorepo TS (`test -f pnpm-workspace.yaml || test -f lerna.json`)

---

## Step 2 — Invocazione `emit-claude-md.py`

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/siae-codebase-map-tiered/scripts/emit-claude-md.py \
  --root . \
  --map docs/CODEBASE_MAP.md \
  --dry-run
```

Dry-run prima per ottenere preview JSON con `files_written`, `l1_lines`, `l2_count`, `l3_count`, `warnings`.

---

## Step 3 — Anti-bloat lint preview

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/siae-codebase-map-tiered/scripts/anti-bloat-lint.py \
  <preview_dir>
```

Lint advisory (exit 0 sempre). Mostra warning all'utente nella pre-flight card.

---

## Step 4 — Pre-flight 🟡 MEDIO

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-codebase-map-tiered |
|:---|
| 📊 File da scrivere: `<N>` (L1: 1, L2: `<n>`, L3: `<n>`) · Total righe: `<sum>` |
| ⚠ Anti-bloat warnings: `<count>` · 📁 Modalità: `<single-repo \| monorepo>` |
| **▼ Azione** |
| 1. ✏️ Scrittura `./CLAUDE.md` (root, `<L1_lines>` righe) |
| 2. ✏️ Scrittura `./<module>/CLAUDE.md` × `<l2_count>` |
| 3. ✏️ Scrittura `./<module>/<subdir>/CLAUDE.md` × `<l3_count>` (se soglia raggiunta) |
| 💡 Perche': gerarchia load-on-demand riduce bloat session start (best practice Anthropic) |
| 🚫 Se NO: CLAUDE.md gerarchici non scritti, comportamento attuale invariato |

Mostra all'utente. Attendi conferma esplicita.

---

## Step 5 — Write CLAUDE.md gerarchici

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/siae-codebase-map-tiered/scripts/emit-claude-md.py \
  --root . \
  --map docs/CODEBASE_MAP.md
```

Senza `--dry-run`: scrive i file. Output JSON con `files_written` array.

---

## Step 6 — Aggiorna frontmatter CODEBASE_MAP.md

Aggiungi al frontmatter:

```yaml
tiered_emitted: <timestamp>
tiered_files:
  - ./CLAUDE.md
  - ./<module>/CLAUDE.md
```

Permette al hook `session-start-tiered-advisor` di sapere quando il tiered è in uso.

---

## Classificazione rischio operazioni

| Operazione | Livello | Pre-flight |
|---|---|---|
| Read CODEBASE_MAP.md | 🟢 Sicuro | No |
| `emit-claude-md.py --dry-run` | 🟢 Sicuro | No |
| `anti-bloat-lint.py` | 🟢 Sicuro | No |
| Write CLAUDE.md L1/L2/L3 | 🟡 Medio | Si |
| Update CODEBASE_MAP.md frontmatter | 🟡 Medio | No (incluso in card Step 4) |

---

## Permission denied handling

| Fase | Se permesso negato |
|---|---|
| Step 1 (Read map) | Glob/Read permission-free |
| Step 2-3 (Bash py) | Se Bash negato: fallback testuale, presenta contenuto in chat |
| Step 5 (Write) | Se Write negato: presenta lista path + contenuto come output testuale, utente copia manualmente |

Memory `feedback_session_start_hook_invariants`: nessun output a stderr in caso di errore. Exit code chiaro.

---

## REQUIRED SUB-SKILL

```
REQUIRED SUB-SKILL: siae-verification
```

Invocata dopo Step 5 per validare che i file scritti rispettino i criteri di accettazione (vedi design doc).

---

## Limiti operativi

| Vincolo | Limite | Se superato |
|---|---|---|
| Profondità L3 | 1 livello sotto L2 | Niente L4. Eccesso → rifattorizza modulo |
| Righe per file | 200 (L1), 150 (L2), 100 (L3) | Warning anti-bloat, scrive comunque |
| Soglia L3 | >=10 file + pattern locale distintivo | Sotto soglia → no L3, eredita L2 |

---

## Anti-pattern (best practice Anthropic)

| Anti-pattern | Soluzione |
|---|---|
| L1 bloated (>200 righe) | Sposta dettagli in L2/L3 |
| L2 ripete L1 | Solo `@../CLAUDE.md` import + local-only |
| L3 generato ovunque | Rispetta soglia 10 file + pattern distintivo |
| TBD/TODO nei file | Risolvi prima di scrivere (anti-bloat-lint segnala) |

---

## Output stato terminale

- File CLAUDE.md L1+L2+L3 scritti con import `@` chain
- `CODEBASE_MAP.md` frontmatter aggiornato con `tiered_emitted`
- Lista file generati mostrata all'utente
- Suggerimento: commit con messaggio `feat(docs): tiered CLAUDE.md (L1+L2+L3)`
