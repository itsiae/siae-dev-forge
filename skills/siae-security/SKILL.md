---
name: siae-security
description: >
  Sicurezza SIAE: OWASP Top 10, AWS security, PII dominio copyright.
  Trigger: codice security-sensitive, gestione credenziali, IAM policy,
  encryption, dati personali autori/artisti, codici ISWC/ISRC.
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

> **Tipo:** Passivo + On-demand | **Fase SDLC:** Trasversale (tutte le fasi)
>
> Questa skill si attiva su codice security-sensitive: gestione credenziali,
> IAM policy, encryption, dati personali autori/artisti, codici ISWC/ISRC.
> Applica OWASP Top 10, best practice AWS e regole PII specifiche SIAE.

---

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

Genera la pre-flight card con `design-system/generate-card.py`:

```bash
echo '{
  "level": "CRITICO",
  "skill": "siae-security",
  "context": [
    {"emoji": "🔑", "label": "Pattern", "value": "Secret rilevato nel file"},
    {"emoji": "📁", "label": "File", "value": "[percorso del file]"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Rilevato pattern segreto", "path": "[percorso del file]"}
  ],
  "reason": "Il file contiene potenziali credenziali",
  "ifno": "Le credenziali potrebbero finire nel repository"
}' | python3 design-system/generate-card.py
```

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

## 5. Vincoli Non Negoziabili

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

## 6. Anti-Razionalizzazione

Risposte a giustificazioni comuni per bypassare le regole di sicurezza:

| Razionalizzazione | Risposta |
|-------------------|----------|
| "E' solo un ambiente di test" | I test hanno dati reali. Stesse regole. |
| "Lo sistemo dopo il go-live" | Il debito di sicurezza non si ripaga mai. Fallo ora. |
| "E' un progetto interno, nessuno lo vede" | Il 60% delle violazioni viene dall'interno. Stesse regole. |
| "La policy IAM `*` e' temporanea" | Le policy temporanee diventano permanenti. Least privilege da subito. |
| "Il bucket S3 deve essere pubblico per il frontend" | Usa CloudFront + OAI. Mai bucket pubblici diretti. |

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
