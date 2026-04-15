# Privacy Guidelines — siae-dev-analytics

## GDPR Compliance

**Base legale:** legittimo interesse (valutazione ROI tool aziendale).

**Minimizzazione:** solo dati già pubblici internamente (GitHub org privata itsiae).

**Scopo dichiarato:** ROI Claude Code + reportistica management.

**No decisioni automatiche:** la skill produce report, non valutazioni HR.

## Gate obbligatorio

Card 🔴 ALTO prima di ogni run nominativo. Vedi SKILL.md → Step 4.

## Anonymize opt-in

Flag `--anonymize` → hash SHA256[:8] su ogni login GitHub.
Determinisico: stesso login → stesso hash (cross-report consistency).

## Retention

- Cache `.cache/github/`: 7 giorni default (TTL auto)
- Excel output: responsabilità utente (conservare in spazio confidenziale)
- No upload automatico esterno

## File sensibili auto in `.gitignore`

- `.cache/github/` — dati PR/commit cachati
- `devforge-analytics-report.*.xlsx` — output nominativi
- `devforge-analytics.yml` se contiene `developers.include` nominativo
