---
name: siae-dwh-etl-edw-add-submodule
description: >
  Use in the dataplatform-dwh-etl repo when adding a new leaf submodule under
  an EDW first-level module (e.g. mus, com, itc). Trigger: "aggiungi sottomodulo edw",
  "nuovo modulo sotto mus/com/itc", "crea modulo edw", "aggiungi ramo edw", "nuovo flusso edw".
---

# EDW Add Submodule — DevForge

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║        🔨 DevForge · EDW ADD SUBMODULE (dwh-etl)              ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 4. Implementation

---

## LA LEGGE DI FERRO

```
MAI CREARE UN SOTTOMODULO EDW SENZA VERIFICARE I PERMESSI IAM — UN ARN MANCANTE CAUSA RUNTIME FAILURE SILENZIOSA.
```

---

## Input Richiesti

| Parametro | Obbligatorio | Esempio | Default |
|-----------|-------------|---------|---------|
| `parent_module` | ✅ | `mus` | — |
| `code` | ✅ | `cod` | — |
| `name_ext` | ✅ | `codifica` | — |
| `resource_name` | ✅ | `bm-utilizzazioni` | — |
| `group_id` | ✅ | `4695` | — |
| `crawler_name` | ❌ | `${env}-datalake-bronze-bm-utilizzazioni-crawler-parquet` | `${env}-datalake-bronze-{resource_name}-crawler-parquet` |
| `ingestion_sfn` | ❌ | `${env}-bm-utilizzazioni-ingestion-orchestration` | *(assente = nessuno step ingestion)* |

**Nomi derivati automaticamente:**
- SFN leaf: `${env}-edw-{parent_module}-{code}-orchestration`
- File TF: `edw-{parent_module}-{code}-orchestration.tf`
- File JSON: `edw-{parent_module}-{code}-orchestration.json`
- Directory: `modules/edw/{parent_module}/{code}/`

---

## Quando si Applica

**Sempre:**
- Aggiunta di un nuovo flusso silver→gold sotto un modulo EDW esistente (mus, com, itc, …)
- Il modulo è un **leaf** (nessun altro livello sotto di lui, come uti o cod)
- Il template di riferimento è sempre `uti` — struttura invariante

**Eccezioni (chiedi esplicitamente):**
- Il `parent_module` non esiste sotto `modules/edw/` → fermati e segnala
- Esiste già una directory `modules/edw/{parent_module}/{code}/` → chiedi se sovrascrivere

---

## Step 1 — Valida i Parametri

🟢 SICURO

Verifica che `parent_module`, `code`, `name_ext`, `resource_name` e `group_id` siano forniti. Se mancano, chiedi:

```
Parametri necessari per aggiungere il sottomodulo EDW:
- parent_module (es. mus, com, itc):
- code (sigla breve, es. cod, uti, pmo):
- name_ext (nome esteso usato negli stati JSON, es. codifica, utilizzazioni):
- resource_name (nome risorsa AWS usato in crawler e ingestion, es. bm-utilizzazioni, codifica):
- group_id (ID gruppo Redshift gold, es. 4695):
- crawler_name (opzionale, default: ${env}-datalake-bronze-{resource_name}-crawler-parquet):
- ingestion_sfn (opzionale, nome SFN ingestion esterna — ometti se non serve):
```

Verifica che `modules/edw/{parent_module}/` esista:

```bash
ls modules/edw/{parent_module}/
```

Se non esiste → segnala e fermati.

Verifica che `modules/edw/{parent_module}/{code}/` NON esista già:

```bash
ls modules/edw/{parent_module}/{code}/ 2>/dev/null && echo EXISTS || echo OK
```

Se esiste → chiedi conferma prima di sovrascrivere.

---

## Step 2 — Crea i File del Sottomodulo

🟡 MEDIO — Mostra pre-flight card prima di eseguire

| 🟡 MEDIO (file locali reversibili) — 🔨 DevForge · siae-dwh-etl-edw-add-submodule |
|:---|
| 🛠️ Operazione: `Creazione modulo {code}` · 📁 Path: `modules/edw/{parent_module}/{code}/` |
| **▼ Azioni** |
| 1. 📂 Crea `modules/edw/{parent_module}/{code}/` |
| 2. ✏️ Crea `_input.tf` (copia da uti, aggiorna description crawler) |
| 3. ✏️ Crea `edw-{parent_module}-{code}-orchestration.tf` |
| 4. ✏️ Crea `edw-{parent_module}-{code}-orchestration.json` |
| 💡 Perché: I file sono il template per la nuova SFN — un errore di naming blocca il deploy |
| 🚫 Se NO: Nessun file viene creato |

**`_input.tf`** — copia da `modules/edw/mus/uti/_input.tf`, sostituisci solo la description del `crawler_sf_name`:
```
description = "Name of the shared crawler state machine invoked for bronze-{code}-crawler step."
```
Le variabili (`env`, `region`, `account_id`, `role_arn`, `crawler_sf_name`) restano invariate.

**`.tf`** — sostituzioni su `edw-mus-uti-orchestration.tf`:
- `sfn_edw_mus_uti_orchestration` → `sfn_edw_{parent_module}_{code}_orchestration`
- `${var.env}-edw-mus-uti-orchestration` → `${var.env}-edw-{parent_module}-{code}-orchestration`
- `edw-mus-uti-orchestration.json` → `edw-{parent_module}-{code}-orchestration.json`

**`.json`** — sostituzioni su `edw-mus-uti-orchestration.json`:
- `uti` → `{code}` (tutti i nomi stato, chiavi, label)
- `utilizzazioni` → `{name_ext}`
- `utilizzazione` → `{name_ext}` (se presente)
- crawler_name: usa `{crawler_name}` (o default `${env}-datalake-bronze-{resource_name}-crawler-parquet`)
- Silver SFN ARN: `${env}-datalake-etl-silver-{name_ext}-orchestration`
- Gold step `GroupId`: usa `{group_id}` — parametro obbligatorio, non lasciare il valore di uti
- Se `ingestion_sfn` è fornito: aggiungi `bronze-{code}-ingestion` come primo stato (prima del crawler), con ARN `arn:aws:states:${region}:${account_id}:stateMachine:{ingestion_sfn}` e Comment `External SFN — owned by bronze-{resource_name} module. Deploy that module before this one.` — `StartAt` diventa `bronze-{code}-ingestion`
- Se `ingestion_sfn` non è fornito: `StartAt` è direttamente `bronze-{code}-crawler` (nessuno step ingestion)

---

## Step 3 — Aggiorna l'Orchestration del Parent Module (.tf e .json)

🟡 MEDIO — Mostra pre-flight card prima di eseguire

| 🟡 MEDIO — 🔨 DevForge · siae-dwh-etl-edw-add-submodule |
|:---|
| 🛠️ Operazione: `Aggiunta blocco module "{code}" e branch nel JSON` · 📁 `modules/edw/{parent_module}/` |
| **▼ Azioni** |
| 1. ✏️ Aggiunge blocco `module "{code}"` in fondo a `edw-{parent_module}-orchestration.tf` |
| 2. ✏️ Aggiunge branch `{code}` nel Parallel state di `edw-{parent_module}-orchestration.json` |
| 💡 Perché: Il .tf crea la risorsa SFN leaf; il .json la inserisce nel flusso parallelo del parent — senza entrambi il modulo esiste su AWS ma non viene mai invocato |
| 🚫 Se NO: I file non vengono modificati e il modulo non è né registrato né invocato |

**Modifica `.tf`** — aggiungi in fondo al file, dopo l'ultimo blocco `module`:

```hcl
module "{code}" {
  source          = "./{code}"
  env             = var.env
  crawler_sf_name = var.crawler_sf_name
  region          = var.region
  account_id      = var.account_id
  role_arn        = var.role_arn
}
```

**Modifica `.json`** — aggiungi un nuovo branch nell'array `Branches` del Parallel state principale, in fondo agli altri branch esistenti (stesso pattern di `uti`):

```json
{
    "StartAt": "{code}",
    "States": {
        "{code}": {
            "Type": "Parallel",
            "Branches": [
                {
                    "StartAt": "{code}-orchestration",
                    "States": {
                        "{code}-orchestration": {
                            "Type": "Task",
                            "Resource": "arn:aws:states:::states:startExecution.sync:2",
                            "Parameters": {
                                "StateMachineArn": "arn:aws:states:${region}:${account_id}:stateMachine:${env}-edw-{parent_module}-{code}-orchestration"
                            },
                            "End": true
                        }
                    }
                }
            ],
            "Next": "{code}-error-handler",
            "Catch": [
                {
                    "ErrorEquals": ["States.ALL"],
                    "ResultPath": "$.parallelError",
                    "Next": "{code}-error-handler"
                }
            ],
            "ResultPath": "$.parallelResults"
        },
        "{code}-error-handler": {
            "Type": "Pass",
            "Result": { "status": "ONE_OR_MORE_SILVER_FAILED_CONTINUED" },
            "End": true
        }
    }
}
```

---

## Step 4 — Verifica e Aggiorna i Permessi IAM

🔴 CRITICO — Mostra pre-flight card prima di eseguire

Leggi i pattern ARN presenti in `modules/edw/edw-orchestration-role.tf` nella risorsa `sfn2_edw_statemachine_permissions`.

Vedi [reference/iam-patterns.md](reference/iam-patterns.md) per i wildcard attivi.

**Per ogni ARN nuova introdotta dal modulo**, verifica se è coperta:

| ARN da verificare | Coperta da wildcard? |
|---|---|
| `${env}-edw-{parent_module}-{code}-orchestration` | ✅ `${env}-edw-*` |
| `${env}-datalake-etl-silver-{name_ext}-orchestration` | ✅ `${env}-datalake-*` |
| `{ingestion_sfn}` (se fornita) | ⚠️ **DA VERIFICARE** — se il nome non inizia con `{env}-edw-` o `{env}-datalake-` NON è coperta |

Se `ingestion_sfn` non è coperta da nessun wildcard esistente, **prima di modificare `edw-orchestration-role.tf`** mostra la card CRITICO:

| 🔴 CRITICO (aggiunta ARN IAM) — 🔨 DevForge · siae-dwh-etl-edw-add-submodule |
|:---|
| **⚠️ OPERAZIONE REMOTA — WRITE/UPDATE SU AWS IAM** |
| 📋 Risorsa: `edw-orchestration-role.tf` · `sfn2_edw_statemachine_permissions` · 🌍 Ambiente: tutti gli env (dev/uat/prod) |
| **▼ Azioni** |
| 1. Aggiunge `arn:aws:states:${var.region}:${var.account_id}:stateMachine:{ingestion_sfn}` all'array `Resource` |
| 2. Aggiunge `arn:aws:states:${var.region}:${var.account_id}:execution:{ingestion_sfn}:*` all'array `Resource` |
| 💡 Perché: `edw-orchestration-role.tf` è una policy IAM **condivisa** — la modifica impatta TUTTI i sottomoduli EDW attivi (mus, com, itc, …) e tutte le SFN che usano il ruolo `edw-orchestration-role`. Un ARN errato o un wildcard troppo permissivo è un rischio sicurezza su tutti gli ambienti AWS. |
| 🚫 Se NO: Le ARN di `{ingestion_sfn}` non vengono aggiunte — la SFN leaf otterrà `States.TaskFailed` a runtime quando tenta di invocare l'ingestion esterna |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, aggiungi **entrambe** le ARN:

```hcl
"arn:aws:states:${var.region}:${var.account_id}:stateMachine:{ingestion_sfn}",
"arn:aws:states:${var.region}:${var.account_id}:execution:{ingestion_sfn}:*"
```

Inseriscile in fondo all'array `Resource` del blocco `sfn2_edw_statemachine_permissions`, dopo le ARN esistenti.

Se nessuna nuova ARN è necessaria (tutti i pattern sono coperti da wildcard esistenti), documenta esplicitamente il motivo (quale wildcard copre) — **nessuna modifica a `edw-orchestration-role.tf` è necessaria in questo caso**.

---

## Step 5 — Riepilogo Finale

🟢 SICURO

Mostra riepilogo strutturato:

```
✅ Sottomodulo EDW creato
   Parent:    modules/edw/{parent_module}/
   Directory: modules/edw/{parent_module}/{code}/
   File:
     - _input.tf
     - edw-{parent_module}-{code}-orchestration.tf
     - edw-{parent_module}-{code}-orchestration.json
   SFN:       ${env}-edw-{parent_module}-{code}-orchestration
   resource_name: {resource_name}
   Crawler:   {crawler_name_effettivo}
   GroupId:   {group_id}
   Ingestion: {ingestion_sfn} oppure "nessuno step ingestion"
   IAM:       {coperto da wildcard / aggiunte N ARN}

⚠️  Verifica manuale richiesta:
   - Silver SFN deve esistere prima del deploy: ${env}-datalake-etl-silver-{name_ext}-orchestration
```

---

## Fallback Obbligatori

### Parent module non trovato
Se `modules/edw/{parent_module}/` non esiste:
```
❌ Parent module "{parent_module}" non trovato sotto modules/edw/.
Moduli disponibili: <lista ls modules/edw/>
Vuoi usare uno di questi o stai lavorando su un nuovo parent?
```

### Directory già esistente
Se `modules/edw/{parent_module}/{code}/` esiste già:
```
⚠️ La directory modules/edw/{parent_module}/{code}/ esiste già.
Vuoi sovrascrivere i file esistenti? Rispondi "sì, sovrascrivi" oppure "no, annulla".
```

### Tool call negato dopo conferma
1. NON riprovare automaticamente
2. Fornire i comandi esatti da eseguire manualmente
3. Aspettare conferma di esecuzione manuale

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realtà |
|----------|--------|
| "Il nome della SFN inizia con env-, è sicuramente coperto" | Non tutti i prefissi rientrano nei wildcard — verifica sempre il pattern esatto contro i 6 wildcard attivi in `edw-orchestration-role.tf` |
| "Ometto lo step ingestion, tanto si può aggiungere dopo" | Se `ingestion_sfn` è fornita va aggiunto ora — aggiungerlo dopo richiede un nuovo deploy e può bloccare esecuzioni intermedie |
| "Copio solo il .json del leaf, il .tf è uguale per tutti" | Il nome della risorsa Terraform e il `name` della SFN devono contenere `{parent_module}` e `{code}` — un nome sbagliato crea conflitti di stato |
| "Il blocco module nel .tf basta, il parent .json lo aggiornerò dopo" | Senza il branch nel JSON del parent la SFN leaf esiste su AWS ma non viene mai invocata — il flusso è silenziosamente rotto |
| "Il GroupId lo lascio uguale a uti (4594), tanto è un placeholder" | `group_id` è parametro obbligatorio — il GroupId determina quali script Redshift vengono eseguiti, un valore sbagliato causa elaborazione dati errata in produzione |
| "Aggiungo il blocco module ovunque nel file, l'ordine non conta" | Aggiungilo sempre in fondo alla lista — coerenza strutturale e leggibilità del file sono parte degli standard SIAE |
| "Se il piano Terraform non mostra errori, i permessi IAM vanno bene" | Il plan non verifica i permessi IAM a runtime — una policy mancante causa `States.TaskFailed` solo durante l'esecuzione della SFN |
| "La silver SFN la creerà il team datalake, non devo verificare" | Segnalalo esplicitamente nel riepilogo — il deploy può avere successo ma la SFN fallirà a runtime se la silver non esiste |
| "Il crawler_name default è ovvio, non serve specificarlo nel riepilogo" | Mostra sempre il valore effettivo usato — un default silenzioso è una fonte di bug difficili da diagnosticare |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Validazione parametri e verifica directory | 🟢 Sicuro | No |
| Lettura file uti come template | 🟢 Sicuro | No |
| Creazione file in `modules/edw/{parent_module}/{code}/` | 🟡 Medio | Sì |
| Modifica `edw-{parent_module}-orchestration.tf` | 🟡 Medio | Sì |
| Modifica `edw-{parent_module}-orchestration.json` (aggiunta branch parallel) | 🟡 Medio | Sì (inclusa nella card Step 3) |
| Modifica `edw-orchestration-role.tf` (aggiunta ARN IAM) | 🔴 Critico | Sì — gate CRITICO con conferma esplicita |

---

## Vincoli

1. **SEMPRE** usare `modules/edw/mus/uti/` come template — non altri sottomoduli
2. **MAI** modificare il `_input.tf` oltre alla description del `crawler_sf_name`
3. **SEMPRE** verificare tutti e 6 i wildcard ARN prima di dichiarare i permessi coperti
4. **SEMPRE** mostrare il riepilogo finale con il GroupId usato e il warning sulla silver SFN
5. **PRE-FLIGHT OBBLIGATORIA** per creazione file e modifiche TF (rischio >= 🟡)
6. **MAI** aggiungere `bronze-{code}-ingestion` se `ingestion_sfn` non è fornita

---

## Risorse Aggiuntive

- [reference/iam-patterns.md](reference/iam-patterns.md) — wildcard ARN attivi in `edw-orchestration-role.tf`
