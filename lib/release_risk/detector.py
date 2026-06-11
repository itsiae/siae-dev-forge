"""Detector criteri 1-15 (criteri 16-18 hanno file dedicati)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
from lib.release_risk.schema import CriterionResult


def criterion_1_db_change(diff_files: list[str], diff_content: str) -> CriterionResult:
    """+3 se DB change (DDL/DML) trovato."""
    # xml solo con hint DB nel path: \.xml$ generico flaggava pom.xml/logback.xml (+3 spurio)
    file_pattern = re.compile(
        r"\.(sql|hql)$|migration|liquibase|flyway|changelog|V\d+__|\bdb/.*\.xml$", re.I
    )
    content_pattern = re.compile(
        r"CREATE TABLE|ALTER TABLE|DROP TABLE|INSERT INTO|UPDATE .+ SET|DELETE FROM|ADD COLUMN|DROP COLUMN"
        r"|<createTable|<addColumn|<dropColumn|<dropTable|<renameColumn|<modifyDataType",
        re.I,
    )
    matched_files = [f for f in diff_files if file_pattern.search(f)]
    has_ddl = bool(content_pattern.search(diff_content))
    if matched_files or has_ddl:
        ev = [f"file:{f}" for f in matched_files[:5]]
        if has_ddl:
            ev.append("ddl_keyword_detected")
        return CriterionResult(id=1, name="Database change (DDL/DML)", status="YES",
                               weight=3, evidence=ev, source="diff:grep")
    return CriterionResult(id=1, name="Database change (DDL/DML)", status="NO",
                           weight=3, source="diff:grep")


def criterion_2_ocp_config(diff_files: list[str], diff_content: str) -> CriterionResult:
    """+2 se OCP/K8s config change."""
    file_pattern = re.compile(r"\.(yaml|yml)$|openshift|ocp|deployment|route|configmap|secret|helm|k8s|kubernetes", re.I)
    content_pattern = re.compile(r"kind:\s*(Deployment|Route|Secret|ConfigMap)", re.I)
    matched = [f for f in diff_files if file_pattern.search(f)]
    has_kind = bool(content_pattern.search(diff_content))
    if matched or has_kind:
        ev = [f"file:{f}" for f in matched[:5]]
        return CriterionResult(id=2, name="OCP/K8s config change", status="YES",
                               weight=2, evidence=ev, source="diff:grep")
    return CriterionResult(id=2, name="OCP/K8s config change", status="NO", weight=2, source="diff:grep")


def criterion_3_breaking_api(diff_files: list[str], diff_content: str) -> CriterionResult:
    """+3 se breaking API: endpoint rimossi o firma cambiata."""
    removed_endpoint = re.compile(
        r"^-\s*.*(@(Get|Post|Put|Delete|Path)Mapping|@RequestMapping)",
        re.MULTILINE,
    )
    if removed_endpoint.search(diff_content):
        return CriterionResult(id=3, name="Breaking API changes", status="YES",
                               weight=3, evidence=["removed_mapping_annotation"],
                               source="diff:grep")
    return CriterionResult(id=3, name="Breaking API changes", status="NO", weight=3, source="diff:grep")


def criterion_4_ext_deps(diff_files: list[str], diff_content: str) -> CriterionResult:
    """+2 se nuove/modificate dipendenze esterne."""
    dep_files = {"pom.xml", "package.json", "package-lock.json", "requirements.txt",
                 "build.gradle", "Cargo.toml", "go.mod"}
    matched = [f for f in diff_files if Path(f).name in dep_files]
    if matched:
        return CriterionResult(id=4, name="External dependencies changed", status="YES",
                               weight=2, evidence=[f"file:{f}" for f in matched],
                               source="diff:files")
    return CriterionResult(id=4, name="External dependencies changed", status="NO",
                           weight=2, source="diff:files")


def criterion_5_critical_service_stub(service_name: str, kg_lookup_fn=None) -> CriterionResult:
    """+3 se servizio critico. Delega a kg_lookup_fn (vedi task-12)."""
    if kg_lookup_fn is None:
        return CriterionResult(id=5, name="Critical service", status="REQUIRES_INPUT",
                               weight=3, source="ask:user",
                               notes="kg_lookup_fn not provided")
    return kg_lookup_fn(service_name)


def criterion_6_first_release(git_tag_count: int, tag_lookup_status: str = "OK") -> CriterionResult:
    """+2 se prima release del servizio (nessun tag release precedente).

    tag_lookup_status="UNAVAILABLE" se subprocess git ha fallito → TOOL_UNAVAILABLE
    (no silent fallback a YES da count=0 indistinguibile).
    """
    if tag_lookup_status == "UNAVAILABLE":
        return CriterionResult(id=6, name="First release", status="TOOL_UNAVAILABLE",
                               weight=2, evidence=["git_tag_lookup_failed"],
                               source="git:tag")
    if git_tag_count == 0:
        return CriterionResult(id=6, name="First release", status="YES", weight=2,
                               evidence=[f"git_tag_count={git_tag_count}"],
                               source="git:tag")
    return CriterionResult(id=6, name="First release", status="NO", weight=2,
                           evidence=[f"git_tag_count={git_tag_count}"], source="git:tag")


def criterion_7_complex_rollback(c1_status: str, c9_status: str, diff_content: str) -> CriterionResult:
    """+2 se rollback complesso. Implied da Criterion 1 (DB change) o 9 (migration)."""
    if c1_status == "YES" or c9_status == "YES":
        return CriterionResult(id=7, name="Complex rollback", status="YES", weight=2,
                               evidence=["implied_by_c1_or_c9"], source="inferred")
    if re.search(r"irreversible|no rollback|one[- ]way|destructive", diff_content, re.I):
        return CriterionResult(id=7, name="Complex rollback", status="YES", weight=2,
                               evidence=["irreversible_keyword"], source="diff:grep")
    return CriterionResult(id=7, name="Complex rollback", status="NO", weight=2, source="inferred")


def criterion_8_downtime(diff_content: str) -> CriterionResult:
    """+3 se downtime richiesto (strategy Recreate o maxUnavailable: 1)."""
    pattern = re.compile(r"strategy:\s*Recreate|maxUnavailable:\s*1", re.I)
    if pattern.search(diff_content):
        return CriterionResult(id=8, name="Downtime required", status="YES", weight=3,
                               evidence=["recreate_strategy_or_maxunavailable_1"],
                               source="diff:grep")
    return CriterionResult(id=8, name="Downtime required", status="NO", weight=3, source="diff:grep")


def criterion_9_data_migration(diff_files: list[str], diff_content: str) -> CriterionResult:
    """+3 se data migration (script V*__*.sql, MigrationRunner classes)."""
    file_pattern = re.compile(r"migration|migrate|V\d+__|R__", re.I)
    content_pattern = re.compile(r"DataMigration|MigrationRunner|@Migration", re.I)
    matched = [f for f in diff_files if file_pattern.search(f)]
    if matched or content_pattern.search(diff_content):
        ev = [f"file:{f}" for f in matched[:5]]
        return CriterionResult(id=9, name="Data migration required", status="YES", weight=3,
                               evidence=ev, source="diff:grep")
    return CriterionResult(id=9, name="Data migration required", status="NO", weight=3,
                           source="diff:grep")


def criterion_10_feature_flag(diff_content: str) -> CriterionResult:
    """-1 se feature flag disabilitabile (mitigazione)."""
    pattern = re.compile(
        r"featureFlag|feature\.flag|FeatureToggle|@ConditionalOnProperty|ff4j|unleash|LaunchDarkly|isEnabled",
        re.I,
    )
    if pattern.search(diff_content):
        return CriterionResult(id=10, name="Feature flag (mitigation)", status="YES",
                               weight=-1, evidence=["flag_pattern_detected"],
                               source="diff:grep")
    return CriterionResult(id=10, name="Feature flag (mitigation)", status="NO",
                           weight=-1, source="diff:grep")


def criterion_11_coverage_stub(coverage_src_fn=None, sha: str = "") -> CriterionResult:
    """+2 se coverage < 70%. Delega a coverage_src_fn (vedi task-14)."""
    if coverage_src_fn is None:
        return CriterionResult(id=11, name="Coverage < 70%", status="REQUIRES_INPUT",
                               weight=2, source="ask:user",
                               notes="coverage_src_fn not provided")
    return coverage_src_fn(sha)


def criterion_12_e2e_tests(ci_config_present: bool, e2e_stage_found: bool) -> CriterionResult:
    """+2 se E2E non eseguiti. CI config + stage detection esterni (delegati a caller)."""
    if not ci_config_present:
        return CriterionResult(id=12, name="E2E tests not run", status="REQUIRES_INPUT",
                               weight=2, source="ask:user", notes="no CI config detected")
    if not e2e_stage_found:
        return CriterionResult(id=12, name="E2E tests not run", status="YES",
                               weight=2, evidence=["no e2e stage in .github/workflows/*.yml"],
                               source="diff:ci")
    return CriterionResult(id=12, name="E2E tests not run", status="NO", weight=2,
                           evidence=["e2e_stage_detected"], source="diff:ci")


def criterion_13_perf_tests(diff_content: str) -> CriterionResult:
    """-1 se perf test eseguiti (mitigazione)."""
    pattern = re.compile(r"jmeter|gatling|locust|k6|performance\.test|load\.test", re.I)
    if pattern.search(diff_content):
        return CriterionResult(id=13, name="Performance tests (mitigation)", status="YES",
                               weight=-1, evidence=["perf_tool_detected"], source="diff:grep")
    return CriterionResult(id=13, name="Performance tests (mitigation)", status="NO",
                           weight=-1, source="diff:grep")


def criterion_14_user_impact(user_impact_ge_50pct: Optional[bool]) -> CriterionResult:
    """+2 se impact > 50% utenti. Inferibile solo da user (caller passa risposta)."""
    if user_impact_ge_50pct is None:
        return CriterionResult(id=14, name="User impact > 50%", status="REQUIRES_INPUT",
                               weight=2, source="ask:user")
    return CriterionResult(id=14, name="User impact > 50%",
                           status="YES" if user_impact_ge_50pct else "NO",
                           weight=2, evidence=[f"user_confirmed={user_impact_ge_50pct}"],
                           source="ask:user")


def criterion_15_files_count(diff_files: list[str]) -> CriterionResult:
    """+1 se modificati > 10 file."""
    count = len(diff_files)
    if count > 10:
        return CriterionResult(id=15, name="Modified > 10 files", status="YES", weight=1,
                               evidence=[f"file_count={count}"], source="diff:count")
    return CriterionResult(id=15, name="Modified > 10 files", status="NO", weight=1,
                           evidence=[f"file_count={count}"], source="diff:count")
