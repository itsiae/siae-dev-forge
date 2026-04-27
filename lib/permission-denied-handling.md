# Permission Denied Handling — Standard DevForge

Strategie uniformi quando un tool è negato in skill DevForge.

## Se Write negato
1. Presenta il contenuto come output testuale formattato in chat
2. Indica il path suggerito
3. L'utente copia manualmente
4. Procedi con il step successivo normalmente

## Se Bash negato (generico)
1. Informa cosa serviva eseguire
2. Fornisci il comando esatto
3. Se è un check (git log, ls), degrada a tool alternativi (Read, Glob)
4. Se è un'azione (commit, push), istruisci l'utente

## Se Bash (git commit) negato
1. File già scritto, non committato
2. Istruisci: `git add <file> && git commit -m "<msg>"`
3. Procedi normalmente

## Se Edit negato
1. Mostra la modifica desiderata in chat (before/after)
2. Utente applica manualmente
3. Non re-tentare automaticamente

## Principio
Il valore primario della skill si preserva sempre via degradazione graceful.
Non abbandonare la skill: cambia modalità.
