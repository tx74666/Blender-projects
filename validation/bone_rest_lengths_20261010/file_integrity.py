"""Record artist/source file integrity around isolated integration checks."""
import hashlib
import json
from pathlib import Path
import sys

folder = Path(__file__).resolve().parent
paths = [Path(r'D:\Blender\Projects\Character\X\X.blend'),
         Path(r'D:\Unity Projects\RandomRealm2\Assets\Art\Character\Cosha\Cosha.fbx'),
         Path(r'D:\Unity Projects\RandomRealm2\Assets\Art\Character\Cosha\Cosha.cdesigner.json')]
current = {str(path): {'bytes': path.stat().st_size,
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths}
if sys.argv[1] == 'before':
    (folder / 'artist_file_integrity_before.json').write_text(json.dumps(current, indent=2), encoding='utf-8')
else:
    before = json.loads((folder / 'artist_file_integrity_before.json').read_text(encoding='utf-8'))
    result = {'unchanged': current == before, 'before': before, 'after': current}
    (folder / 'artist_file_integrity_after.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    assert result['unchanged'], 'An artist/source file changed during isolated verification.'
print(json.dumps({'mode': sys.argv[1], 'files': len(current)}, indent=2))
