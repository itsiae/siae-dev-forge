#!/usr/bin/env node
// Cross-platform hook launcher for siae-devforge plugin.
//
// Design: hooks.json invokes `node run-hook.js <script>` instead of
// `bash '...run-hook.cmd' <script>`. On Windows without Git Bash, the old
// approach made Claude Code fail at the `bash` prefix, never reaching the
// polyglot wrapper. Node is reliably present in the hook environment
// (Claude Code CLI is Node-based).
//
// OS detection is delegated to the OS via process.platform:
//   - win32: locate bash in 7 known paths + PATH fallback.
//            If missing, auto-trigger install.ps1, re-locate, exec hook.
//            If install also fails: silent exit 0 (no regression).
//   - unix (darwin/linux/...): bash is always present; exec directly.
//
// Dependency injection via `deps` parameter keeps findBashOnWindows and
// dispatch pure/testable without monkey-patching globals.

'use strict';

const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const WINDOWS_BASH_CANDIDATES = (env) => [
    'C:\\Program Files\\Git\\bin\\bash.exe',
    'C:\\Program Files (x86)\\Git\\bin\\bash.exe',
    env.LOCALAPPDATA && path.win32.join(env.LOCALAPPDATA, 'Programs', 'Git', 'bin', 'bash.exe'),
    env.USERPROFILE && path.win32.join(env.USERPROFILE, 'scoop', 'apps', 'git', 'current', 'bin', 'bash.exe'),
    'C:\\msys64\\usr\\bin\\bash.exe',
    'C:\\cygwin64\\bin\\bash.exe',
    env.LOCALAPPDATA && path.win32.join(env.LOCALAPPDATA, 'DevForge', 'PortableGit', 'bin', 'bash.exe')
].filter(Boolean);

function findBashOnWindows(deps) {
    const candidates = WINDOWS_BASH_CANDIDATES(deps.env);
    for (const c of candidates) {
        if (deps.existsSync(c)) return c;
    }
    const where = deps.spawnSync('where', ['bash'], { encoding: 'utf-8' });
    if (where.status === 0 && where.stdout) {
        const first = where.stdout.trim().split(/\r?\n/)[0];
        if (first && deps.existsSync(first)) return first;
    }
    return null;
}

function dispatch(scriptName, scriptArgs, deps) {
    const hookScript = deps.hookDir.includes('\\')
        ? `${deps.hookDir}\\${scriptName}`
        : `${deps.hookDir}/${scriptName}`;

    if (deps.platform !== 'win32') {
        const result = deps.spawnSync('bash', [hookScript, ...scriptArgs], { stdio: 'inherit' });
        return result.status !== null && result.status !== undefined ? result.status : 1;
    }

    // Windows: locate bash or auto-bootstrap via install.ps1
    let bash = findBashOnWindows(deps);
    if (!bash && deps.installScript && deps.existsSync(deps.installScript)) {
        const installResult = deps.spawnSync('powershell', [
            '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', deps.installScript
        ], { stdio: 'inherit' });
        if (installResult.status === 0) {
            bash = findBashOnWindows(deps);
        }
    }
    if (!bash) {
        // Silent degradation: matches pre-enforcement behavior so the plugin
        // keeps working (no telemetry but no crash).
        return 0;
    }
    const result = deps.spawnSync(bash, [hookScript, ...scriptArgs], { stdio: 'inherit' });
    return result.status !== null && result.status !== undefined ? result.status : 1;
}

module.exports = { findBashOnWindows, dispatch };

// Main entry point when invoked directly from hooks.json
if (require.main === module) {
    const scriptName = process.argv[2];
    if (!scriptName) {
        process.stderr.write('run-hook.js: missing script name\n');
        process.exit(1);
    }
    const scriptArgs = process.argv.slice(3);
    const hookDir = __dirname;
    const pluginRoot = path.resolve(hookDir, '..');
    const installScript = path.join(pluginRoot, 'install.ps1');

    const exitCode = dispatch(scriptName, scriptArgs, {
        platform: process.platform,
        hookDir: hookDir,
        installScript: installScript,
        existsSync: fs.existsSync,
        spawnSync: spawnSync,
        env: process.env
    });
    process.exit(exitCode);
}
