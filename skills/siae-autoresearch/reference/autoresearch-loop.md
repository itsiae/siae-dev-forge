# Autoresearch Loop — Dettaglio Tecnico

## Integrazione con evals/

La skill autoresearch **non implementa logica di eval propria**. Usa esclusivamente i moduli esistenti in `evals/`:

| Modulo | Uso in Autoresearch |
|--------|-------------------|
| `runner.py --level L1` | Baseline e re-scoring (trigger precision/recall) |
| `runner.py --ab-test --description-b` | Confronto A vs B per ogni iterazione |
| `trigger_eval.py` | Motore sottostante (invocato da runner.py) |
| `grader.py` | NON usato direttamente (serve per L2/L3, non per trigger) |
| `ab_test.py` | Motore A/B sottostante (invocato da runner.py --ab-test) |

## Differenza con evals esistenti

```
evals/runner.py (MISURA)          siae-autoresearch (OTTIMIZZA)
──────────────────────             ──────────────────────────────
1. Riceve --skill e --level       1. Sceglie skill target
2. Esegue eval                    2. Esegue baseline via runner.py
3. Produce risultato JSON         3. Analizza risultato → trova punto debole
4. STOP                           4. Genera variante description
                                  5. Testa via runner.py --ab-test
                                  6. Keep/revert in base a risultato
                                  7. Ripete fino a target o max iterazioni
                                  8. Applica miglior description
                                  9. Estrae regole universali
```

**In sintesi:** runner.py e' il termometro, autoresearch e' il dottore.

## Formato Changelog

Il changelog e' il log strutturato di ogni iterazione. Viene mantenuto in conversazione
(non salvato su file) durante il loop, e le regole estratte vengono salvate in
`evals/workspace/autoresearch-rules.md` alla fine.

```
AUTORESEARCH CHANGELOG — siae-brainstorming
══════════════════════════════════════════════
Target: siae-brainstorming
Baseline: P=0.80 R=0.60 Acc=0.70
Obiettivo: Acc >= 0.90 per 3 run consecutive
Data inizio: 2026-03-22

Iter | Cambio                              | P    | R    | Acc  | Esito
-----|-------------------------------------|------|------|------|--------
0    | — (baseline)                        | 0.80 | 0.60 | 0.70 | base
1    | +keyword "architettura decisionale" | 0.80 | 0.70 | 0.75 | WIN
2    | +esclusione "NON per code review"   | 0.90 | 0.70 | 0.80 | WIN
3    | +keyword "trade-off alternative"    | 0.90 | 0.80 | 0.85 | WIN
4    | rimosso "design" (troppo generico)  | 0.85 | 0.80 | 0.83 | REVERT
5    | +keyword "approcci possibili"       | 0.90 | 0.90 | 0.90 | WIN ✓
6    | conferma stabilita'                 | 0.90 | 0.90 | 0.90 | WIN ✓✓
```

## Soglie e Criteri di Arresto

| Condizione | Azione |
|-----------|--------|
| Accuracy >= 0.90 per 3 run consecutive | SUCCESSO — applica e chiudi |
| 6 iterazioni senza target | STOP — riporta stato, suggerisci prossimi passi |
| 3 iterazioni consecutive senza miglioramento | PLATEAU — ferma loop, analisi manuale |
| Accuracy peggiora rispetto a baseline | REVERT immediato |

## Costi Stimati

Ogni iterazione A/B test esegue `runs_per_query * num_queries * 2` (A + B) invocazioni Claude.
Con default (3 run, 20 query): **120 invocazioni per iterazione**.

Per una sessione completa (6 iterazioni): ~720 invocazioni Sonnet.
Costo stimato: ~$2-4 su Bedrock (Sonnet pricing).

## Scope di Ottimizzazione

**v1 (corrente):** Solo campo `description` del frontmatter YAML
- E' l'unico campo che influenza il trigger di skill in Claude Code
- Cambiamento isolato, facilmente revertibile, misurabile con L1

**v2 (futuro):** Step ordering, constraint wording, anti-rationalization table
- Richiede eval L2 (functional) per misurare impatto
- Piu' costoso, loop piu' lento

**v3 (futuro):** Cross-skill chaining rules, disambiguazione
- Richiede eval custom multi-skill
- Complessita' significativamente maggiore
