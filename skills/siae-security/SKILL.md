---
name: siae-security
description: >
  Use when handling security-sensitive code: credentials, IAM policy, encryption,
  PII (autori/artisti), copyright codes (ISWC/ISRC). Applies OWASP Top 10 + AWS
  security policy SIAE.
  Trigger: codice security-sensitive, gestione credenziali, IAM policy, encryption,
  dati personali autori/artisti, codici ISWC/ISRC.
---

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║                                                                  ║
║              🔨  DevForge  ·  AI Competence Center               ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

# siae-security

> **Tipo:** Flexible | **Fase SDLC:** Trasversale (tutte le fasi)
>
> Questa skill si attiva su codice security-sensitive: gestione credenziali,
> IAM policy, encryption, dati personali autori/artisti, codici ISWC/ISRC.
> Applica OWASP Top 10, best practice AWS e regole PII specifiche SIAE.

---

> 📊 **Dai repo itsiae:** Su 816 repo, 23 avevano secrets committati in history. Il 100% era in repo senza pre-commit hook attivo.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## 1. OWASP Top 10 — Checklist AWS

Checklist adattata al contesto AWS/serverless SIAE.

| # | Vulnerabilita' | Mitigazione SIAE |
|---|----------------|------------------|
| A01 | **Broken Access Control** | IAM least privilege. Cognito authorizer su API Gateway. RBAC applicativo. |
| A02 | **Cryptographic Failures** | KMS per encryption at rest. TLS 1.2+ in transit. No dati sensibili in query string. |
| A03 | **Injection** | Prepared statements (JPA/Drizzle). Input validation. No string concatenation in query. |
| A04 | **Insecure Design** | Threat modeling pre-sviluppo. Separation of concerns. Defense in depth. |
| A05 | **Security Misconfiguration** | No default credentials. Security headers. S3 Block Public Access. |
| A06 | **Vulnerable Components** | Dependabot attivo. Aggiornamento dipendenze trimestrale. SBOM tracking. |
| A07 | **Auth Failures** | Cognito JWT verification (`aws-jwt-verify`). Session timeout. MFA dove richiesto. |
| A08 | **Data Integrity Failures** | Verifica firma artefatti CI/CD. OIDC per GitHub Actions (no long-lived keys). |
| A09 | **Logging Failures** | Structured logging obbligatorio. CloudTrail attivo. Alert su eventi security. |
| A10 | **SSRF** | Validazione URL in Lambda. No fetch di URL arbitrari da input utente. VPC endpoint dove possibile. |

---

## 2. AWS Security SIAE

### 2.1 IAM — Least Privilege

- **Mai** policy con `"Action": "*"` o `"Resource": "*"`
- Usa policy specifiche per servizio e risorsa
- OIDC per GitHub Actions (pattern dal repo `gh-roles`): niente access key long-lived

```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:PutObject"],
  "Resource": "arn:aws:s3:::bucket-name/prefix/*"
}
```

### 2.2 Cognito — JWT Verification

Pattern da `accertatori-route-service` con `aws-jwt-verify`:

```typescript
import { CognitoJwtVerifier } from "aws-jwt-verify";

const verifier = CognitoJwtVerifier.create({
  userPoolId: process.env.COGNITO_USER_POOL_ID,
  tokenUse: "access",
  clientId: process.env.COGNITO_CLIENT_ID,
});

// Verifica in middleware o authorizer Lambda
const payload = await verifier.verify(token);
```

### 2.3 KMS — Encryption at Rest

- **S3**: SSE-S3 (default) o SSE-KMS per dati sensibili
- **DynamoDB**: encryption at rest abilitata (default AWS)
- **RDS/Aurora**: KMS managed key
- **Secrets Manager**: encryption automatica via KMS

### 2.4 Secrets Manager

**Mai hardcode di segreti.** Usa sempre AWS Secrets Manager:

- CLI: `aws secretsmanager get-secret-value --secret-id {secret-name}`
- SDK: `SecretsManagerClient` + `GetSecretValueCommand` da `@aws-sdk/client-secrets-manager`
- Spring Boot: integrazione via `spring-cloud-aws-secrets-manager`

### 2.5 VPC

- Lambda in VPC **dove necessario** (accesso RDS, ElastiCache, risorse interne)
- Lambda senza VPC per servizi che accedono solo a risorse AWS pubbliche (S3, DynamoDB, SQS)
- VPC endpoint per S3 e DynamoDB in subnet private

### 2.6 S3

- **Nessun bucket pubblico.** S3 Block Public Access abilitato a livello account
- Encryption: SSE-S3 o SSE-KMS
- Versioning abilitato per bucket con dati critici
- Lifecycle policy per dati temporanei

---

## 3. PII e Dominio Copyright

### 3.1 Dati Personali Autori/Artisti

Il dominio SIAE tratta dati di autori, artisti, editori. Trattamento GDPR conforme:

| Dato | Classificazione | Regola |
|------|----------------|--------|
| Nome/Cognome autore | PII | Encryption at rest. Accesso controllato. |
| Codice fiscale | PII sensibile | Encryption obbligatoria. Mai in log o URL. |
| IBAN / dati bancari | PII finanziario | Encryption at rest e in transit. Audit trail. |
| Email | PII | Mai in log. Mascherare in output (`m***@siae.it`). |
| Indirizzo | PII | Encryption at rest. Accesso controllato. |

### 3.2 Codici ISWC/ISRC

Validazione formato obbligatoria:

| Codice | Formato | Esempio |
|--------|---------|---------|
| **ISWC** | `T-NNN.NNN.NNN-C` | `T-034.524.680-1` |
| **ISRC** | `CC-XXX-YY-NNNNN` | `IT-AB1-24-00001` |

```typescript
// Regex validazione
const ISWC_REGEX = /^T-\d{3}\.\d{3}\.\d{3}-\d$/;
const ISRC_REGEX = /^[A-Z]{2}-[A-Z0-9]{3}-\d{2}-\d{5}$/;
```

### 3.3 Dati Finanziari Ripartizione

- Encryption **obbligatoria** at rest e in transit
- Audit trail su ogni accesso e modifica
- Separazione ambienti: dati di produzione mai in sviluppo/collaudo

### 3.4 Log e PII

**MAI PII nei log.** Mascherare sempre:

```java
// SBAGLIATO
log.info("Pagamento per autore: {}, CF: {}", nome, codiceFiscale);

// CORRETTO
log.info("Pagamento per autore ID: {}, operazione: {}", autorId, operazioneId);
```

---

## 4. Secret Scanning

### 4.1 Pre-flight Card

Quando un file contiene pattern sospetti, mostra la card:

| 🚨 CRITICO (irreversibile) — 🔨 DevForge · siae-security |
|:---|
| **⚠️ STOP — Secret rilevato nel file** |
| 🔑 Pattern: `Secret rilevato` · 📁 File: `[percorso del file]` |
| **▼ Azione** |
| 1. ⚠️ Azione: Rimozione/sostituzione pattern segreto → `[percorso del file]` |
| 💡 Perche': Il file contiene potenziali credenziali |
| 🚫 Se NO: Le credenziali potrebbero finire nel repository |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

### 4.2 Pattern Regex da Intercettare

```regex
# AWS Keys
AKIA[0-9A-Z]{16}
aws_secret_access_key\s*=\s*.+

# Generic secrets
[pP]assword\s*[:=]\s*["'][^"']+["']
[aA][pP][iI][-_]?[kK][eE][yY]\s*[:=]\s*["'][^"']+["']
[tT]oken\s*[:=]\s*["'][^"']+["']
[sS]ecret\s*[:=]\s*["'][^"']+["']

# .env content in source
process\.env\.\w+\s*\|\|\s*["'][^"']+["']
```

### 4.3 File da Controllare

| File | Rischio | Azione |
|------|---------|--------|
| `.env`, `.env.*` | 🚨 Critico | Mai in git. Verificare `.gitignore`. |
| `.aws/credentials` | 🚨 Critico | Mai in git. Mai copiare in progetto. |
| Stringhe hardcoded con pattern secret | 🚨 Critico | Estrarre in Secrets Manager. |
| `application-*.yml` con password | 🚨 Critico | Usare variabili d'ambiente o Secrets Manager. |

---

## 5. Context-Aware Triage

<EXTREMELY-IMPORTANT>
NON classificare la gravita' di un finding basandoti solo sul pattern.
Il contesto infrastrutturale e applicativo cambia TUTTO.

Un Security Group 0.0.0.0/0 in subnet privata senza IGW = igiene, non emergenza.
Lo stesso SG in subnet pubblica = CRITICO.

Il pattern da solo non basta. Verifica SEMPRE il contesto prima di classificare.
</EXTREMELY-IMPORTANT>

### 5.1 Framework di Verifica — 5 Step

Applica questi 5 step a QUALSIASI finding di sicurezza, in ordine:

```
FINDING RILEVATO
  |
  STEP 1: FALSO POSITIVO?
  |    Il valore e' richiesto dal protocollo/API esterna?
  |    Il pattern matcha ma il contesto semantico e' diverso?
  |    (es. campo "password" che e' un label UI, non una credenziale)
  |    (es. "securitypassword" che e' un parametro fisso dell'API)
  |    → SI' = NON VULNERABILITA' — documenta il perche'
  |
  STEP 2: REACHABILITY
  |    Il componente e' raggiungibile dall'esterno?
  |    Verifica: subnet pubblica/privata, IGW, NAT, VPN-only,
  |    publicly_accessible flag, routing table, VPC peering
  |    → NO = gravita' ridotta (igiene da correggere, non emergenza)
  |
  STEP 3: MITIGAZIONI COMPENSATIVE
  |    Ci sono controlli che riducono il rischio reale?
  |    Verifica: auth (JWT, API key, Cognito), WAF, SG restrittivi,
  |    network isolation, encryption layer, cookie vs header auth
  |    → SI' = gravita' ridotta proporzionalmente alle mitigazioni
  |
  STEP 4: ENVIRONMENT
  |    Il codice/config e' attivo in produzione?
  |    Verifica: feature flag, env var, log level (debug vs info),
  |    build condition, dead code analysis, VITE_* flags
  |    → NO = gravita' ridotta (pulire comunque, non e' emergenza)
  |
  STEP 5: SELF-VERIFICATION (pattern Anthropic)
       "Tenta di dimostrare che NON e' grave."
       Cerca attivamente prove che il finding sia benigno:
       - Leggi la configurazione VPC/subnet
       - Verifica se l'env var e' sempre settata in prod
       - Controlla se il feature flag e' spento in prod
       Solo se NON trovi prove di benignita' → classifica come grave.
```

### 5.2 Matrice Gravita' Contestuale

La gravita' finale e' funzione del contesto verificato, NON del pattern trovato:

| Raggiungibile? | Mitigato? | Attivo in prod? | Gravita' finale | Azione |
|----------------|-----------|-----------------|-----------------|--------|
| No | - | - | BASSO | Backlog: igiene da correggere |
| Si | Si | No | BASSO | Backlog: pulire codice morto |
| Si | Si | Si | MEDIO | Prossimo sprint: ridurre superficie |
| Si | No | No | MEDIO | Prossimo sprint: aggiungere mitigazione |
| Si | No | Si | ALTO/CRITICO | Immediato: fix o mitigazione urgente |

---

## 6. Come Riconoscere un Falso Positivo

Non tutti i match di pattern sono vulnerabilita'. Prima di segnalare, verifica:

### 6.1 Criteri Generici

| Criterio | Domanda da porsi | Se SI' |
|----------|------------------|--------|
| **Valore di protocollo** | Il valore e' richiesto dall'API esterna come campo fisso? | Non vulnerabilita' |
| **Codice morto / dev-only** | Il codice e' raggiungibile solo in condizioni che non esistono in prod? | Gravita' ridotta |
| **Pattern semanticamente diverso** | La regex matcha "password" ma il contesto e' un label UI, un nome colonna, un placeholder doc? | Non vulnerabilita' |
| **Mitigazione completa** | Il finding e' completamente mitigato da controlli compensativi? | Gravita' ridotta |
| **Fallback non funzionale** | Il fallback punta a localhost/mock che non esiste in ambiente AWS? | Gravita' ridotta |

### 6.2 Esempi da Audit Reali

Questi esempi illustrano come il contesto cambia il verdetto:

**Esempio 1 — Valore di protocollo scambiato per secret**
```
Pattern trovato: securitypassword = "@webservizi@"
Verdetto iniziale: 🚨 Credenziale hardcoded
Contesto: campo fisso richiesto dall'API SIAE Portali per il flusso cambio password
Verdetto finale: ✅ NON VULNERABILITA' — valore di protocollo, non credenziale
```

**Esempio 2 — Security Group 0.0.0.0/0 in subnet privata**
```
Pattern trovato: cidr_blocks = ["0.0.0.0/0"] su SG Aurora
Verdetto iniziale: 🚨 Database esposto a Internet
Contesto: Aurora in subnet data privata, no IGW, publicly_accessible = false
Verdetto finale: ⚠️ BASSO — non raggiungibile dall'esterno, ma igiene da correggere
Nota: il CIDR corretto era commentato, qualcuno ha usato 0.0.0.0/0 come workaround
```

**Esempio 3 — Fallback credenziale funzionale solo in dev**
```
Pattern trovato: if not secret_name: return {"username": "user", "pwd": "***"}
Verdetto iniziale: 🚨 Credenziale di fallback in produzione
Contesto: secret_name viene sempre da env var in AWS Batch. Il fallback punta a localhost:5432
Verdetto finale: ⚠️ BASSO — non funziona in ambiente AWS, serve solo per dev locale
```

---

## Operazioni Attive — Rotazione Credenziali

Quando Claude gestisce direttamente la rotazione di credenziali o l'aggiornamento di secret:

🚨 CRITICO — Pre-flight card OBBLIGATORIA

<EXTREMELY-IMPORTANT>
NON eseguire rotazione credenziali o aggiornamento secret senza mostrare la pre-flight
card e ottenere conferma esplicita dall'utente. Un secret ruotato incorrettamente puo'
causare downtime immediato su tutti i servizi dipendenti.
</EXTREMELY-IMPORTANT>

| 🚨 CRITICO (irreversibile) — 🔨 DevForge · siae-security |
|:---|
| **⚠️ STOP — Rotazione credenziale causa downtime immediato se errata** |
| 🔐 Secret: `<secret-name>` · 🌍 Ambiente: `<dev|collaudo|produzione>` · 📦 Servizi dipendenti: `<lista servizi>` |
| **▼ Azione** |
| 1. ⚠️ Azione: Rotazione credenziale / aggiornamento secret → `aws secretsmanager update-secret --secret-id <id>` |
| 💡 Perche': Secret scaduto/compromesso, rotazione necessaria |
| 🚫 Se NO: STOP — il secret resta invariato, valuta rischio manuale |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Checklist pre-rotazione:**
- [ ] Backup del secret corrente
- [ ] Lista servizi dipendenti verificata
- [ ] Strategia di rollout definita (rolling restart / blue-green)
- [ ] Monitoring attivo per errori post-rotazione

---

## 7. Vincoli Non Negoziabili

Queste regole non ammettono eccezioni, in **nessun** ambiente.

| # | Vincolo | Motivazione |
|---|---------|-------------|
| 1 | **No secrets in git** | Nessun segreto, chiave o credenziale nei repository. Mai. |
| 2 | **No IAM `*` policy** | Nessuna policy con `Action: *` o `Resource: *`. Least privilege sempre. |
| 3 | **No public S3** | Nessun bucket S3 con accesso pubblico. Block Public Access a livello account. |
| 4 | **No PII in logs** | Nessun dato personale nei log. Mascherare email, nomi, codici fiscali, IBAN. |
| 5 | **No HTTP** | Solo HTTPS. Nessuna eccezione, nemmeno per endpoint interni. |
| 6 | **Encryption at rest** | Obbligatoria per tutti i dati persistiti. S3, DynamoDB, RDS, Secrets Manager. |

---

## 8. Anti-Razionalizzazione

Risposte a giustificazioni comuni per bypassare le regole di sicurezza:

| Razionalizzazione | Risposta |
|-------------------|----------|
| "E' solo un ambiente di test" | I test hanno dati reali. Stesse regole. |
| "Lo sistemo dopo il go-live" | Il debito di sicurezza non si ripaga mai. Fallo ora. |
| "E' un progetto interno, nessuno lo vede" | Il 60% delle violazioni viene dall'interno. Stesse regole. |
| "La policy IAM `*` e' temporanea" | Le policy temporanee diventano permanenti. Least privilege da subito. |
| "Il bucket S3 deve essere pubblico per il frontend" | Usa CloudFront + OAI. Mai bucket pubblici diretti. |
| "Il Security Group 0.0.0.0/0 e' sempre critico" | Dipende dalla subnet. In subnet privata senza IGW non e' raggiungibile. Verifica il contesto. |
| "CORS * e' sempre una vulnerabilita'" | Con API key + JWT obbligatori e niente cookie auth, il rischio reale e' basso. Verifica le mitigazioni. |
| "Ho trovato 'password' nel codice, e' un secret" | Potrebbe essere un label UI, un nome colonna, o un valore di protocollo. Verifica il contesto semantico. |

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per errore | 2 | Fermati. Diagnosi diversa necessaria. |
| File modificati per singolo step | 5 | Se devi toccare piu' file, decomponi in sub-task. |
| Output max per raccomandazione | 200 righe | Prioritizza. Top 5 issue, non lista esaustiva. |

---

REQUIRED SUB-SKILL: siae-verification

Invoca `siae-verification` prima di dichiarare il codice sicuro.

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Ho bisogno di debug veloce, metto la password hardcoded" | Ogni secret in git vive per sempre nella history. `git filter-branch` non basta. |
| "IAM `*` e' piu' semplice, lo sistemo dopo" | Il "dopo" non arriva mai. Ogni policy over-privileged e' un blast radius illimitato. |
| "Il bucket S3 e' interno, non serve encryption" | I breach iniziano dall'interno. Encryption at rest e' l'ultima linea di difesa. |
| "Usiamo JWT senza firma perche' e' solo dev" | I JWT senza firma sono testo base64 che chiunque puo' modificare. |
| "Non serve VPC per Lambda, e' serverless" | Lambda senza VPC non puo' accedere a RDS/ElastiCache privati e i requisiti GDPR lo richiedono. |
| "Secrets Manager costa, uso SSM Parameter Store" | SSM Parameter Store Standard tier e' gratuito e supporta encryption KMS. Cost non e' un motivo. |
| "Il log dell'errore include l'input per debug" | Se l'input e' PII (ISRC, CF autore, IBAN), loggarlo viola il GDPR. Logga ID e tipo, non il dato. |
| "Questo dato autore non e' sensibile" | Dati SIAE = identita' autori + dati finanziari. Tratta tutto come PII per default. |
| "Ho verificato manualmente che non ci sono secret" | La review manuale fallisce. Usa il Secret Scan automatico del quality gate. |
| "L'endpoint e' protetto da Cognito, basta cosi'" | Autenticazione != Autorizzazione. Verifica anche i permessi sull'azione, non solo l'identita'. |
| "Il pattern matcha, quindi e' grave" | Il pattern trova candidati. Il contesto determina la gravita'. Applica i 5 step del triage. |
| "Meglio segnalare troppo che troppo poco" | I falsi positivi diluiscono l'attenzione. Un report con 17 finding di cui 8 falsi e' peggio di uno con 9 veri. |
| "Non ho tempo di verificare il contesto" | Verificare il contesto richiede 2-5 minuti. Ritrattare un falso positivo escalato richiede ore. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|------------|---------|------|
| Analisi codice per vulnerabilita' | 🟢 Sicuro | No |
| Suggerimento fix di sicurezza | 🟢 Sicuro | No |
| Modifica codice per fix sicurezza | 🟡 Medio | Si |
| Modifica IAM policy | 🔴 Alto | Si |
| Modifica configurazione encryption | 🔴 Alto | Si |
| Gestione file con segreti (.env, credenziali) | 🚨 Critico | Si |
| Modifica configurazione CI/CD security | 🚨 Critico | Si |
| Rotazione credenziali / Secrets Manager | 🚨 Critico | Si |

---

## Rule Reference — Semgrep SIAE Custom Rules (Wave 1)

Catalogo rule attive in `rules/semgrep/siae/`. Default `severity: WARNING` (ADR-005) — promotion `ERROR` (block) richiede FP rate `<5%` misurato per 30gg via `lib/review_evidence/tools/fp_rate.py` (ADR-005a).

### siae.formula-injection.ts.csv-row-join-naive (F1.a)

- **CWE:** CWE-1236 (Improper Neutralization of Formula Elements in CSV)
- **OWASP:** A03:2021
- **Stack:** TypeScript / JavaScript
- **Severity:** WARNING · confidence HIGH
- **Pentest:** F-01 broadcasting 2026-05-18
- **Fix:**
  ```typescript
  import { stringify } from 'csv-stringify/sync';
  function sanitizeCsvCell(v: unknown): string {
    const s = v == null ? '' : String(v);
    return /^[=+\-@\t\r]/.test(s) ? `'${s}` : s;
  }
  const csv = stringify([headers, ...rows], { quoted: true, cast: { string: sanitizeCsvCell } });
  ```
- **Suppress:** `// nosemgrep: siae.formula-injection.ts.csv-row-join-naive reason=... expires=YYYY-MM-DD`

### siae.formula-injection.ts.csv-rows-join-newline-naive (F1.b)

- **CWE:** CWE-1236 + CWE-93 (RFC 4180 violation)
- **OWASP:** A03:2021
- **Stack:** TypeScript / JavaScript
- **Severity:** WARNING · confidence MEDIUM
- **Pentest:** F-01 + F-05 broadcasting 2026-05-18
- **Fix:** identico a F1.a (csv-stringify con cast sanitize)

### siae.authz-tenant.ts.dao-missing-tenant-filter (F2)

- **CWE:** CWE-639 (Broken Object Level Authorization / IDOR)
- **OWASP:** A01:2021
- **Stack:** TypeScript
- **Severity:** WARNING · confidence HIGH
- **Pentest:** F-03 broadcasting 2026-05-18
- **Fix:**
  ```typescript
  // BEFORE (vulnerable):
  db.query("SELECT * FROM file_logs WHERE id_file = $1", [id])

  // AFTER (safe):
  db.query(
    "SELECT * FROM file_logs WHERE id_file = $1 AND id_emittente = $2",
    [id, context.user.idEmittente]   // tenant dal token, mai da input
  )
  ```
- **Allowlist by-design** (tabelle globali, già in `paths.exclude` della rule):
  - `**/dao/audit_log*.ts` + `**/audit_log_dao*.ts`
  - `**/dao/system_config*.ts` + `**/system_config_dao*.ts`
  - `**/dao/migration_history*.ts` + `**/migration_history_dao*.ts`
  - `**/dao/feature_flag*.ts` + `**/feature_flag_dao*.ts`
  - `**/dao/kg_topology_snapshot*.ts`
- **Suppress per casi edge:** entry in `rules/semgrep/siae/suppressions.yaml` (PR-gate ADR-009 valida schema)

### siae.authz-tenant.ts.query-param-tenant-override (F6)

- **CWE:** CWE-639
- **OWASP:** A01:2021
- **Stack:** TypeScript
- **Severity:** WARNING · confidence HIGH
- **Pentest:** F-06 broadcasting 2026-05-18
- **Fix:**
  ```typescript
  // Reject token con tenant null su ruolo scoped (NEVER user-supplied):
  if (context.user.idEmittente == null) {
    throw new UnauthorizedError("Missing tenant scope on token");
  }
  filters.idEmittente = [context.user.idEmittente];
  ```

### siae.soft-delete.sql.view-only-state-filter (F4)

- **CWE:** CWE-639 (soft-delete logical deletion bypass)
- **OWASP:** A01:2021
- **Stack:** SQL (Postgres)
- **Severity:** WARNING · confidence MEDIUM (cross-file: rule non vede i GRANT)
- **Pentest:** F-04 broadcasting 2026-05-18
- **Fix:**
  ```sql
  ALTER TABLE dettaglio_canale_mensile ENABLE ROW LEVEL SECURITY;
  CREATE POLICY hide_cancelled ON dettaglio_canale_mensile
    USING (EXISTS (
      SELECT 1 FROM report_logico rl
      WHERE rl.id_canale = dettaglio_canale_mensile.id_canale
        AND rl.id_stato_report <> 6
    ));
  -- Verify GRANT con `\dp` (psql).
  ```

### siae.jwt.ts.jwt-in-localstorage (F26)

- **CWE:** CWE-1004 (Sensitive Cookie Without HttpOnly) + CWE-79 (XSS amplification)
- **OWASP:** A02:2021
- **Stack:** TypeScript / JavaScript (frontend)
- **Severity:** WARNING · confidence HIGH
- **Fix:** HttpOnly + Secure + SameSite=Strict cookie server-side (vedi sezione "JWT" sopra in questa SKILL).

---

## Suppression Workflow (Wave 1)

3 modalità di soppressione per finding legittimi:

1. **Inline `// nosemgrep`** (Wave 1 MVP):
   ```typescript
   // nosemgrep: siae.formula-injection.ts.csv-row-join-naive reason=false-positive-confirmed expires=2026-09-01
   ```
2. **Annotation domain-specific** (Wave 1 MVP, inline contextual):
   ```typescript
   // siae-tenant-safe: tabella audit globale by-design SDLC-1234
   db.query('SELECT * FROM audit_log WHERE id_file = $1', [id]);
   ```
3. **Strutturata** (`rules/semgrep/siae/suppressions.yaml`, validata da PR-gate ADR-009):
   ```yaml
   suppressions:
     - rule_id: siae.authz-tenant.ts.dao-missing-tenant-filter
       path_glob: "**/dao/audit_log*.ts"
       reason: "Globale by-design ARCH-2026-05-12"
       owner: tuo.email@siae.it
       expires_at: "2026-08-15"  # <=90gg
   ```

PR-gate hook valida schema strutturata: no catch-all glob, reason ≥30 char + Jira ref, expires ≤90gg, owner `@siae.it`. Violazione → BLOCK_REGRESSION.

## FP Rate Measurement (ADR-005a)

Tool `lib/review_evidence/tools/fp_rate.py` misura false positive rate per rule SIAE:

```bash
semgrep --config rules/semgrep/siae/ --json . | \
  python -m lib.review_evidence.tools.fp_rate \
    --rule siae.formula-injection.ts.csv-row-join-naive \
    --corpus . \
    --output reports/fp_rate.json
```

Thresholds: <5% PROMOTE | 5-10% RETRY +30gg | ≥10% REWORK.

## Drools `.drl` Review (ADR-007)

Semgrep CE non parsa Drools. PR che modifica `*.drl` deve avere UNA delle 2 forme:

- **Form A** (PR-level): label `drools-security-reviewed` (security team)
- **Form B** (file header): `// drools-security-reviewed: <Jira> by:<email@siae.it> on:<YYYY-MM-DD>`

Missing → WARNING (NON block, ADR-007 goal "no bloccare tutto").
