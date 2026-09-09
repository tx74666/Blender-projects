import ast
import hashlib
import json
import zipfile
from pathlib import Path

root = Path(r'D:\Blender\Projects\Character\X')
source = root / 'addons' / 'character_designer'
installed = Path(r'C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\character_designer')
files = sorted(p for p in source.iterdir() if p.is_file() and p.suffix in ('.py', '.md'))
for path in files:
    if path.suffix == '.py':
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    assert path.read_bytes() == (installed / path.name).read_bytes(), f'Installed mismatch: {path.name}'
archive = root / 'dist' / 'character_designer-0.37.0.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
    for path in files:
        package.write(path, 'character_designer/' + path.name)
with zipfile.ZipFile(archive) as package:
    assert package.testzip() is None
    for path in files:
        assert package.read('character_designer/' + path.name) == path.read_bytes()
report = {'archive': str(archive), 'files': len(files), 'python_files': sum(p.suffix == '.py' for p in files),
          'bytes': archive.stat().st_size, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'source_installed_archive_equal': True,
          'production_blend_sha256': hashlib.sha256((root / 'X.blend').read_bytes()).hexdigest()}
(root / '.codex-backups' / 'forearm-twist-probe' / 'release-0.37.0.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))

