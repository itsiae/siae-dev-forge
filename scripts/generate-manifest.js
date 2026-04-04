#!/usr/bin/env node
/**
 * generate-manifest.js
 *
 * Allinea automaticamente i conteggi skill/hook/command/agent in:
 *   - .claude-plugin/plugin.json
 *   - .claude-plugin/marketplace.json
 *   - README.md
 *
 * Conta:
 *   - skills:   sotto-directory in skills/
 *   - commands:  file .md in commands/ (0 se la dir non esiste)
 *   - agents:    file .md in agents/  (0 se la dir non esiste)
 *   - hooks:     chiavi dell'oggetto "hooks" in hooks/hooks.json
 *
 * Uso:  node scripts/generate-manifest.js
 */

'use strict';

const fs   = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');

// ── Conteggi ────────────────────────────────────────────────────────────────

function countDirs(dir) {
  if (!fs.existsSync(dir)) return 0;
  return fs.readdirSync(dir, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .length;
}

function countMdFiles(dir) {
  if (!fs.existsSync(dir)) return 0;
  return fs.readdirSync(dir)
    .filter(f => f.endsWith('.md'))
    .length;
}

function countHooks() {
  const hooksFile = path.join(ROOT, 'hooks', 'hooks.json');
  const data = JSON.parse(fs.readFileSync(hooksFile, 'utf8'));
  return Object.keys(data.hooks).length;
}

const skillCount   = countDirs(path.join(ROOT, 'skills'));
const commandCount = countMdFiles(path.join(ROOT, 'commands'));
const agentCount   = countMdFiles(path.join(ROOT, 'agents'));
const hookCount    = countHooks();

const summary = `${skillCount} skill, ${commandCount} comandi, ${agentCount} agent, ${hookCount} hook`;

console.log(`Conteggi rilevati: ${summary}`);

// ── Descrizione ─────────────────────────────────────────────────────────────

const DESC_PREFIX = 'SIAE Development Forge - AI SDLC Chain per sviluppo software conforme a standard SIAE.';
const newDescription = `${DESC_PREFIX} ${summary}.`;

// ── plugin.json ─────────────────────────────────────────────────────────────

function updatePluginJson() {
  const filePath = path.join(ROOT, '.claude-plugin', 'plugin.json');
  const plugin   = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  plugin.description = newDescription;
  fs.writeFileSync(filePath, JSON.stringify(plugin, null, 2) + '\n', 'utf8');
  console.log(`Aggiornato: ${path.relative(ROOT, filePath)}`);
}

// ── marketplace.json ────────────────────────────────────────────────────────

function updateMarketplaceJson() {
  const filePath    = path.join(ROOT, '.claude-plugin', 'marketplace.json');
  const marketplace = JSON.parse(fs.readFileSync(filePath, 'utf8'));

  // Aggiorna la description del plugin "siae-devforge" nell'array plugins
  for (const p of marketplace.plugins) {
    if (p.name === 'siae-devforge') {
      p.description = newDescription;
    }
  }

  fs.writeFileSync(filePath, JSON.stringify(marketplace, null, 2) + '\n', 'utf8');
  console.log(`Aggiornato: ${path.relative(ROOT, filePath)}`);
}

// ── README.md ───────────────────────────────────────────────────────────────

function updateReadme() {
  const filePath = path.join(ROOT, 'README.md');
  let content    = fs.readFileSync(filePath, 'utf8');

  // Matcha la riga con i conteggi: "con NN skill, NN comandi, NN agent, NN hook"
  const pattern = /con \d+ skill, \d+ comandi, \d+ agent, \d+ hook/;
  if (pattern.test(content)) {
    content = content.replace(pattern, `con ${summary}`);
    fs.writeFileSync(filePath, content, 'utf8');
    console.log(`Aggiornato: ${path.relative(ROOT, filePath)}`);
  } else {
    console.warn('WARN: pattern conteggi non trovato in README.md — nessuna modifica');
  }
}

// ── Main ────────────────────────────────────────────────────────────────────

updatePluginJson();
updateMarketplaceJson();
updateReadme();

console.log('Done.');
