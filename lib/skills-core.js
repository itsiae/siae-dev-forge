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

  if (namePhaseMap[name]) {
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

  // Extract trigger from description (first sentence or up to first period)
  let trigger = skill.description || '';
  const triggerMatch = trigger.match(/[Tt]rigger:\s*(.+)/);
  if (triggerMatch) {
    trigger = triggerMatch[1].replace(/\.\s*$/, '');
  } else {
    // Use first meaningful clause
    trigger = trigger.split('.')[0].replace(/^Use when\s*/i, '').trim();
  }
  if (trigger.length > 80) {
    trigger = trigger.substring(0, 77) + '...';
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

  return {
    table: lines.join('\n'),
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
  findSkillsInDir,
  resolveSkillPath,
  stripFrontmatter,
  buildCatalog,
};
