# Task 03 — Bump versione plugin + CHANGELOG

**Goal:** allineare la versione nei due manifest e registrare la modifica nel CHANGELOG. Stato: `[PENDING]`.
**Dipende da:** Task 01 + 02 (bump solo a comportamento completo e testato).

## File coinvolti
- MODIFICA: `.claude-plugin/plugin.json`
- MODIFICA: `.claude-plugin/marketplace.json`
- MODIFICA: `CHANGELOG.md`

## Step

### Step 1 — Leggi la versione corrente (NON assumere)
Run:
```bash
grep -m1 '"version"' .claude-plugin/plugin.json
grep -m1 '"version"' .claude-plugin/marketplace.json
```
Output atteso: due valori `"version": "X.Y.Z"`. Devono coincidere; se divergono, è il bug noto [[project_plugin_version_dual_source]] — allinea entrambi al maggiore PRIMA di bumpare.

### Step 2 — Bump minor (feature additiva)
Nuova versione = `X.(Y+1).0` rispetto al valore corrente letto allo Step 1. Aggiorna ENTRAMBI i file allo stesso valore. Esempio se corrente = `1.90.3` → nuova = `1.91.0`.
- `.claude-plugin/plugin.json`: campo `"version"`.
- `.claude-plugin/marketplace.json`: campo `"version"` dentro `plugins[0]`.

### Step 3 — CHANGELOG
Aggiungi in cima a `CHANGELOG.md` una entry per la nuova versione:
```markdown
## [X.(Y+1).0] - 2026-06-24
### Added
- **SIAE Global Rules**: fonte unica versionata (`skills/using-devforge/reference/siae-global-rules.md`) iniettata da `session-start` in ogni sessione (scope control, interaction style, data handling, conventions dev/qa/prod, CI/CD GitHub Environments, workspace, network corporate). Allineamento per costruzione (single source of truth) + test di guardia del link.
```

### Step 4 — Verifica allineamento versioni
Run:
```bash
diff <(grep -m1 -oE '[0-9]+\.[0-9]+\.[0-9]+' .claude-plugin/plugin.json) <(grep -m1 -oE '[0-9]+\.[0-9]+\.[0-9]+' .claude-plugin/marketplace.json)
```
Output atteso: nessun output (versioni identiche), exit 0.

## Criteri di accettazione
- [ ] `plugin.json` e `marketplace.json` hanno la stessa nuova versione minor.
- [ ] `CHANGELOG.md` ha l'entry datata 2026-06-24.
- [ ] Lo `diff` dello Step 4 non produce output.

## Commit
```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "chore(release): bump versione per SIAE Global Rules injection"
```
