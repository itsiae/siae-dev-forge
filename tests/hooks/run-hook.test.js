// Node built-in test runner: no external deps (Node 18+).
// Validates cross-platform launcher contract BEFORE implementation exists.
// Tests must FAIL initially (RED) because hooks/run-hook.js does not exist yet.

'use strict';

const { test, describe, beforeEach } = require('node:test');
const assert = require('node:assert');
const path = require('node:path');

// Module under test -- will not exist on RED iteration.
const MODULE_PATH = path.resolve(__dirname, '../../hooks/run-hook.js');

function loadModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

describe('run-hook.js -- cross-platform launcher', () => {
    describe('findBashOnWindows()', () => {
        test('returns null if no candidate path exists and where bash fails', () => {
            const mod = loadModule();
            const deps = {
                existsSync: () => false,
                spawnSync: () => ({ status: 1, stdout: '' }),
                env: {}
            };
            assert.strictEqual(mod.findBashOnWindows(deps), null);
        });

        test('returns first existing candidate (machine-wide Git for Windows)', () => {
            const mod = loadModule();
            const expected = 'C:\\Program Files\\Git\\bin\\bash.exe';
            const deps = {
                existsSync: (p) => p === expected,
                spawnSync: () => ({ status: 1, stdout: '' }),
                env: {}
            };
            assert.strictEqual(mod.findBashOnWindows(deps), expected);
        });

        test('falls back to scoop user profile when Program Files absent', () => {
            const mod = loadModule();
            const scoop = 'C:\\Users\\dev\\scoop\\apps\\git\\current\\bin\\bash.exe';
            const deps = {
                existsSync: (p) => p === scoop,
                spawnSync: () => ({ status: 1, stdout: '' }),
                env: { USERPROFILE: 'C:\\Users\\dev' }
            };
            assert.strictEqual(mod.findBashOnWindows(deps), scoop);
        });

        test('falls back to PortableGit embedded location', () => {
            const mod = loadModule();
            const portable = 'C:\\Users\\dev\\AppData\\Local\\DevForge\\PortableGit\\bin\\bash.exe';
            const deps = {
                existsSync: (p) => p === portable,
                spawnSync: () => ({ status: 1, stdout: '' }),
                env: { LOCALAPPDATA: 'C:\\Users\\dev\\AppData\\Local' }
            };
            assert.strictEqual(mod.findBashOnWindows(deps), portable);
        });

        test('falls back to PATH lookup via where bash', () => {
            const mod = loadModule();
            const custom = 'D:\\custom\\bash.exe';
            const deps = {
                existsSync: (p) => p === custom,
                spawnSync: (cmd, args) => {
                    if (cmd === 'where' && args[0] === 'bash') {
                        return { status: 0, stdout: `${custom}\r\n` };
                    }
                    return { status: 1, stdout: '' };
                },
                env: {}
            };
            assert.strictEqual(mod.findBashOnWindows(deps), custom);
        });
    });

    describe('dispatch(platform, scriptName, args, deps)', () => {
        test('Unix: delegates to bash with hook script path', () => {
            const mod = loadModule();
            const calls = [];
            const deps = {
                platform: 'linux',
                hookDir: '/plugin/hooks',
                spawnSync: (cmd, args) => {
                    calls.push({ cmd, args });
                    return { status: 0 };
                },
                existsSync: () => true
            };
            const exitCode = mod.dispatch('session-start', ['--flag'], deps);
            assert.strictEqual(exitCode, 0);
            assert.strictEqual(calls.length, 1);
            assert.strictEqual(calls[0].cmd, 'bash');
            assert.deepStrictEqual(calls[0].args, ['/plugin/hooks/session-start', '--flag']);
        });

        test('Windows with bash present: exec hook via detected bash', () => {
            const mod = loadModule();
            const bashPath = 'C:\\Program Files\\Git\\bin\\bash.exe';
            const calls = [];
            const deps = {
                platform: 'win32',
                hookDir: 'C:\\plugin\\hooks',
                existsSync: (p) => p === bashPath,
                spawnSync: (cmd, args) => {
                    calls.push({ cmd, args });
                    return { status: 7 };
                },
                env: {}
            };
            const exitCode = mod.dispatch('session-start', [], deps);
            assert.strictEqual(exitCode, 7);
            assert.strictEqual(calls[0].cmd, bashPath);
        });

        test('Windows without bash: auto-triggers install.ps1 and retries', () => {
            const mod = loadModule();
            const bashPath = 'C:\\Program Files\\Git\\bin\\bash.exe';
            const installScript = 'C:\\plugin\\install.ps1';
            let installCalled = false;
            let bashExistsAfterInstall = false;

            const deps = {
                platform: 'win32',
                hookDir: 'C:\\plugin\\hooks',
                installScript: installScript,
                existsSync: (p) => {
                    if (p === installScript) return true;
                    if (p === bashPath) return bashExistsAfterInstall;
                    return false;
                },
                spawnSync: (cmd, args) => {
                    if (cmd === 'powershell' && args.includes(installScript)) {
                        installCalled = true;
                        bashExistsAfterInstall = true;
                        return { status: 0 };
                    }
                    if (cmd === bashPath) {
                        return { status: 0 };
                    }
                    return { status: 1, stdout: '' };
                },
                env: {}
            };
            const exitCode = mod.dispatch('session-start', [], deps);
            assert.strictEqual(installCalled, true, 'install.ps1 should have been triggered');
            assert.strictEqual(exitCode, 0);
        });

        test('Windows without bash AND install.ps1 missing: exits 0 (silent degradation, no regression)', () => {
            const mod = loadModule();
            const deps = {
                platform: 'win32',
                hookDir: 'C:\\plugin\\hooks',
                installScript: 'C:\\plugin\\install.ps1',
                existsSync: () => false,
                spawnSync: () => ({ status: 1, stdout: '' }),
                env: {}
            };
            const exitCode = mod.dispatch('session-start', [], deps);
            assert.strictEqual(exitCode, 0);
        });

        test('Windows auto-install fails: exits 0 (silent, plugin keeps working)', () => {
            const mod = loadModule();
            const installScript = 'C:\\plugin\\install.ps1';
            const deps = {
                platform: 'win32',
                hookDir: 'C:\\plugin\\hooks',
                installScript: installScript,
                existsSync: (p) => p === installScript,
                spawnSync: (cmd) => {
                    if (cmd === 'powershell') return { status: 1 };
                    return { status: 1, stdout: '' };
                },
                env: {}
            };
            const exitCode = mod.dispatch('session-start', [], deps);
            assert.strictEqual(exitCode, 0);
        });
    });
});
