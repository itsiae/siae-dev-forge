#!/bin/bash
# find-polluter.sh — Identifica quale test inquina gli altri (test pollution)
#
# UTILIZZO:
#   ./skills/siae-debugging/find-polluter.sh '<pattern_inquinamento>' '<glob_test_files>'
#
# ESEMPI:
#   ./find-polluter.sh '.git' 'src/**/*.test.ts'
#   ./find-polluter.sh 'tmp_session_' 'tests/unit/**/*.spec.ts'
#   ./find-polluter.sh 'DB_DIRTY' 'tests/**/*.test.py'
#
# COME FUNZIONA:
#   Esegue i file di test uno alla volta e verifica se il pattern di
#   inquinamento appare dopo ogni esecuzione. Ferma al primo test che
#   causa la contaminazione.

set -e

POLLUTION_PATTERN="${1:?Errore: specifica il pattern di inquinamento come primo argomento}"
TEST_GLOB="${2:?Errore: specifica il glob dei file di test come secondo argomento}"

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "🔍 find-polluter — Ricerca test che causa: '$POLLUTION_PATTERN'"
echo "   File test: $TEST_GLOB"
echo ""

# Verifica che il pattern NON esista già prima di iniziare
check_pollution() {
    if ls $POLLUTION_PATTERN 2>/dev/null | head -1 | grep -q .; then
        return 0  # trovato
    fi
    return 1  # non trovato
}

if check_pollution; then
    echo -e "${RED}⚠️  Il pattern '$POLLUTION_PATTERN' esiste già PRIMA di qualsiasi test.${NC}"
    echo "   Non è un problema di test pollution — controlla il setup dell'ambiente."
    exit 1
fi

# Funzione per rilevare il runner di test
detect_runner() {
    local file="$1"
    if [[ "$file" == *.py ]]; then
        echo "pytest"
    elif [[ "$file" == *.spec.ts ]] || [[ "$file" == *.test.ts ]]; then
        if [[ -f "vitest.config.ts" ]] || [[ -f "vitest.config.js" ]]; then
            echo "vitest"
        else
            echo "jest"
        fi
    elif [[ "$file" == *.spec.js ]] || [[ "$file" == *.test.js ]]; then
        echo "jest"
    elif [[ "$file" == *Test.java ]] || [[ "$file" == *Tests.java ]]; then
        echo "mvn"
    else
        echo "unknown"
    fi
}

# Esegui test uno alla volta
COUNT=0
POLLUTER=""

for test_file in $TEST_GLOB; do
    if [[ ! -f "$test_file" ]]; then
        continue
    fi

    COUNT=$((COUNT + 1))
    runner=$(detect_runner "$test_file")

    printf "  [%3d] %-60s" "$COUNT" "$test_file"

    # Esegui il singolo file di test (silenziato)
    EXIT_CODE=0
    case "$runner" in
        pytest)
            python -m pytest "$test_file" -q --tb=no 2>&1 > /dev/null || EXIT_CODE=$?
            ;;
        vitest)
            npx vitest run "$test_file" --reporter=verbose 2>&1 > /dev/null || EXIT_CODE=$?
            ;;
        jest)
            npx jest "$test_file" --testPathPattern="$test_file" 2>&1 > /dev/null || EXIT_CODE=$?
            ;;
        mvn)
            # Estrai il nome della classe di test dal path
            TEST_CLASS=$(basename "$test_file" .java)
            mvn test -Dtest="$TEST_CLASS" -q 2>&1 > /dev/null || EXIT_CODE=$?
            ;;
        *)
            echo -e " ${YELLOW}[SKIP — runner non rilevato]${NC}"
            continue
            ;;
    esac

    # Controlla se il pattern di inquinamento è apparso
    if check_pollution; then
        POLLUTER="$test_file"
        echo -e " ${RED}💥 POLLUTER TROVATO${NC}"
        break
    else
        echo -e " ${GREEN}✓${NC}"
    fi
done

echo ""

if [[ -n "$POLLUTER" ]]; then
    echo -e "${RED}💥 POLLUTER IDENTIFICATO${NC}"
    echo ""
    echo "  File:    $POLLUTER"
    echo "  Pattern: $POLLUTION_PATTERN"
    echo ""
    echo "  Prossimi passi:"
    echo "  1. Apri $POLLUTER"
    echo "  2. Cerca operazioni che creano '$POLLUTION_PATTERN' (es. mkdir, git init, write file)"
    echo "  3. Aggiungi cleanup in afterEach/teardown"
    echo "  4. Vedi: skills/siae-debugging/defense-in-depth.md (Layer 3 — Environment Guards)"
    echo ""
else
    echo -e "${YELLOW}Nessun polluter trovato tra i $COUNT test analizzati.${NC}"
    echo ""
    echo "  Possibili cause:"
    echo "  - Il pattern viene creato da un hook globale (beforeAll, setup.ts)"
    echo "  - Il pattern viene creato al di fuori dei test (script di setup)"
    echo "  - Il glob non copre tutti i file di test rilevanti"
fi
