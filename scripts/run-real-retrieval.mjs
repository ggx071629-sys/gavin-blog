import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { stopTree } from './assistant-dev-process.mjs';

const api = fileURLToPath(new URL('../apps/api/', import.meta.url));
const python = join(api, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const child = spawn(python, ['-m', 'app.local_embedding.local', ...process.argv.slice(2)], {
  cwd: api,
  stdio: 'inherit',
  env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' },
  windowsHide: true,
  detached: process.platform !== 'win32',
});
child.on('error', (error) => { console.error(error.message); process.exitCode = 1; });
child.on('exit', (code) => { process.exitCode = code ?? 1; });
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    stopTree(child).catch((error) => { console.error(error.message); process.exitCode = 1; });
  });
}
