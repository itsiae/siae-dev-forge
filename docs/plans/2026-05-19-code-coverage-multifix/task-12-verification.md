# Task 12 — Verification: smoke E2E + pytest + LOC check

**Fix-group:** — (gate finale)
**Stato:** [PENDING]
**Dipendenze:** Task 01-11 tutti completati

## Verifiche

### 1. Pytest no regression

```bash
cd /Users/mazzacuv/Git/siae-dev-forge/skills/code-coverage
python3 -m pytest scripts/tests/ -v
```
Atteso: tutti i test esistenti + nuovi (test_estimate_size_anchored.py, extension di test_detect_stack_ext.py, test_select_command_multimodule.py, test_validate_env_ext.py) → PASS.

### 2. SKILL.md LOC

```bash
wc -l skills/code-coverage/SKILL.md
```
Atteso: ≤ 100.

### 3. Zero jq

```bash
grep -c "\bjq\b" skills/code-coverage/SKILL.md skills/code-coverage/lib/phase*.sh
```
Atteso: 0 (zero match).

### 4. E2E sui 4 archetipi blind-review

Clone i 4 repo e verifica output di `detect_stack.py`:

```bash
for repo in dataplatform-dwh-etl uptime-console-backend pae-pae-services-be jarvis-bff; do
  TMPDIR=$(mktemp -d)
  gh repo clone itsiae/$repo "$TMPDIR/repo" -- --depth 1
  python3 skills/code-coverage/scripts/detect_stack.py "$TMPDIR/repo" | \
    python3 -c "import json,sys; s=json.load(sys.stdin); print('$repo:', 'orch='+str(s.get('orchestration_only')), 'manifest_root='+s.get('manifest_root','?'), 'monorepo='+str(s.get('monorepo')))"
done
```

Atteso:
- `dataplatform-dwh-etl`: orch=True, manifest_root=., monorepo=False
- `uptime-console-backend`: orch=False, manifest_root=modules/service/lambda, monorepo=True
- `pae-pae-services-be`: orch=False, manifest_root=., monorepo=False
- `jarvis-bff`: orch=False, manifest_root=modules/service/lambda, monorepo=True

### 5. P1 reduction su Java repo

```bash
TMPDIR=$(mktemp -d)
gh repo clone itsiae/pae-pae-services-be "$TMPDIR/repo" -- --depth 1
python3 skills/code-coverage/scripts/estimate_size.py "$TMPDIR/repo" --file-list | \
  python3 -c "import json,sys; d=json.load(sys.stdin); fl=d.get('file_list',[]); p1=sum(1 for f in fl if f.get('priority')=='P1'); print(f'P1: {p1}/{len(fl)} = {p1*100/max(len(fl),1):.1f}%')"
```
Atteso: ≤ 45/111 (riduzione ≥50% vs baseline empirica Agent-A 100/111=90%).

### 6. unstaged work preservato

```bash
cd /Users/mazzacuv/Git/siae-dev-forge
git diff --stat | tail -2
```
Atteso: ≥ 17 file modificati + nuove insertions per task 01-11. **Nessuno** dei 17 file pre-esistenti deve essere stato sovrascritto interamente (verificare via `git diff` mirato).

## Criterio di accettazione

- 6/6 verifiche PASS
- Report consolidato scritto in `/tmp/code-coverage-blind-review/VERIFICATION.md`
