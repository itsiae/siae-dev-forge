// lib/atomic_append.js — append durevole una-riga (lock già acquisito dal wrapper bash).
// Riceve il percorso file come argv[2], la riga via stdin.
// Apre il file in append (O_APPEND) + fsyncSync prima di chiudere.
// Exit 0 = successo, Exit 1 = errore I/O.
//
// IMPORTANT — caller contract:
//   The caller (_devforge_lock_append in logger.sh) MUST pass through
//   _devforge_disk_gate before invoking this script. A partial write on ENOSPC
//   is not safe: the fd is opened with O_APPEND, so a failed writeSync may leave
//   a partial line in the file. Without the disk gate, low-disk conditions can
//   produce corrupt JSONL that is unrecoverable. Never invoke this script directly
//   without the disk-space pre-check.
'use strict';
const fs = require('fs');
const file = process.argv[2];
if (!file) {
    process.stderr.write('atomic_append.js: missing file argument\n');
    process.exit(1);
}
let data = '';
process.stdin.on('data', function(c) { data += c; });
process.stdin.on('end', function() {
    var fd;
    // Record initial file size for potential truncate on ENOSPC (best-effort partial-write recovery).
    var initialSize = -1;
    try { initialSize = fs.statSync(file).size; } catch (_) {}
    try {
        fd = fs.openSync(file, 'a');
        try {
            fs.writeSync(fd, data);
            fs.fsyncSync(fd);
        } finally {
            fs.closeSync(fd);
        }
    } catch (e) {
        // Attempt to truncate to initial position on I/O error to avoid leaving a partial line.
        if (initialSize >= 0) {
            try { fs.truncateSync(file, initialSize); } catch (_) {}
        }
        process.stderr.write('atomic_append.js error: ' + e.message + '\n');
        process.exit(1);
    }
});
process.stdin.on('error', function(e) {
    process.stderr.write('atomic_append.js stdin error: ' + e.message + '\n');
    process.exit(1);
});
