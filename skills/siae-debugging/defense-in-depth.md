# Defense-in-Depth Validation

Tecnica complementare alla Root Cause Investigation (Fase 1 di `siae-debugging`).

Quando hai identificato una root cause e scritto il fix, valuta se la difesa
a un solo livello è sufficiente o se servono protezioni multiple.

---

## Il Pattern a 4 Layer

Ogni layer cattura bug che gli altri non vedono. In sistemi critici,
applicarli tutti e 4 previene regression e facilita il debugging futuro.

### Layer 1 — Entry Point (API Boundary)

Rifiuta input non validi al confine del sistema, prima che causino danni interni.

```java
// Java
public ProjectDto createProject(String name, String workingDirectory) {
    if (workingDirectory == null || workingDirectory.isBlank()) {
        throw new IllegalArgumentException("workingDirectory non può essere vuoto");
    }
    // ...
}
```

```typescript
// TypeScript
function createProject(name: string, workingDirectory: string): Project {
    if (!workingDirectory || workingDirectory.trim() === '') {
        throw new Error('workingDirectory non può essere vuoto');
    }
    // ...
}
```

```python
# Python
def create_project(name: str, working_directory: str) -> Project:
    if not working_directory or not working_directory.strip():
        raise ValueError("working_directory non può essere vuoto")
    # ...
```

---

### Layer 2 — Business Logic

Assicura che i dati abbiano senso nel contesto del dominio, non solo che siano
tecnicamente presenti.

```typescript
function initializeWorkspace(projectDir: string, sessionId: string): void {
    if (!projectDir) {
        throw new Error(`projectDir obbligatorio per la sessione ${sessionId}`);
    }
    if (!path.isAbsolute(projectDir)) {
        throw new Error(`projectDir deve essere un path assoluto: ${projectDir}`);
    }
    // ...
}
```

---

### Layer 3 — Environment Guards

Previeni operazioni distruttive in contesti non intenzionali (es. test che
modificano il filesystem reale, deploy in ambienti sbagliati).

```typescript
// Esempio: prevenire git init fuori da una directory temp durante i test
async function gitInit(directory: string): Promise<void> {
    if (process.env.NODE_ENV === 'test') {
        const tmpDir = os.tmpdir();
        const normalized = path.resolve(directory);
        if (!normalized.startsWith(tmpDir)) {
            throw new Error(
                `Rifiuto git init fuori da tmp durante i test: ${directory}`
            );
        }
    }
    // ...
}
```

```python
# Esempio: prevenire scrittura su S3 production durante i test
def upload_to_s3(bucket: str, key: str, data: bytes) -> None:
    if os.getenv("ENVIRONMENT") == "test" and "prod" in bucket:
        raise RuntimeError(
            f"Rifiuto upload su bucket production durante i test: {bucket}"
        )
    # ...
```

---

### Layer 4 — Debug Instrumentation

Cattura il contesto necessario per diagnosticare problemi futuri, specialmente
in ambienti difficili da riprodurre (produzione, CI).

```typescript
async function gitInit(directory: string): Promise<void> {
    const stack = new Error().stack;
    logger.debug('git init', {
        directory,
        cwd: process.cwd(),
        nodeEnv: process.env.NODE_ENV,
        callerStack: stack,
    });
    // ...
}
```

```python
def upload_to_s3(bucket: str, key: str, data: bytes) -> None:
    logger.debug("upload_to_s3", extra={
        "bucket": bucket,
        "key": key,
        "data_size": len(data),
        "environment": os.getenv("ENVIRONMENT"),
    })
    # ...
```

---

## Quando Applicare

| Situazione | Layer minimi consigliati |
|-----------|--------------------------|
| Bug ripetuto (3+ occorrenze) | Tutti e 4 |
| Sistema critico (pagamenti, dati autori) | Tutti e 4 |
| Ambiente di test instabile | Layer 3 + 4 |
| API pubblica / consumer esterno | Layer 1 + 2 |
| Fix urgente con poco tempo | Layer 1 obbligatorio, Layer 4 fortemente consigliato |

---

## Regola Pratica

**Non tutti i layer sono necessari per ogni bug.** Ma quando un bug riappare
dopo un fix, probabilmente stavi difendendo un solo layer.

Quando noti:
- Il bug si è spostato in un altro componente → manca Layer 2
- I test locali passano ma CI fallisce → manca Layer 3
- "Non capisco come sia potuto succedere" → manca Layer 4

Aggiungi il layer mancante insieme al fix.
