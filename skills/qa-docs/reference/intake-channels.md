# MODULO INTAKE — 3 Canali

Richiamato in Fase 1, 3, 4, 5. I canali sono cumulabili tra loro.

---

## Canale 1 — JIRA (1..N issue key)

Pre-check obbligatorio (nell'ordine, fermati al primo successo):

1. **MCP Atlassian connesso?** → usa `mcp__atlassian__*` per leggere l'issue
2. **Token API in env** (`ATLASSIAN_TOKEN`, `JIRA_TOKEN`, `JIRA_API_TOKEN`)? → usa REST:
   ```
   GET /rest/api/3/issue/{key}
   Authorization: Bearer <token>
   ```
3. **Nessuno dei due** → comunica il blocco chiaramente, proponi Canale 2 o 3

Per ogni issue estratta, raccoglie:
- `summary` — titolo
- `description` — descrizione funzionale
- `acceptance criteria` — se presenti (campo custom o sezione nel body)
- `subtask` — lista sottoattività
- `linked issues` — dipendenze e relazioni
- `commenti rilevanti` — commenti tecnici/funzionali significativi
- `allegati testuali` — se scaricabili e leggibili

---

## Canale 2 — Chat testuale

Raccogli dall'utente tramite domande conversazionali:
- Titolo del progetto / nome breve
- Codice DMND o issue key
- Descrizione funzionale (cosa fa, cosa cambia)
- Requisiti o criteri di accettazione
- Sistemi e piattaforme impattati (anche approssimativi)
- Vincoli, esclusioni, note

Accetta testo libero o incollato dall'utente. Non vincolare il formato.

---

## Canale 3 — Ingestion documenti

### Pre-check
Verifica file presenti in `/mnt/user-data/uploads/` o nel percorso indicato dall'utente:
```bash
ls /mnt/user-data/uploads/ 2>/dev/null || echo "cartella uploads non trovata"
```
Se vuota o non trovata: chiedi all'utente di caricare i file o ripiegare su Canale 2.

### Estrazione per tipo file

| Tipo | Metodo |
|---|---|
| `.docx` / `.odt` | Read diretto + python-docx per estrarre testo strutturato, oppure skill `docx` |
| `.pdf` | Skill `pdf-reading` (testo estratto; se scansione → OCR/vision) |
| `.xlsx` / `.csv` | pandas `read_excel`/`read_csv` o skill `xlsx` |
| `.pptx` | Skill `pptx` o python-pptx per estrarre testo slide |
| `.txt` / `.md` | Read diretto |
| Immagini (`.png`, `.jpg`) | Vision/OCR |

### Normalizzazione
- Converti tutto in testo strutturato (markdown leggibile)
- Cita la provenienza `[nome_file, sezione/pagina]` per ogni informazione importante
- Non omettere informazioni rilevanti anche se il formato di origine è complesso

---

## Fusione multi-canale

Quando si usano più canali contemporaneamente:

1. Raccogli tutto il materiale grezzo da ogni canale
2. Unifica in un unico `intake_grezzo` coerente per canale:
   ```yaml
   intake_grezzo:
     jira: [{key: "DMND-123", contenuto: "..."}]
     chat: "testo fornito dall'utente..."
     documenti: [{nome: "spec.pdf", contenuto: "..."}]
   ```
3. Segnala **conflitti tra fonti** come:
   > «DA CONFERMARE: [fonte A] dice X, [fonte B] dice Y»
4. Riporta l'elenco delle fonti usate prima di procedere all'analisi

---

## Regola di fallback generale

Se un canale non è disponibile o fallisce, comunica chiaramente il motivo
e proponi immediatamente il canale alternativo senza bloccarsi.
Non tentare il canale successivo silenziosamente: informa sempre l'utente.
