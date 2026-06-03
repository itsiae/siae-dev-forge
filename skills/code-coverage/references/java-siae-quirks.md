# Java / Maven / SIAE — Stack-Specific Reference

> Auto-loaded by Phase 4 when `stack.json.language == "java"` (or Maven build
> system detected). Do not edit without updating the Phase 4 loader instruction
> in SKILL.md.

<!-- extracted from SKILL.md on 2026-05-25 to reduce context for non-Java stacks -->

---

## Multi-module Maven repos (SIAE legacy)

`detect_stack.py` cerca automaticamente un pom aggregator (`<packaging>pom</packaging>` + `<modules>` non vuoto) fino a 4 livelli di profondità (override via `CC_POM_MAXDEPTH`).

Quando rilevato, `stack.json` contiene:
```json
{
  "manifest_root": "pae-deposito-musica",
  "maven_aggregator": {
    "manifest_root": "pae-deposito-musica",
    "aggregator_pom": "pae-deposito-musica/pom.xml",
    "modules": ["mod-a", "mod-b"],
    "selection_reason": "packaging-pom-with-modules"
  }
}
```

`select_command.py` inietta `-f <aggregator_pom>` nel `cov_cmd` Maven. Phase 6 esegue da repo root con il pom aggregator esplicito.

**Selection priority:**
1. Pom con `<packaging>pom</packaging>` + `<modules>` non vuoto (aggregator vero). PIU' SHALLOW vince.
2. Fallback: pom con `jacoco-maven-plugin` + `junit-jupiter` deps. PIU' SHALLOW vince.
3. None se nessun pom matcha.

**Override manuale:** se la detection sbaglia (es. aggregator > maxdepth=4), creare `.code-coverage/overrides.json`:
```json
{
  "manifest_root": "custom/path",
  "aggregator_pom": "custom/path/pom.xml"
}
```

---

## Maven placeholder handling (Task 02)

Pom SIAE usano ``${appVersion}``, ``${revision}`` iniettati dalla pipeline CI/CD ma non definiti nel pom. Phase 4 scansiona i pom, rileva i placeholder non risolti, e popola ``env.json.maven_placeholders``:

```json
{
  "maven_placeholders": {
    "appVersion": "1.0.0-SNAPSHOT",
    "revision": "1.0.0-SNAPSHOT"
  }
}
```

`select_command.py` propaga ``-D<token>=<value>`` nel mvn cmd Phase 6. Default = ``1.0.0-SNAPSHOT`` (override via ``overrides.json.maven_placeholders``).

**Esclusi:** built-in Maven (``${project.version}``, ``${pom.basedir}``, ...) e placeholder definiti localmente nel ``<properties>`` del pom.

**Override esempio:**
```json
{
  "maven_placeholders": {
    "appVersion": "2.0.0-RELEASE",
    "revision": "1.2.3"
  }
}
```

---

## JDK / Lombok compatibility (Task 03)

Phase 4 confronta JDK runtime + versione Lombok + Java source level contro una matrice di compatibilità nota. Emette ``env.json.jdk_compat``:

```json
{
  "jdk_compat": {
    "severity": "HARD-WARN",
    "reason": "Lombok 1.18.16 max_jdk=17, runtime is 25 → TypeTag UNKNOWN expected",
    "suggested_fix": "export JAVA_HOME=$(/usr/libexec/java_home -v 17)",
    "jdk_major": 25,
    "lombok_version": "1.18.16",
    "source_level": "1.7"
  }
}
```

**Severity levels:**

- ``OK`` — combinazione compatibile, run procede
- ``WARN`` — combinazione subottimale (es. source 1.7 + JDK 25 senza Lombok): plugin Maven legacy possibly incompatibili
- ``HARD-WARN`` — combinazione che causerà BUILD ERROR (es. Lombok 1.18.16 + JDK 25): la skill consumer DEVE bloccare il primo run e suggerire ``suggested_fix`` prima di tentare ``mvn``

**Matrice Lombok → max JDK:**

| Lombok version    | Max JDK | Reason |
|-------------------|---------|--------|
| 1.18.0 — 1.18.22  | 17      | TypeTag UNKNOWN su JDK ≥ 18 (lombok issue #3247) |
| 1.18.23 — 1.18.29 | 20      | javac internals breaking JDK ≥ 21 |
| 1.18.30+          | 25      | Modern |

**Override:** ``--ignore-jdk-mismatch`` (CLI flag a ``validate_env.py``) downgrade HARD-WARN → WARN. Power-user only — la skill avvisa che il primo mvn run probabilmente fallirà.

**Consumer-side gate operativo** — Phase 4 (o qualsiasi consumer della skill) invoca:

```bash
bash skills/code-coverage/lib/phase4-gate.sh <repo>
```

Comportamento (exit codes):

| severity | exit | side effect |
|---|---|---|
| OK | 0 | silent |
| WARN | 0 | stderr: `[phase4] WARN: <reason>` |
| HARD-WARN | 2 | stderr: BLOCKED + suggested_fix + override hint, consumer aborta mvn |
| env.json mancante/malformato | 0 | fail-open (non blocca run legittimi) |

Sourceable anche come libreria: `source phase4-gate.sh; check_jdk_compat_gate <repo>` ritorna exit code.

---

## Surefire includes/excludes handling (Task 05)

Phase 4 estrae la configurazione di ``maven-surefire-plugin`` da ogni pom e popola ``env.json.surefire_config``:

```json
{
  "surefire_config": {
    "includes": ["**/BollettinoMusicaServiceImplTest.java"],
    "excludes": [],
    "restrictive": true
  }
}
```

``restrictive=true`` significa che gli ``<includes>`` configurati NON matchano i pattern surefire standard (``**/*Test.java``, ``**/Test*.java``, ``**/*Tests.java``). Risultato: i nuovi test generati da Phase 5 verrebbero ignorati silenziosamente → coverage falsa 0% sui nuovi test → Phase 7 entra in repair loop su problema fantasma.

**Phase 5 behaviour quando restrictive=true:**

1. **Opzione A — Match existing pattern:** nominare i nuovi test come gli esistenti se semanticamente coerente
2. **Opzione B — Proposed pom patch:** emettere ``.code-coverage/proposed-pom-patches.diff`` con il patch ai ``<includes>`` da approvare. NON applicare automaticamente (Principle 1).

```bash
python3 skills/code-coverage/scripts/generate_pom_patches.py <repo> --package model
# Scrive .code-coverage/proposed-pom-patches.diff con +<include>**/model/*Test.java</include>
# Cumulative: invocazioni successive accumulano (più package patch in un singolo file)
```

Lo script legge ``env.json.surefire_config.restrictive`` — no-op se non restrittivo. Il diff prodotto è in formato unified compatibile con ``git apply``. L'operatore conferma manualmente prima di applicare.

Excludes (``**/IT*.java``, etc.) sono rispettati come da spec surefire — il naming dei test generati evita i pattern excluded.

---

## Jacoco-skipped modules (Task 06)

Moduli SIAE legacy hanno spesso ``<jacoco.skip>true</jacoco.skip>`` per design (es. ``siae-pae-bollettino-service`` è aggregator senza source Java). Phase 4 detecta queste proprietà e popola ``env.json.skipped_modules``.

Phase 8 reporting USA ``scripts/phase8_filter.py`` per applicare il filtro operativo:

```bash
python3 skills/code-coverage/scripts/phase8_filter.py <repo>
# Output JSON: bundle_line_pct, bundle_branch_pct, skipped_modules_excluded, modules_included
```

Lo script:
- Legge ``env.json.skipped_modules`` automaticamente
- Cerca ``target/site/jacoco-aggregate/jacoco.xml`` (priorità) o ``target/site/jacoco/jacoco.xml``
- Aggrega counters LINE/BRANCH solo sui `<group>` NOT skipped
- Bundle coverage calcolato è quello che Phase 8 compara contro il target chosen (Task 10)

I moduli SKIPPED compaiono nel report finale in sezione "Moduli skipped" con ragione ``jacoco.skip=true by-design`` — non contano come FAIL.

---

## Entity setter detection (Task 08)

Entity Hibernate SIAE legacy hanno setter con logica nascosta (normalizer, escape, conditional). Round-trip naive (``set("Foo"); get() == "Foo"``) fallisce silenziosamente → Phase 7 repair loop su pattern ricorrente.

`scripts/setter_scanner.py` pre-scansiona i `.java` del repo e classifica:

```json
{
  "BollettinoMusica": {
    "setTitolo": {
      "kind": "non_trivial",
      "transforms": ["lowercase", "unescape_html"],
      "has_conditional": false
    },
    "setClasseStampa": {
      "kind": "non_trivial",
      "transforms": ["lowercase"],
      "has_conditional": false
    },
    "setId": {"kind": "trivial", "transforms": [], "has_conditional": false}
  }
}
```

Usage CLI:
```bash
python3 skills/code-coverage/scripts/setter_scanner.py <repo> --write
# Scrive .code-coverage/setter-scan.json
```

**Phase 5 generation pattern:**

| Classificazione | Test generato |
|---|---|
| ``trivial`` (``this.x = x;``) | Round-trip naive |
| ``non_trivial`` + transforms (es. ``lowercase``) | Assertion adapted (``assertEquals("foo", entity.getX())`` per input ``"FOO"``) + branch null/empty |
| ``has_conditional=true`` | Smoke test only (assert non-null) + WARN ``decisions.log`` |

Transforms native risolte da ``apply_transforms()``: ``trim``, ``lowercase``, ``uppercase``. Altre (``escape_html``, ``replace``) sono pass-through con WARN.

---

## Java source level support (Task 07)

Phase 4 deriva ``compat_profile`` dal source level Java (``<maven.compiler.source>`` o ``<java.version>``) e popola ``env.json``:

```json
{
  "java_source_level": "1.7",
  "compat_profile": "legacy-java"
}
```

**Profili supportati:**

| source level | compat_profile | template selezionato (con vanilla variant) |
|---|---|---|
| < 10 (1.7/1.8/8/9) | ``legacy-java`` | ``junit5-java8.template.java`` (no var, no text-blocks) |
| 10-13 | ``modern-java-10`` | ``junit5.template.java`` (var ok, no text-blocks) |
| 14+ | ``modern-java-14`` | ``junit5.template.java`` (full modern) |

**Selezione template (4-way matrix):**

`template-cache.sh` combina ``compat_profile`` + ``assertion_lib`` (Task 04):

| compat_profile | assertion_lib | template |
|---|---|---|
| modern-* | assertj | ``junit5.template.java`` (default) |
| modern-* | junit5_vanilla | ``junit5-vanilla.template.java`` |
| legacy-java | assertj | ``junit5-java8.template.java`` |
| legacy-java | junit5_vanilla | ``junit5-java8-vanilla.template.java`` |

I template Java 8 usano placeholder ``{{TypeXxx}}`` per tipi espliciti (no ``var`` keyword) — Phase 5 generation deve risolvere i tipi durante l'interpolazione.

---

## Assertion library — NO auto-add deps (Task 04, rationale)

> Principle: `Never add assertion library deps automatically.` (kept in SKILL.md.)

Phase 4 (validate_env.py) rileva la libreria di assertion presente nel pom Java:

- ``assertj-core`` in deps → ``env.json.assertion_lib = "assertj"`` → template
  ``junit5.template.java`` (AssertJ style: ``assertThat(x).isEqualTo(y)``)
- Solo JUnit5 vanilla (no AssertJ) → ``env.json.assertion_lib = "junit5_vanilla"``
  → template ``junit5-vanilla.template.java`` (``assertEquals(expected, actual)``)

**Principle 1 enforcement:** la skill NON modifica autonomamente il pom per
aggiungere AssertJ. È responsabilità dell'utente decidere l'upgrade. Il template
vanilla è funzionalmente equivalente per le assertion comuni.

**Detection scope:** scansiona aggregator pom + tutti i moduli figli (path
letti da ``stack.json.maven_aggregator.modules`` quando rilevato in Task 01).
AssertJ presente in UN qualsiasi modulo → template AssertJ globale.

---

## mvn invocation strategy (Task 09)

Phase 6 supporta due strategy mvn:

| Strategy | Comportamento | Quando |
|---|---|---|
| ``single-shot`` (default) | 1 mvn finale con tutti i test, parse surefire-reports per fail, Phase 7 ri-esegue solo i Class#method falliti | Default + Spring Boot detected |
| ``verify-each`` (opt-in legacy) | mvn separato per ogni batch generato | ``--verify-each`` CLI flag |

`env.json.mvn_strategy` + `env.json.is_spring_boot` informano Phase 6.

**Wall-clock benefit:** su Spring Boot 2.5 (boot context ~20-30s × 3 batch) il single-shot porta da ~12 min a ~4-5 min (60% saved).

**Phase 7 skinny invocation:**
```bash
mvn test -Dtest=ClassName#methodName -Dsurefire.failIfNoSpecifiedTests=false
```

`scripts/surefire_parser.py` estrae `Class#method` da `target/surefire-reports/TEST-*.xml`:
```bash
python3 skills/code-coverage/scripts/surefire_parser.py target/surefire-reports
# Output: it.siae.FooTest#testFail
#         it.siae.BarTest#testNPE
```
