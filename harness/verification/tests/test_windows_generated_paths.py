from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def test_windows_generated_paths_preserve_urls_and_encode_eslint_imports(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[3] / 'apps/web/scripts/fix-nuxt-tsconfig-paths.mjs'
    node = shutil.which('node')
    assert node, 'The workspace Node runtime is required for the generated-path contract'
    nuxt = tmp_path / '.nuxt'
    (nuxt / 'types').mkdir(parents=True)
    config = nuxt / 'types' / 'tsconfig.json'
    config.write_text(json.dumps({
        'extends': './D:/repo with spaces/#generated/base.json',
        'compilerOptions': {'paths': {'@/*': ['./D:/repo/app/*'], '~/*': ['./relative/*']}},
        'url': 'file:///D:/already%20valid/module.mjs',
    }), encoding='utf-8')
    eslint = nuxt / 'eslint.config.mjs'
    eslint.write_text(
        "import { createConfig } from './D:/repo with spaces/#generated/create-config.mjs'\n"
        'export { extra } from "./D:/repo with spaces/#generated/extra.mjs"\n'
        "import './D:/repo with spaces/#generated/side-effect.mjs'\n"
        "export { relative } from './relative.mjs'\n"
        "import 'file:///D:/already%20valid/module.mjs'\n"
        "export default { literal: './D:/data-is-not-an-import' }\n",
        encoding='utf-8',
    )
    for _ in range(2):
        result = subprocess.run(
            [node, str(script)], cwd=tmp_path, capture_output=True, text=True,
            encoding='utf-8', timeout=30, check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(config.read_text(encoding='utf-8'))
        assert payload['extends'] == 'D:/repo with spaces/#generated/base.json'
        assert payload['compilerOptions']['paths']['@/*'] == ['D:/repo/app/*']
        assert payload['compilerOptions']['paths']['~/*'] == ['./relative/*']
        assert payload['url'] == 'file:///D:/already%20valid/module.mjs'
        generated = eslint.read_text(encoding='utf-8')
        for filename in ('create-config.mjs', 'extra.mjs', 'side-effect.mjs'):
            assert f'file:///D:/repo%20with%20spaces/%23generated/{filename}' in generated
        assert "from './relative.mjs'" in generated
        assert "import 'file:///D:/already%20valid/module.mjs'" in generated
        assert "literal: './D:/data-is-not-an-import'" in generated
        if _ == 0:
            first_output = generated
        else:
            assert generated == first_output
