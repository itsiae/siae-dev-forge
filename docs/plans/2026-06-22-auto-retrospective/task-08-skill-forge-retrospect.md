# Task 08 — `skills/forge-retrospect/SKILL.md` (MINE + APPLY + DISMISS)

**Goal:** Skill user-invocabile `/forge-retrospect` che orchestra lo stadio MINE (analisi LLM inline del digest → proposta lezioni, dry-run) + APPLY (`--apply`, scrive via writer + consuma il record) + DISMISS (`--dismiss`, rimuove il record senza scrivere). Riusa la cornice analitica di `siae-retrospective` (no duplicazione).

**Dipende da:** Task 03 (writer) + Task 04 (digest). **File coinvolti:** crea `skills/forge-retrospect/SKILL.md`; crea `tests/test_retro_skill_structure.py`.

## Step TDD bite-sized

### Step 1 — Test strutturale fallente
Crea `tests/test_retro_skill_structure.py`:
```python
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "forge-retrospect" / "SKILL.md"


def test_skill_exists_and_has_three_modes():
    src = SKILL.read_text(encoding="utf-8")
    for mode in ("MINE", "APPLY", "DISMISS"):
        assert mode in src
    assert "dry-run" in src.lower()


def test_skill_references_real_modules_and_reuses_retrospective():
    src = SKILL.read_text(encoding="utf-8")
    assert "lib/retro/digest.py" in src
    assert "lib/retro/writer.py" in src
    assert "siae-retrospective" in src           # riuso, non duplicazione
    assert "evidence_count" in src               # soglia ≥2 lezioni
    assert "retro-pending" in src
```

### Step 2 — Verifica fallimento
Run: `python3 -m pytest tests/test_retro_skill_structure.py -q`
Output atteso: `FAILED` — `FileNotFoundError: .../skills/forge-retrospect/SKILL.md`.

### Step 3 — Implementa
Crea `skills/forge-retrospect/SKILL.md`:
```markdown
---
name: forge-retrospect
description: Auto-retrospective DevForge — estrae lezioni dai fallimenti ripetuti dell'ultima sessione (mining del transcript) e le propone a CLAUDE.md/memory con dry-run/apply. Trigger - "/forge-retrospect", nudge a inizio sessione su fallimenti pendenti.
---

# forge-retrospect — Auto-retrospective (port di headroom learn)

> **Tipo:** On-demand · **Fase SDLC:** Retrospettiva · **Scope:** personale (CLAUDE.md + memory dell'utente)
> Riusa la cornice analitica di `siae-retrospective` per la qualità delle lezioni; qui aggiunge il loop automatico detect→mine→apply. NON duplica `siae-retrospective`.

## Modi

### MINE (default — dry-run, NON scrive nulla)
1. Trova il record pending più recente in `~/.claude/devforge-state/retro-pending/*.json`. Se nessuno: "Nessun fallimento pendente." e termina.
2. Costruisci il digest dal `transcript_path` del record:
   `python3 -c "from lib.retro.digest import build_digest; print(build_digest('<transcript_path>'))"`
3. Analizza il digest INLINE (sei già in una sessione Claude — nessun subprocess `claude -p`). Estrai lezioni che:
   - hanno `evidence_count` ≥ 2 (il pattern compare almeno 2 volte — categoria ripetuta o stesso fallimento poi risolto);
   - classifica ognuna come `context_file_rule` (fatto stabile → CLAUDE.md) o `memory_file_rule` (preferenza evolutiva → memory/);
   - per i `context_file_rule`, dai `section` (es. nome tool/tema) e `content` (bullet markdown actionable).
4. Mostra il DIFF proposto SENZA scrivere, usando il writer in dry-run:
   `python3 -c "from lib.retro.writer import Lesson, write_lessons; from pathlib import Path; print(write_lessons(Path.home()/'.claude'/'CLAUDE.md', [Lesson('<section>','<content>')], apply=False))"`
5. Chiedi conferma: "Applico con --apply o ignoro con --dismiss?"

### APPLY (`/forge-retrospect --apply`)
1. Stessa analisi di MINE.
2. Scrivi le lezioni con `write_lessons(..., apply=True)`:
   - `context_file_rule` → `~/.claude/CLAUDE.md` (sezione marker `<!-- devforge:retro:start/end -->`);
   - `memory_file_rule` → nuovo file in `~/.claude/projects/<hash>/memory/` + pointer in `MEMORY.md` (convenzione memory).
3. Rimuovi il record pending consumato (`rm` del `<sid>.json`).
4. Conferma cosa è stato scritto (idempotente: re-apply non duplica, sezioni umane intatte).

### DISMISS (`/forge-retrospect --dismiss`)
1. Rimuovi il record pending senza scrivere nulla. Conferma "ignorato".

## Vincoli
- Dry-run è il default: nessuna scrittura su CLAUDE.md/memory senza `--apply`.
- Mai inventare lezioni: ogni lezione deve citare l'evidenza dal digest (`evidence_count` ≥ 2).
- Scope personale: nessun dato lascia la macchina.
- Per lezioni team-wide ricorrenti → backlog (Approccio 3 batch-S3, vedi design §9).
```

### Step 4 — Verifica passa
Run: `python3 -m pytest tests/test_retro_skill_structure.py -q`
Output atteso: `2 passed`.

### Step 5 — Commit
`git add skills/forge-retrospect/SKILL.md tests/test_retro_skill_structure.py && git commit -m "feat(retro): skill /forge-retrospect MINE+APPLY+DISMISS (riusa siae-retrospective)"`

## Criteri di accettazione
- [ ] `SKILL.md` definisce i 3 modi MINE/APPLY/DISMISS; MINE è dry-run di default.
- [ ] Referenzia `lib/retro/digest.py` + `lib/retro/writer.py` e riusa `siae-retrospective` (no duplicazione).
- [ ] Menziona `evidence_count` ≥2 e `retro-pending`.
- [ ] APPLY consuma il record; DISMISS rimuove senza scrivere. `tests/test_retro_skill_structure.py` passa (2 test).
