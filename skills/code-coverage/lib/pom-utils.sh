#!/usr/bin/env bash
# pom-utils.sh — Helper bash per leggere proprietà / configurazioni dai pom Maven.
#
# Strategia: usa xmllint quando disponibile (XPath robusto su entità XML),
# fallback a grep/sed quando assente. Tutte le funzioni stampano su stdout e
# ritornano 0 anche se il valore non è trovato (output vuoto). Usate da
# phase1-discover.sh, phase2-strategy inline, e validate_env.py via shell-out.
#
# Pubbliche:
#   pom_xmllint_available     → 0 se xmllint disponibile, 1 altrimenti
#   pom_extract_property POM NAME        → valore <NAME> o vuoto
#   pom_has_packaging_pom POM            → 0 se <packaging>pom</packaging>, 1 altrimenti
#   pom_extract_modules POM              → lista <module> uno per riga
#   pom_has_jacoco_plugin POM            → 0 se jacoco-maven-plugin presente
#   pom_has_junit5 POM                   → 0 se junit-jupiter[-api] presente
#   pom_extract_surefire_includes POM    → lista include pattern uno per riga
#   pom_extract_surefire_excludes POM    → lista exclude pattern uno per riga
#   pom_jacoco_skip POM                  → "true"/"false" (default "false")
#   pom_extract_lombok_version POM       → versione Lombok o vuoto
#   pom_extract_source_level POM         → "1.7"/"1.8"/"11"/... o vuoto

pom_xmllint_available() {
    command -v xmllint >/dev/null 2>&1
}

# Estrae il primo valore di un tag XML semplice, ignorando namespace.
# Usage: pom_extract_property /path/to/pom.xml appVersion
pom_extract_property() {
    local pom="$1"
    local name="$2"
    [ -f "$pom" ] || return 0
    if pom_xmllint_available; then
        # Nota: --xpath richiede prefissi per namespace. Usiamo local-name() per
        # essere agnostici a `<project xmlns=...>` (pattern Maven canonico).
        xmllint --xpath "string(//*[local-name()='${name}'][1])" "$pom" 2>/dev/null
    else
        # Fallback regex multilinea (sed). Match prima occorrenza,
        # strip whitespace.
        sed -n "s|.*<${name}[^>]*>\([^<]*\)</${name}>.*|\1|p" "$pom" 2>/dev/null | head -1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
    fi
}

pom_has_packaging_pom() {
    local pom="$1"
    local pkg
    pkg=$(pom_extract_property "$pom" "packaging")
    [ "$pkg" = "pom" ]
}

pom_extract_modules() {
    local pom="$1"
    [ -f "$pom" ] || return 0
    if pom_xmllint_available; then
        # Itera su tutti i <module> figli di <modules>
        xmllint --xpath "//*[local-name()='modules']/*[local-name()='module']/text()" "$pom" 2>/dev/null \
            | tr '\n' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
            | grep -v '^$' || true
    else
        # Fallback: extract content fra <modules>...</modules> e parse <module>
        awk '/<modules>/,/<\/modules>/' "$pom" 2>/dev/null \
            | sed -n 's|.*<module>\([^<]*\)</module>.*|\1|p' \
            | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
            | grep -v '^$' || true
    fi
}

pom_has_jacoco_plugin() {
    grep -q '<artifactId>jacoco-maven-plugin</artifactId>' "$1" 2>/dev/null
}

pom_has_junit5() {
    grep -qE '<artifactId>junit-jupiter(-api)?</artifactId>' "$1" 2>/dev/null
}

pom_extract_surefire_includes() {
    local pom="$1"
    [ -f "$pom" ] || return 0
    if pom_xmllint_available; then
        xmllint --xpath "//*[local-name()='plugin'][./*[local-name()='artifactId']='maven-surefire-plugin']//*[local-name()='include']/text()" \
            "$pom" 2>/dev/null | grep -v '^$' || true
    else
        # Fallback: parse plugin block testualmente
        awk '/<artifactId>maven-surefire-plugin<\/artifactId>/,/<\/plugin>/' "$pom" 2>/dev/null \
            | sed -n 's|.*<include>\([^<]*\)</include>.*|\1|p' || true
    fi
}

pom_extract_surefire_excludes() {
    local pom="$1"
    [ -f "$pom" ] || return 0
    if pom_xmllint_available; then
        xmllint --xpath "//*[local-name()='plugin'][./*[local-name()='artifactId']='maven-surefire-plugin']//*[local-name()='exclude']/text()" \
            "$pom" 2>/dev/null | grep -v '^$' || true
    else
        awk '/<artifactId>maven-surefire-plugin<\/artifactId>/,/<\/plugin>/' "$pom" 2>/dev/null \
            | sed -n 's|.*<exclude>\([^<]*\)</exclude>.*|\1|p' || true
    fi
}

pom_jacoco_skip() {
    local pom="$1"
    local val
    val=$(pom_extract_property "$pom" "jacoco.skip")
    case "$val" in
        true|TRUE|True) echo "true" ;;
        *) echo "false" ;;
    esac
}

pom_extract_lombok_version() {
    local pom="$1"
    [ -f "$pom" ] || return 0
    # Try <lombok.version> property first
    local v
    v=$(pom_extract_property "$pom" "lombok.version")
    if [ -n "$v" ]; then
        echo "$v"
        return 0
    fi
    # Fallback: cerca dependency block lombok e estrai <version>
    awk '/<artifactId>lombok<\/artifactId>/{flag=1; next} flag && /<version>/{
        match($0, /<version>([^<]*)<\/version>/, a); if (a[1] != "") print a[1]; flag=0
    } flag && /<\/dependency>/{flag=0}' "$pom" 2>/dev/null | head -1
}

# Source level Java (1.7/1.8/11/17/...): scan in ordine maven.compiler.source,
# maven.compiler.release, java.version, source level del compiler plugin.
pom_extract_source_level() {
    local pom="$1"
    [ -f "$pom" ] || return 0
    local v
    for prop in "maven.compiler.source" "maven.compiler.release" "java.version" "source"; do
        v=$(pom_extract_property "$pom" "$prop")
        if [ -n "$v" ]; then
            echo "$v"
            return 0
        fi
    done
    # Fallback: <source>1.8</source> dentro maven-compiler-plugin
    awk '/<artifactId>maven-compiler-plugin<\/artifactId>/,/<\/plugin>/' "$pom" 2>/dev/null \
        | sed -n 's|.*<source>\([^<]*\)</source>.*|\1|p' | head -1
}
