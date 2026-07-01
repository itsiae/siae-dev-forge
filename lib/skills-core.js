#!/usr/bin/env node
/**
 * skills-core.js — Dynamic skill discovery for siae-devforge
 *
 * Scans skill directories, extracts YAML frontmatter, and builds
 * the skill catalog for the session-start hook.
 *
 * Usage:
 *   node lib/skills-core.js <plugin-root>
 *
 * Output (stdout): Markdown table of skills with name, trigger, type, phase.
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// Frontmatter extraction
// ---------------------------------------------------------------------------

/**
 * Extract YAML frontmatter fields (name, description) from a SKILL.md file.
 * Returns { name, description } or null if frontmatter is missing.
 */
function extractFrontmatter(filePath) {
  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch {
    return null;
  }

  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;

  const yaml = match[1];
  const result = {};

  // Extract name
  const nameMatch = yaml.match(/^name:\s*(.+)$/m);
  if (nameMatch) {
    result.name = nameMatch[1].trim().replace(/^["']|["']$/g, '');
  }

  // Extract description (supports multi-line YAML folded/literal/plain blocks)
  // Strategy: find "description:" line, then collect all subsequent indented lines
  const yamlLines = yaml.split('\n');
  let descLines = [];
  let inDesc = false;

  for (const line of yamlLines) {
    if (/^description:\s*/.test(line)) {
      inDesc = true;
      // Check for inline value (not just > or |)
      const inlineVal = line.replace(/^description:\s*/, '').replace(/^[>|]\s*$/, '').trim();
      if (inlineVal && inlineVal !== '>' && inlineVal !== '|') {
        descLines.push(inlineVal);
      }
      continue;
    }
    if (inDesc) {
      // Continuation lines are indented (start with space/tab)
      if (/^\s+/.test(line) && line.trim().length > 0) {
        descLines.push(line.trim());
      } else {
        break; // Non-indented line = end of description block
      }
    }
  }

  if (descLines.length > 0) {
    result.description = descLines.join(' ');
  }

  return result.name ? result : null;
}

// ---------------------------------------------------------------------------
// Skill discovery
// ---------------------------------------------------------------------------

/**
 * Find all SKILL.md files in a directory (one level deep: dir/<name>/SKILL.md).
 * Returns array of { name, description, dirName, filePath }.
 */
function findSkillsInDir(dir) {
  const skills = [];

  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return skills;
  }

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;

    const skillFile = path.join(dir, entry.name, 'SKILL.md');
    if (!fs.existsSync(skillFile)) continue;

    const fm = extractFrontmatter(skillFile);
    if (!fm) continue;

    skills.push({
      name: fm.name,
      description: fm.description || '',
      dirName: entry.name,
      filePath: skillFile,
    });
  }

  return skills;
}

// ---------------------------------------------------------------------------
// Path resolution
// ---------------------------------------------------------------------------

/**
 * Resolve a skill name to its SKILL.md path.
 * Searches in <pluginDir>/skills/ for a directory matching the skill name.
 */
function resolveSkillPath(skillName, pluginDir) {
  const skillsDir = path.join(pluginDir, 'skills');

  // Direct match: skill name == directory name
  const direct = path.join(skillsDir, skillName, 'SKILL.md');
  if (fs.existsSync(direct)) return direct;

  // Scan for matching frontmatter name
  const skills = findSkillsInDir(skillsDir);
  const match = skills.find(s => s.name === skillName);
  return match ? match.filePath : null;
}

// ---------------------------------------------------------------------------
// Frontmatter stripping
// ---------------------------------------------------------------------------

/**
 * Remove YAML frontmatter from content string.
 */
function stripFrontmatter(content) {
  return content.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/, '');
}

// ---------------------------------------------------------------------------
// Frontmatter phase extraction
// ---------------------------------------------------------------------------

/**
 * Read sdlc_phase from SKILL.md frontmatter (first choice for phase inference).
 * Returns the phase string or null if not present.
 */
function readPhaseFromFrontmatter(skillDir, skillName) {
  try {
    const content = fs.readFileSync(path.join(skillDir, skillName, 'SKILL.md'), 'utf-8');
    const fmMatch = content.match(/^---\n([\s\S]*?)\n---/);
    if (fmMatch) {
      const phaseMatch = fmMatch[1].match(/sdlc_phase:\s*(.+)/i);
      if (phaseMatch) return phaseMatch[1].trim();
    }
  } catch (e) { /* fallback */ }
  return null;
}

/**
 * True when punctuation at index terminates a sentence instead of being part
 * of an extension or token such as ".tf", "Vue.js", ".robot".
 */
function isSentenceBoundary(text, index) {
  const rest = text.slice(index + 1);
  if (/^\s*$/.test(rest)) return true;
  return /^\s+(?:(?:NOT|NON|BUT|MA)\b|["'`([{<]|[A-Z0-9])/.test(rest);
}

/**
 * Extract the user-facing trigger summary from a description.
 * Supports "Trigger:", "Use when:" and "Invoca quando" patterns.
 */
function extractTriggerText(skill) {
  const description = (skill.description || '').trim();
  if (!description) return '';

  const triggerPatterns = [
    /\bTrigger:\s*/i,
    /\bUse when:\s*/i,
    /\bInvoca quando:?\s*/i,
  ];

  let trigger = description;
  let matched = false;

  for (const pattern of triggerPatterns) {
    const match = pattern.exec(description);
    if (match) {
      trigger = description.slice(match.index + match[0].length).trim();
      matched = true;
      break;
    }
  }

  if (!matched) {
    trigger = trigger.replace(/^Use when\s*/i, '').trim();
  }

  for (let i = 0; i < trigger.length; i += 1) {
    if (!'.!?'.includes(trigger[i])) continue;
    if (isSentenceBoundary(trigger, i)) {
      trigger = trigger.slice(0, i).trim();
      break;
    }
  }

  return trigger.replace(/[.!?]\s*$/, '').trim();
}

// ---------------------------------------------------------------------------
// Catalog generation
// ---------------------------------------------------------------------------

/**
 * Infer skill type (Rigid/Flexible) and SDLC phase from description + content.
 */
function inferSkillMeta(skill) {
  const desc = (skill.description || '').toLowerCase();

  // Infer type: name-based map first (authoritative), then keyword fallback
  const nameTypeMap = {
    'siae-onboarding': 'Auto',
    'siae-brainstorming': 'Rigid',
    'siae-architecture': 'Flexible',
    'siae-git-workflow': 'Rigid',
    'siae-code-standards': 'Flexible',
    'siae-security': 'Flexible',
    'siae-iac': 'Flexible',
    'siae-data-engineering': 'Flexible',
    'siae-frontend': 'Flexible',
    'siae-flutter': 'Flexible',
    'siae-subagent-development': 'Rigid',
    'siae-tdd': 'Rigid',
    'siae-qa': 'Rigid',
    'siae-automation': 'Rigid',
    'siae-debugging': 'Rigid',
    'siae-documentation': 'Flexible',
    'siae-verification': 'Rigid',
    'siae-writing-skills': 'Flexible',
    'siae-finops': 'Flexible',
  };

  const name = (skill.name || '').toLowerCase();
  let type = nameTypeMap[name] || null;

  if (!type) {
    // Fallback: keyword-based inference from content
    type = 'Flexible';
    const rigidKeywords = ['rigid', 'iron law', 'legge di ferro', 'hard-gate'];
    try {
      const content = fs.readFileSync(skill.filePath, 'utf8').toLowerCase();
      // Check for explicit "Tipo: Rigid" or "Tipo:** Rigid" patterns first
      if (/tipo:\s*\*{0,2}\s*rigid/i.test(content)) {
        type = 'Rigid';
      } else if (rigidKeywords.some(k => content.includes(k))) {
        type = 'Rigid';
      }
    } catch { /* keep default */ }
  }

  // Infer phase from skill name first (most reliable), then fallback to description
  let phase = 'Cross-cutting';

  // Name-based phase mapping (high confidence)
  const namePhaseMap = {
    'siae-onboarding': '1. Init',
    'siae-codebase-map': '1. Init',
    'siae-git-worktrees': '1. Init',
    'siae-microservices-map': '1. Init',
    'siae-service-logic-map': '1. Init',
    'siae-brainstorming': '2. Design',
    'siae-writing-plans': '2. Design',
    'siae-finishing-branch': '3. Branching',
    'siae-architecture': '2. Design',
    'siae-git-workflow': '3. Branching',
    'siae-code-standards': '4. Implementation',
    'siae-security': '4. Implementation',
    'siae-iac': '4. Implementation',
    'siae-data-engineering': '4. Implementation',
    'siae-frontend': '4. Implementation',
    'siae-flutter': '4. Implementation',
    'siae-subagent-development': '4. Implementation',
    'siae-tdd': '5. Testing',
    'siae-qa': '5. Testing / QA',
    'siae-automation': '5. Testing / Automation',
    'siae-debugging': '6. QA Gate',
    'siae-documentation': '7. Release',
    'siae-verification': 'Cross-cutting',
    'siae-receiving-review': 'Cross-cutting',
    'siae-requesting-review': 'Cross-cutting',
    'siae-parallel-agents': '4. Implementation',
    'siae-executing-plans': '4. Implementation',
    'siae-writing-skills': 'Meta',
    'siae-finops': '4. Implementation',
  };

  // 1. Frontmatter sdlc_phase (highest priority)
  const skillsDir = path.dirname(skill.filePath ? path.dirname(skill.filePath) : '');
  const fmPhase = readPhaseFromFrontmatter(skillsDir, skill.dirName || '');
  if (fmPhase) {
    phase = fmPhase;
  } else if (namePhaseMap[name]) {
    // 2. namePhaseMap fallback
    phase = namePhaseMap[name];
  } else {
    // Fallback: infer from description keywords
    const phasePatterns = [
      [/onboarding|setup|init/, '1. Init'],
      [/brainstorm|architecture/, '2. Design'],
      [/branch|git.?workflow/, '3. Branching'],
      [/implement|code.?standard|security|iac|terraform|data.?eng|frontend/, '4. Implementation'],
      [/\btdd\b|test|qa|automat/, '5. Testing'],
      [/debug|rca/, '6. QA Gate'],
      [/document|hld|lld/, '7. Release'],
      [/verification|claim|complete/, 'Cross-cutting'],
      [/writing.?skill|creat.*skill/, 'Meta'],
    ];

    for (const [regex, p] of phasePatterns) {
      if (regex.test(desc)) {
        phase = p;
        break;
      }
    }
  }

  // Prefer authoritative summaries for the core workflows we want to trigger
  // reliably, then fall back to extraction from the frontmatter description.
  const nameTriggerMap = {
    'siae-brainstorming': 'QUALSIASI task implementativo: feature, bug fix, refactoring, config, ottimizzazione (SEMPRE prima di implementare)',
    'siae-writing-plans': 'dopo brainstorming approvato: scrivi o aggiorna il piano implementativo step-by-step',
    'siae-debugging': 'bug, errore, stacktrace, crash, test che fallisce, comportamento inatteso',
    'siae-tdd': 'qualsiasi scrittura di codice di produzione: implementazione, bug fix, refactoring',
    'siae-security': 'SEMPRE come companion skill per implementazione e review: codice, config, IAM, encryption, PII, ISWC/ISRC',
    'siae-git-workflow': 'QUALSIASI operazione git: checkout -b, commit, push, merge, tag, PR',
    'siae-finishing-branch': 'branch pronto per PR / ready to merge / apertura PR / gh pr create',
    'siae-blind-review': 'SEMPRE nel workflow review/pre-PR: blind review, audit spec-vs-codice, review senza diff',
    'siae-requesting-review': 'quando chiedi review su una PR: reviewer, PR aperta, pronto per review',
    'siae-receiving-review': 'quando ricevi feedback di review: commenti PR, CHANGES REQUESTED, fix richiesti',
  };

  let trigger = nameTriggerMap[name] || extractTriggerText(skill);
  if (trigger.length > 140) {
    trigger = trigger.substring(0, 137) + '...';
  }

  return { type, phase, trigger };
}

/**
 * Build a Markdown skill catalog table from discovered skills.
 * Excludes the meta-skill (using-devforge) from the table.
 */
function buildCatalog(pluginDir) {
  const skillsDir = path.join(pluginDir, 'skills');
  const skills = findSkillsInDir(skillsDir);

  // Sort: meta-skill first, then by phase, then by name
  const phaseOrder = { '1. Init': 1, '2. Design': 2, '3. Branching': 3, '4. Implementation': 4, '5. Testing': 5, '5. Testing / QA': 5.1, '5. Testing / Automation': 5.2, '6. QA Gate': 6, '7. Release': 7, 'Cross-cutting': 8, 'Meta': 9 };

  const enriched = skills
    .filter(s => s.name !== 'using-devforge')
    .map(s => ({ ...s, ...inferSkillMeta(s) }))
    .sort((a, b) => (phaseOrder[a.phase] || 99) - (phaseOrder[b.phase] || 99) || a.name.localeCompare(b.name));

  const lines = [
    '| Skill | INVOCA SE l\'utente menziona | Tipo | Fase SDLC |',
    '|-------|----------------------------|------|-----------|',
  ];

  for (const s of enriched) {
    lines.push(`| ${s.name} | ${s.trigger} | ${s.type} | ${s.phase} |`);
  }

  const alwaysOn = [
    '**Core Workflow DevForge (obbligatorio):**',
    '- Task implementativo (feature, bug fix, refactoring, config, ottimizzazione) -> `siae-brainstorming` PRIMA di tutto',
    '- Brainstorming approvato -> `siae-writing-plans`',
    '- Bug o failure da capire -> `siae-debugging` PRIMA del fix',
    '- Scrittura di codice di produzione -> `siae-tdd`',
    '- Qualsiasi implementazione o modifica tecnica -> skill di dominio + `siae-security` SEMPRE + `siae-tdd`',
    '- Operazioni git o apertura PR -> `siae-git-workflow` (e `siae-finishing-branch` prima della PR)',
    '- Qualsiasi review / pre-PR / audit -> skill di dominio + `siae-blind-review` SEMPRE; poi `siae-requesting-review` o `siae-receiving-review` secondo il momento',
    '- Prima di dichiarare successo/completamento -> `siae-verification`',
    '',
  ];

  const flowCoupling = [
    '**Legame Delle Skill Specialistiche Al Flusso:**',
    '- Le skill specialistiche non sostituiscono il workflow core: si AGGANCIANO a `siae-brainstorming`, `siae-debugging`, `siae-tdd`, `siae-security`, workflow review e `siae-verification`',
    '- Design o nuova iniziativa -> skill specialistica + `siae-brainstorming`, poi `siae-writing-plans`',
    '- Bug o regressione -> skill specialistica + `siae-debugging`, poi fix con `siae-tdd` + `siae-security`',
    '- Implementazione in corso -> skill specialistica + `siae-tdd` + `siae-security`',
    '- Review / PR / dichiarazione di completamento -> skill specialistica + workflow review + `siae-security` + `siae-verification`',
    '- Chiusura task / claim di completamento -> skill specialistica + `siae-verification`',
    '- Esempi di skill specialistiche da agganciare: `siae-architecture`, `siae-code-standards`, `siae-security`, `siae-iac`, `siae-data-engineering`, `siae-frontend`, `siae-flutter`, `siae-automation`, `siae-robot-framework`, `siae-finops`, `siae-codebase-map`, `siae-microservices-map`, `siae-service-logic-map`',
    '',
  ];

  // Disambiguation rules — injected after catalog table (Level 1, always in system prompt)
  const disambiguation = [
    '',
    '**Disambiguazione skill (quando piu\' skill matchano):**',
    '- Query su C4, HLD, bounded context, CQRS, microservizi vs monolite, pattern architetturale → `siae-architecture` + `siae-brainstorming`',
    '- Query su Playwright, Cypress, test E2E, CI/CD pipeline, GitHub Actions, automatizza test → `siae-automation` + `siae-brainstorming`',
    '- Query su Glue, PySpark, ETL, pipeline ingestion, Medallion, bronze-to-silver → `siae-data-engineering` + `siae-brainstorming`',
    '- Query su Terraform, terragrunt, VPC, ECS, Lambda, security group → `siae-iac` + `siae-brainstorming`',
    '- Query su bug, errore, stacktrace, crash, fallisce, non funziona → `siae-debugging` + `siae-brainstorming`',
    '- Query su git checkout, git commit, git push, branch, merge, tag → `siae-git-workflow` (brainstorming non richiesto per pure operazioni git)',
    '- `siae-brainstorming` per QUALSIASI task implementativo (feature, bug fix, refactoring, config, ottimizzazione): la profondita\' scala sempre; per i cambiamenti trivial (1 file, poche righe, path non-sensibile, non-IaC) il gate e\' silente, per i complessi resta obbligatorio. Produce SEMPRE un piano con subtask via siae-writing-plans.',
  ];

  return {
    table: alwaysOn.join('\n') + flowCoupling.join('\n') + lines.join('\n') + '\n' + disambiguation.join('\n'),
    count: enriched.length,
    skills: enriched,
  };
}

// ---------------------------------------------------------------------------
// CLI entry point
// ---------------------------------------------------------------------------

if (require.main === module) {
  const pluginDir = process.argv[2] || path.resolve(__dirname, '..');
  const catalog = buildCatalog(pluginDir);
  process.stdout.write(catalog.table + '\n');
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

module.exports = {
  extractFrontmatter,
  readPhaseFromFrontmatter,
  findSkillsInDir,
  resolveSkillPath,
  stripFrontmatter,
  buildCatalog,
};
