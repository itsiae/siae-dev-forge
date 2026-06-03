# Esempio reference — RTD-108 Magic Link

Esempio di output completo della skill `siae-qa` v2.3.0 sulla story
**RTD-108 — Magic Link Authentication**. Usato come reference per:

- Dimostrare il formato dei 3 artefatti separati prodotti da Phase 5
- Mostrare un caso reale di applicazione dei Guardrail TC Negativi (R1-R5)
- Validare gli schemi JSON contro un output concreto

## Contesto

La TL originale RTD-108 generata da v2.2.0 conteneva **80 TC** di cui **54% non eseguibili
da QA manuale** (richiedevano modifiche a template, config SMTP, INSERT/UPDATE DB diretto,
fault injection, o erano mirror inversi del POS corrispondente). Questo era il bug fix
che ha motivato l'introduzione dei Guardrail R1-R5 in v2.3.0.

## Artefatti

| File | Descrizione |
|---|---|
| `RTD-108_TC.csv` | 42 TC manuali eseguibili, importabile direttamente in Xray (semicolon-separated, no commenti, Description semantiche 40-400 char senza metadata di tracciabilita') |
| `automated_only_notes.md` | 21 entry non eseguibili (8 R1 + 6 R2 + 7 R3) con suggerimento di copertura via test automatico (snapshot, contract, unit fuzzed, integration schema, chaos, load) |
| `coverage_certificate.json` | FULL_PASS · Gate #1+#2 PASS · J6 PASS 23/23 · 8 eliminated rows (R4 mirror) · 1 gap MEDIUM accettato |

## Statistiche

```
M_FINAL righe:            71 (totali post classificazione + 8 eliminate)
TC manuali (CSV):         42 (100% eseguibili da QA standard)
Automated-only notes:     21 (delegate a test automatici con suggerimento)
Eliminated mirror (R4):    8 (copertura garantita dai POS corrispondenti)
Coverage score:           100%
Gate #2 J6 executability: 23/23 PASS (R1-R5)
```

## Vincoli rispettati

- ✅ CSV pulito: nessuna riga commento `#`, nessuna entry `[AUTOMATED-ONLY]`/`[ELIMINATED]` (vincolo #21)
- ✅ Description semantiche: 40-400 char, no metadata `matrix_row_id`/`entity:`/`field:` (vincolo #4)
- ✅ Tracciabilita' tramite campo schema `matrix_row_id` separato (vincolo #1)
- ✅ Multi-step per mutating 4xx: action + side-effect NOT occurred (vincolo #15)
