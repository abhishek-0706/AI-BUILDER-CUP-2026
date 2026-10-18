'use strict';
// Compatibility entry point. Real model calls require explicit free-tier confirmation.
process.argv.push('--live');
require('./eval');
