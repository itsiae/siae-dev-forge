# Task 04 — Implementa emit in session-start startup (GREEN)

**Tipo:** impl (TDD GREEN) · **AC:** AC4, AC5, AC8 · **File:** `lib/logger.sh`, `hooks/session-start`

## Obiettivo

Far passare Task 03: funzione `devforge_emit_identity_observability` + chiamata nel branch `startup)`.

## Implementazione

### 1. Funzione in `lib/logger.sh`

Aggiungi dopo `_devforge_ensure_auth` (Task 02):

```sh
# Emette 1 evento osservabilità sull'identità SSO corrente (best-effort).
# Chiamata UNA volta dal branch startup) di session-start (1×/sessione logica).
# DEVFORGE_AUTH_EMAIL deve essere già risolto dal chiamante.
devforge_emit_identity_observability() {
    local domain_expected="${DEVFORGE_AUTH_DOMAIN:-siae.it}"
    if [ -z "${DEVFORGE_AUTH_EMAIL:-}" ]; then
        devforge_log "identity_unresolved" "warning" '{"reason":"oauthAccount_absent"}' 2>/dev/null || true
    else
        local _dom="${DEVFORGE_AUTH_EMAIL##*@}"
        if [ "$_dom" != "$domain_expected" ]; then
            devforge_log "identity_external_domain" "warning" \
                "{\"domain\":\"$(devforge_sanitize_json_str "$_dom")\"}" 2>/dev/null || true
        fi
    fi
}
```

### 2. Chiamata nel branch `startup)` di `hooks/session-start`

Il `case "$SESSION_START_SOURCE"` è a riga ~417, branch `startup)` a riga ~418.
Le var auth sono già valorizzate (righe 91-95). **La nuova chiamata va inserita PRIMA del
`;;` esistente** che chiude il branch — il `;;` resta l'ultima riga del branch.

Struttura **attuale** del branch (verifica con `sed -n '415,425p' hooks/session-start`):

```sh
    startup)
        # Fresh session — reset skills invoked
        echo "" > "${HOME}/.claude/.devforge-session-skills"
        ;;
```

Struttura **risultante** (la chiamata è inserita tra `echo …` e `;;`):

```sh
    startup)
        # Fresh session — reset skills invoked
        echo "" > "${HOME}/.claude/.devforge-session-skills"
        devforge_emit_identity_observability   # <-- NUOVA (1×/sessione logica)
        ;;
```

> ⚠️ NON inserire la chiamata dopo `;;`: finirebbe fuori dal `case` (o nel branch
> successivo) e non verrebbe eseguita nel ramo startup. Il `;;` deve rimanere l'ultima
> riga del branch `startup)`.

## Verifica GREEN

```bash
bash tests/hooks/test_identity_observability.sh ; echo "exit=$?"
```

**Atteso:** `PASS test_identity_observability`, exit 0.

## No-regression

```bash
bash tests/hooks/test_lazy_auth_resolution.sh ; echo "exit=$?"   # Task 01-02 ancora verdi
bash -n hooks/session-start ; echo "syntax=$?"                   # session-start sintatticamente valido
```

## Done quando

- Funzione aggiunta + chiamata nel branch `startup)`.
- Task 03 verde; `bash -n hooks/session-start` exit 0; Task 01 ancora verde.
