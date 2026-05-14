# Task 08 — detector.py criteri 6-10

**Stato:** [DONE]
**SP:** 1.5 Human / 0.5 Augmented
**Dipendenze:** task-06

## Goal

Estendere `lib/release_risk/detector.py` con criteri 6-10: first release, complex rollback, downtime, data migration, feature flag.

## File coinvolti

- Edit: `lib/release_risk/detector.py` (append funzioni)

## Step

### Step 1 — Append a detector.py

Edit `lib/release_risk/detector.py` aggiungendo:
```python
def criterion_6_first_release(git_tag_count: int) -> CriterionResult:
    """+2 se prima release del servizio (nessun tag release precedente)."""
    if git_tag_count == 0:
        return CriterionResult(id=6, name="First release", status="YES", weight=2,
                               evidence=[f"git_tag_count={git_tag_count}"],
                               source="git:tag")
    return CriterionResult(id=6, name="First release", status="NO", weight=2,
                           evidence=[f"git_tag_count={git_tag_count}"], source="git:tag")


def criterion_7_complex_rollback(c1_status: str, c9_status: str, diff_content: str) -> CriterionResult:
    """+2 se rollback complesso. Implied da Criterion 1 (DB change) o 9 (migration)."""
    if c1_status == "YES" or c9_status == "YES":
        return CriterionResult(id=7, name="Complex rollback", status="YES", weight=2,
                               evidence=["implied_by_c1_or_c9"], source="inferred")
    if re.search(r"irreversible|no rollback|one[- ]way|destructive", diff_content, re.I):
        return CriterionResult(id=7, name="Complex rollback", status="YES", weight=2,
                               evidence=["irreversible_keyword"], source="diff:grep")
    return CriterionResult(id=7, name="Complex rollback", status="NO", weight=2, source="inferred")


def criterion_8_downtime(diff_content: str) -> CriterionResult:
    """+3 se downtime richiesto (strategy Recreate o maxUnavailable: 1)."""
    pattern = re.compile(r"strategy:\s*Recreate|maxUnavailable:\s*1", re.I)
    if pattern.search(diff_content):
        return CriterionResult(id=8, name="Downtime required", status="YES", weight=3,
                               evidence=["recreate_strategy_or_maxunavailable_1"],
                               source="diff:grep")
    return CriterionResult(id=8, name="Downtime required", status="NO", weight=3, source="diff:grep")


def criterion_9_data_migration(diff_files: list[str], diff_content: str) -> CriterionResult:
    """+3 se data migration (script V*__*.sql, MigrationRunner classes)."""
    file_pattern = re.compile(r"migration|migrate|V\d+__|R__", re.I)
    content_pattern = re.compile(r"DataMigration|MigrationRunner|@Migration", re.I)
    matched = [f for f in diff_files if file_pattern.search(f)]
    if matched or content_pattern.search(diff_content):
        ev = [f"file:{f}" for f in matched[:5]]
        return CriterionResult(id=9, name="Data migration required", status="YES", weight=3,
                               evidence=ev, source="diff:grep")
    return CriterionResult(id=9, name="Data migration required", status="NO", weight=3,
                           source="diff:grep")


def criterion_10_feature_flag(diff_content: str) -> CriterionResult:
    """-1 se feature flag disabilitabile (mitigazione)."""
    pattern = re.compile(
        r"featureFlag|feature\.flag|FeatureToggle|@ConditionalOnProperty|ff4j|unleash|LaunchDarkly|isEnabled",
        re.I,
    )
    if pattern.search(diff_content):
        return CriterionResult(id=10, name="Feature flag (mitigation)", status="YES",
                               weight=-1, evidence=["flag_pattern_detected"],
                               source="diff:grep")
    return CriterionResult(id=10, name="Feature flag (mitigation)", status="NO",
                           weight=-1, source="diff:grep")
```

### Step 2 — Verifica import

Run:
```bash
python3 -c "from lib.release_risk.detector import criterion_6_first_release, criterion_7_complex_rollback, criterion_8_downtime, criterion_9_data_migration, criterion_10_feature_flag; print('OK')"
```
Output atteso: `OK`

### Step 3 — Commit

```bash
git add lib/release_risk/detector.py
git commit -m "feat(release-risk): detector criteri 6-10 (first release, rollback, downtime, migration, flag)"
```

## Criteri di accettazione

- [ ] 5 funzioni aggiunte
- [ ] Criterion 7 inference logic (implied da c1/c9)
- [ ] Criterion 10 weight negative (-1 mitigation)
- [ ] Commit eseguito
