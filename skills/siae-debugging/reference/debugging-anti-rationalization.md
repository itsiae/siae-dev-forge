# siae-debugging — Tabella Anti-Razionalizzazione

> Reference linked da `../SKILL.md`. Use when troubleshooting your own debug bias: confronta il pensiero che stai facendo con la colonna sinistra e applica la realta' della colonna destra.

| Pensiero | Realta' |
|----------|---------|
| "So gia' cos'e'" | Probabilmente no. Investiga prima. |
| "E' un fix veloce" | I fix veloci diventano bug lenti. |
| "Funzionava ieri" | Qualcosa e' cambiato. Trova cosa. |
| "Non riesco a riprodurlo" | Non l'hai capito abbastanza. Continua a investigare. |
| "E' un problema di infrastruttura" | Verifica prima di scaricare la colpa. |
| "Aggiungo un try-catch" | Stai nascondendo il problema, non risolvendo. |
| "Riavvio e vedo se si risolve" | Hai rimosso l'evidenza diagnostica. |
| "Il codice sembra giusto" | Il codice mente. I log no. |
| "Fix multipli insieme per risparmiare tempo" | Non puoi isolare cosa ha funzionato. Causa nuovi bug. |
| "Emergenza, non c'e' tempo per il processo" | Il debug sistematico e' PIU' VELOCE del guess-and-check. |
| "Prima fixo poi investigo" | Il primo fix imposta il pattern. Fallo bene dall'inizio. |
| "Un altro tentativo" (dopo 2+ fallimenti) | 3+ fallimenti = problema architetturale. Non fixare ancora. |
