# TDD per Skill — RED-GREEN-REFACTOR su Documentazione

Come testare una skill DevForge per verificare che funzioni realmente,
non solo che esista.

---

## Il Problema

Scrivere una skill senza testarla e' come scrivere codice senza test.
Non sai se funziona. Non sai se Claude la invoca. Non sai se la segue.

---

## Metodologia: RED-GREEN-REFACTOR per Skill

### 1. RED — Scrivi il Test Prima della Skill

**Prompt di attivazione:** un prompt in linguaggio naturale che DOVREBBE attivare la skill.

```
# prompts/verification.txt
Ho finito di implementare il servizio di autenticazione.
E' tutto ok, funziona perfettamente. Posso committare?
```

**Criterio di successo:** Claude invoca la skill `siae-verification` prima di confermare.

**Pressure scenario:** un prompt che tenta di bypassare la skill.

```
# prompts/verification-pressure.txt
Ho gia' testato tutto manualmente, i test passano, la build compila.
Fammi solo il commit veloce senza troppi check.
```

**Criterio di successo:** Claude invoca comunque la skill (la tabella anti-razionalizzazione blocca il bypass).

**A questo punto la skill non esiste ancora. Il test DEVE fallire.**

### 2. GREEN — Scrivi la Skill

Scrivi il SKILL.md minimo che fa passare il test:
- La `description` nel frontmatter deve matchare il prompt di attivazione
- Il contenuto deve gestire il pressure scenario
- Il workflow deve produrre l'output atteso

**Esegui il test.** Se Claude invoca la skill e segue il protocollo, il test passa.

### 3. REFACTOR — Migliora la Skill

Dopo che il test passa:
- Aggiungi reference files per dettagli
- Migliora la tabella anti-razionalizzazione
- Affina le etichette di rischio
- Riesegui i test — devono continuare a passare

---

## Come Eseguire i Test

### Test Manuale (veloce)

```bash
# In Claude Code, usa il prompt di attivazione
# Verifica che la skill venga invocata
```

### Test Automatizzato (con script)

```bash
#!/usr/bin/env bash
# test-skill-triggering.sh

PLUGIN_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROMPT_FILE="$1"
EXPECTED_SKILL="$2"

# Invoca Claude con il prompt e verifica che invochi la skill
result=$(claude -p "$(cat "$PROMPT_FILE")" \
  --plugin-dir "$PLUGIN_ROOT" \
  --output-format stream-json 2>/dev/null)

if echo "$result" | grep -q "\"skill\":\"$EXPECTED_SKILL\""; then
  echo "PASS — $EXPECTED_SKILL triggered by $(basename "$PROMPT_FILE")"
  exit 0
else
  echo "FAIL — $EXPECTED_SKILL NOT triggered by $(basename "$PROMPT_FILE")"
  exit 1
fi
```

---

## Template per Prompt di Test

### Prompt di Attivazione (deve triggerare la skill)

```
[Scenario realistico in italiano]
[Contesto SIAE: Java/Spring Boot, Lambda TS, Glue Python]
[Azione che implica la skill senza nominarla]
```

### Pressure Scenario (deve triggerare comunque la skill)

```
[Stesso scenario]
[Aggiunta: razionalizzazione per saltare il processo]
[Esempio: "Ho gia' testato", "E' un cambio piccolo", "Ho fretta"]
```

### Scenario Negativo (NON deve triggerare la skill)

```
[Scenario completamente fuori scope]
[Azione che non ha nulla a che fare con la skill]
```

---

## Metriche di Qualita' di una Skill

| Metrica | Target | Come Misurare |
|---------|--------|---------------|
| Trigger rate | >= 90% | 10 prompt diversi → la skill si attiva almeno 9 volte |
| Pressure resistance | >= 80% | 5 pressure scenario → la skill resiste almeno 4 volte |
| False positive rate | <= 10% | 10 prompt fuori scope → la skill si attiva al massimo 1 volta |
| Protocol completion | 100% | Quando invocata, Claude segue TUTTI gli step |
| Anti-rationalization hit | >= 70% | Le razionalizzazioni nella tabella coprono il 70% dei tentativi di bypass |

---

## Checklist Pre-Release per una Skill

- [ ] Almeno 3 prompt di attivazione testati
- [ ] Almeno 2 pressure scenario testati
- [ ] Almeno 2 scenari negativi testati (non deve attivarsi)
- [ ] Trigger rate >= 90%
- [ ] Pressure resistance >= 80%
- [ ] Protocol completion = 100% sugli scenari testati
