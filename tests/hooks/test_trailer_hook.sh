#!/usr/bin/env bash
# Test: prepare-commit-msg trailer hook DevForge-Author (Task 08 / Comp.4)
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INSTALLER="${PLUGIN_ROOT}/lib/install-trailer-hook.sh"
FAIL=0
MARKER="# DEVFORGE-TRAILER-HOOK v1"

newrepo() { local d; d=$(mktemp -d); ( cd "$d" && git init -q && git config user.email t@t.local && git config user.name T ); echo "$d"; }

# Fixture ~/.claude.json con oauthAccount
CJ=$(mktemp)
printf '{"oauthAccount":{"emailAddress":"carmen.lasala@siae.it","accountUuid":"u","organizationUuid":"o","organizationName":"IT"}}' > "$CJ"

# T1: installa hook con marker + eseguibile
R1=$(newrepo); ( cd "$R1" && bash "$INSTALLER" >/dev/null 2>&1 )
H="$R1/.git/hooks/prepare-commit-msg"
[ -f "$H" ] && grep -qF "$MARKER" "$H" && [ -x "$H" ] || { echo "FAIL T1: hook non installato/marker/exec"; FAIL=1; }

# T2: idempotente (2a esecuzione, marker singolo)
( cd "$R1" && bash "$INSTALLER" >/dev/null 2>&1 )
[ "$(grep -cF "$MARKER" "$H")" = "1" ] || { echo "FAIL T2: marker non singolo dopo re-install"; FAIL=1; }

# T3: skip hook estraneo (rc=2, file intatto)
R3=$(newrepo); FOREIGN="$R3/.git/hooks/prepare-commit-msg"
printf '#!/bin/sh\necho husky\n' > "$FOREIGN"; chmod +x "$FOREIGN"
( cd "$R3" && bash "$INSTALLER" >/dev/null 2>&1 ); RC3=$?
grep -qF "husky" "$FOREIGN" && ! grep -qF "$MARKER" "$FOREIGN" || { echo "FAIL T3: hook estraneo modificato"; FAIL=1; }
[ "$RC3" = "2" ] || { echo "FAIL T3: rc atteso 2 su foreign, ottenuto $RC3"; FAIL=1; }

# T4: opt-out
R4=$(newrepo); ( cd "$R4" && DEVFORGE_SKIP_TRAILER_HOOK=1 bash "$INSTALLER" >/dev/null 2>&1 )
[ ! -f "$R4/.git/hooks/prepare-commit-msg" ] || { echo "FAIL T4: hook installato nonostante opt-out"; FAIL=1; }

# T5: e2e — commit -m timbra il trailer
R5=$(newrepo); ( cd "$R5" && bash "$INSTALLER" >/dev/null 2>&1 )
( cd "$R5" && echo a > f && git add f && DEVFORGE_CLAUDE_JSON="$CJ" git commit -q -m "feat: x" )
MSG5=$( cd "$R5" && git log -1 --format=%B )
echo "$MSG5" | grep -qF "DevForge-Author: carmen.lasala@siae.it" || { echo "FAIL T5: trailer assente. msg=[$MSG5]"; FAIL=1; }
# corpo preservato
echo "$MSG5" | grep -qF "feat: x" || { echo "FAIL T5: corpo messaggio perso"; FAIL=1; }

# T6: amend non duplica
( cd "$R5" && echo b >> f && git add f && DEVFORGE_CLAUDE_JSON="$CJ" git commit -q --amend --no-edit )
MSG6=$( cd "$R5" && git log -1 --format=%B )
[ "$(echo "$MSG6" | grep -cF "DevForge-Author:")" = "1" ] || { echo "FAIL T6: trailer duplicato su amend"; FAIL=1; }

# T7: best-effort — niente claude.json → commit OK senza trailer, messaggio intatto
R7=$(newrepo); ( cd "$R7" && bash "$INSTALLER" >/dev/null 2>&1 )
( cd "$R7" && echo a > f && git add f && DEVFORGE_CLAUDE_JSON="/nonexistent/x.json" git commit -q -m "no-trailer-msg" )
MSG7=$( cd "$R7" && git log -1 --format=%B )
echo "$MSG7" | grep -qF "no-trailer-msg" || { echo "FAIL T7: commit fallito/messaggio perso senza claude.json"; FAIL=1; }
echo "$MSG7" | grep -qF "DevForge-Author:" && { echo "FAIL T7: trailer presente senza email"; FAIL=1; } || true

# T8: hook usa --in-place (safety) + skip merge
grep -qF -- "--in-place" "$H" || { echo "FAIL T8: hook non usa --in-place"; FAIL=1; }
TMPMSG=$(mktemp); printf 'merge msg\n' > "$TMPMSG"
DEVFORGE_CLAUDE_JSON="$CJ" bash "$H" "$TMPMSG" merge >/dev/null 2>&1
grep -qF "DevForge-Author:" "$TMPMSG" && { echo "FAIL T8: trailer aggiunto su merge"; FAIL=1; } || true

[ "$FAIL" = "0" ] && echo "PASS test_trailer_hook" || exit 1
