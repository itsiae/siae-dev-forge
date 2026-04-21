# Task 15 — hooks/run-hook.cmd fail-loud + DEVFORGE_SILENT_ON_NO_BASH escape hatch

**PR:** PR-2 | **SP:** 0.1 SP-Augmented | **Dipendenze:** nessuna (indipendente da T13/T14) | **Stato:** [PENDING]

## File coinvolti

- `hooks/run-hook.cmd` (modifica)
- `tests/windows-runtime/run-hook-cmd.test.bat` (nuovo — test cmd-native)
- `tests/windows-runtime/run-hook-cmd.test.sh` (nuovo — test polyglot per Unix path)

## Step 1 — Test RED

File: `tests/windows-runtime/run-hook-cmd.test.bat`

```batch
@echo off
REM Test che run-hook.cmd fa fail-loud se bash assente, e rispetta
REM DEVFORGE_SILENT_ON_NO_BASH come escape hatch.

setlocal enabledelayedexpansion
set "FAILED=0"
set "HOOK_FILE=%~dp0..\..\hooks\run-hook.cmd"

REM Test 1: short-circuit via DEVFORGE_TEST_HIDE_BASH → exit /b 1 + emit repair
REM (necessario perché runner CI Windows ha Git preinstallato — non possiamo
REM "rimuovere" bash modificando PATH, i path fissi nel .cmd matcherebbero)
set "APPDATA_TEST=%TEMP%\devforge-test-appdata-%RANDOM%"
set "APPDATA=%APPDATA_TEST%"
set "DEVFORGE_TEST_HIDE_BASH=1"

call "%HOOK_FILE%" session-start
if !ERRORLEVEL! NEQ 1 (
    echo FAIL Test 1: expected exit 1, got !ERRORLEVEL!
    set /a FAILED+=1
) else (
    echo PASS Test 1: fail-loud exit 1 quando bash assente
)

REM Verifica che flag devforge-needs-repair sia stato creato
if not exist "%APPDATA_TEST%\Claude\devforge-needs-repair" (
    echo FAIL Test 2: flag devforge-needs-repair non creato
    set /a FAILED+=1
) else (
    echo PASS Test 2: flag devforge-needs-repair creato
)

REM Test 3: DEVFORGE_SILENT_ON_NO_BASH=1 → exit /b 0 senza fail-loud
set "DEVFORGE_SILENT_ON_NO_BASH=1"
rmdir /s /q "%APPDATA_TEST%" 2>nul
mkdir "%APPDATA_TEST%\Claude" 2>nul

call "%HOOK_FILE%" session-start
if !ERRORLEVEL! NEQ 0 (
    echo FAIL Test 3: expected exit 0 with panic button, got !ERRORLEVEL!
    set /a FAILED+=1
) else (
    echo PASS Test 3: panic button silent exit 0
)

REM Verifica che flag NON sia creato con panic button
if exist "%APPDATA_TEST%\Claude\devforge-needs-repair" (
    echo FAIL Test 4: flag creato anche con panic button
    set /a FAILED+=1
) else (
    echo PASS Test 4: panic button preserva silent behavior
)

set "PATH=%SAVED_PATH%"
set "DEVFORGE_SILENT_ON_NO_BASH="
rmdir /s /q "%APPDATA_TEST%" 2>nul

if !FAILED! GTR 0 (
    echo.
    echo !FAILED! test FAILED
    exit /b 1
)
echo.
echo All tests PASSED
exit /b 0
```

File: `tests/windows-runtime/run-hook-cmd.test.sh` (bats)

```bash
#!/usr/bin/env bats
# Test polyglot: run-hook.cmd path Unix (bash source)

HOOK_FILE="${BATS_TEST_DIRNAME}/../../hooks/run-hook.cmd"

@test "run-hook.cmd (Unix path): exec bash su script esistente" {
    # Crea script dummy
    local dummy_dir=$(mktemp -d)
    echo '#!/usr/bin/env bash' > "$dummy_dir/test-hook"
    echo 'echo "dummy ran"' >> "$dummy_dir/test-hook"
    chmod +x "$dummy_dir/test-hook"

    # Copia run-hook.cmd nella dir dummy
    cp "$HOOK_FILE" "$dummy_dir/"

    run bash "$dummy_dir/run-hook.cmd" test-hook
    [ "$status" -eq 0 ]
    [[ "$output" =~ "dummy ran" ]]

    rm -rf "$dummy_dir"
}
```

## Step 2 — Run (RED)

```cmd
rem Windows
call tests\windows-runtime\run-hook-cmd.test.bat
rem Atteso: 4 test FAIL (run-hook.cmd attuale non ha fail-loud logic)
```

```bash
# Mac/Linux
bats tests/windows-runtime/run-hook-cmd.test.sh
# Il test Unix-path dovrebbe già passare col comportamento attuale
```

## Step 3 — Impl

Modifica `hooks/run-hook.cmd` — sostituisci il blocco finale:

```cmd
: << 'CMDBLOCK'
@echo off
REM Cross-platform polyglot wrapper for hook scripts.
REM On Windows: cmd.exe runs the batch portion, which finds and calls bash.
REM On Unix: the shell interprets this as a script (: is a no-op in bash).
REM Hook scripts use extensionless filenames (e.g. "session-start" not
REM "session-start.sh") so Claude Code's Windows auto-detection — which
REM prepends "bash" to any command containing .sh — doesn't interfere.
REM Usage: run-hook.cmd <script-name> [args...]

if "%~1"=="" (
    echo run-hook.cmd: missing script name >&2
    exit /b 1
)

set "HOOK_DIR=%~dp0"

REM BLOCK-2 fix (plan-reviewer): test short-circuit.
REM Permette alla CI matrix di testare il fail-loud path anche su runner
REM Windows con Git preinstallato (windows-latest/windows-2019). Non usare
REM mai in produzione — solo CI tests.
if "%DEVFORGE_TEST_HIDE_BASH%"=="1" goto :no_bash_found

REM Try Git for Windows bash in standard locations
if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)
if exist "C:\Program Files (x86)\Git\bin\bash.exe" (
    "C:\Program Files (x86)\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

REM User-scope Git install (no admin required)
if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" (
    "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

REM DevForge PortableGit embedded (installed by install.ps1)
if exist "%LOCALAPPDATA%\DevForge\PortableGit\bin\bash.exe" (
    "%LOCALAPPDATA%\DevForge\PortableGit\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

REM Try bash on PATH (user Git Bash, MSYS2, Cygwin)
where bash >nul 2>nul
if %ERRORLEVEL% equ 0 (
    bash "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

REM No bash found (o short-circuit test).
:no_bash_found
REM Panic button: DEVFORGE_SILENT_ON_NO_BASH=1 → vecchio comportamento silent
if "%DEVFORGE_SILENT_ON_NO_BASH%"=="1" exit /b 0

REM Fail LOUD — stderr + flag + emit repair event + exit 1
echo. >&2
echo [DevForge] bash not found - DevForge hooks disabled. >&2
echo [DevForge] Ripara con: >&2
echo   Set-ExecutionPolicy -Scope Process Bypass -Force >&2
echo   iwr https://github.com/itsiae/siae-dev-forge/releases/latest/download/install.ps1 ^| iex >&2
echo [DevForge] Per silenziare temporaneamente: set DEVFORGE_SILENT_ON_NO_BASH=1 >&2
echo. >&2
if not exist "%APPDATA%\Claude" mkdir "%APPDATA%\Claude" 2>nul
type NUL > "%APPDATA%\Claude\devforge-needs-repair" 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%HOOK_DIR%emit-repair-event.ps1" >nul 2>&1
exit /b 1
CMDBLOCK

# Unix: run the named script directly (invariato)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="$1"
shift
exec bash "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@"
```

**Nota:** il blocco CMD include ora 5 path di detection (invece di 3 originali): aggiungo `%LOCALAPPDATA%\Programs\Git` (user-scope) e `%LOCALAPPDATA%\DevForge\PortableGit` (installer PR-1). Questi NON cambiano il comportamento Unix (il file CMD non viene letto da bash).

## Step 4 — Run (GREEN)

```cmd
call tests\windows-runtime\run-hook-cmd.test.bat
rem Atteso: 4/4 PASS
```

```bash
bats tests/windows-runtime/run-hook-cmd.test.sh
# Atteso: 1/1 pass (Unix path inchangé)
```

## Step 5 — Commit

```bash
git add hooks/run-hook.cmd tests/windows-runtime/run-hook-cmd.test.bat tests/windows-runtime/run-hook-cmd.test.sh
git commit -m "feat(windows-runtime): run-hook.cmd fail-loud + DEVFORGE_SILENT_ON_NO_BASH escape hatch [AC-5, AC-17]"
```
