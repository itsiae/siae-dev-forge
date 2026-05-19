# Task 06 — select_command.py: manifest_root usage + JaCoCo plugin pre-check

**Fix-group:** G2, G10
**ADR riferito:** ADR-2, ADR-10 (Maven snippet con `<executions>`)
**Stato:** [PENDING]
**Dipendenze:** Task 03 (manifest_root field in stack.json)

## File modificati

- `skills/code-coverage/scripts/select_command.py`
- `skills/code-coverage/scripts/tests/test_select_command_multimodule.py` (extend)

## Test (TDD-first)

1. `test_jacoco_plugin_missing_emits_actionable_error`:
   - Setup: `pom.xml` con `<jacoco.version>0.8.12</jacoco.version>` ma SENZA `<artifactId>jacoco-maven-plugin</artifactId>` in `<plugins>`
   - Atteso: `select_command.py` output con `error` field contenente la stringa `"jacoco-maven-plugin"` E la stringa `"<executions>"` (snippet completo)

2. `test_jacoco_plugin_present_returns_command`:
   - Setup: `pom.xml` con plugin wired correttamente
   - Atteso: `cov_cmd="mvn -T 1C test jacoco:report"`, `error=None`

3. `test_manifest_root_used_when_set`:
   - Setup: `stack.json` con `manifest_root="modules/service/lambda"`, dir contiene `package.json` con vitest
   - Atteso: `cov_cmd` con prefisso `cd modules/service/lambda && ...` OR il consumer SKILL.md riceve `manifest_root` e fa `cd` esplicito (verificare convention)

## Implementazione

In `select_command.py`:

1. Estendi `_resolve_jacoco_report_path` con plugin check:
   ```python
   _JACOCO_PLUGIN_SNIPPET = """\
   <plugin>
     <groupId>org.jacoco</groupId>
     <artifactId>jacoco-maven-plugin</artifactId>
     <version>0.8.12</version>
     <executions>
       <execution>
         <id>prepare-agent</id>
         <goals><goal>prepare-agent</goal></goals>
       </execution>
       <execution>
         <id>report</id>
         <phase>test</phase>
         <goals><goal>report</goal></goals>
       </execution>
     </executions>
   </plugin>"""

   def _pom_has_jacoco_plugin(pom_path: Path) -> bool:
       try:
           content = pom_path.read_text(encoding="utf-8", errors="ignore")
       except OSError:
           return False
       return "<artifactId>jacoco-maven-plugin</artifactId>" in content
   ```

2. In `select_fields(stack_key="java", ...)`:
   ```python
   if stack_key == "java" and has_pom:
       pom = repo_root / "pom.xml"
       if not _pom_has_jacoco_plugin(pom):
           err = (
               "jacoco-maven-plugin not configured in pom.xml. "
               "Add this to <plugins>:\n" + _JACOCO_PLUGIN_SNIPPET
           )
           return None, None, None, err
       # ... resto invariato
   ```

3. Esporta `manifest_root` nell'output: legge da `stack.json`, aggiunge field `manifest_root` al JSON output di `emit()`.

## Criterio di accettazione

- 3/3 test PASS
- E2E: `select_command.py /tmp/pae-pae-services-be-clone` → error contiene snippet pronto
- Output JSON includes `manifest_root` field
