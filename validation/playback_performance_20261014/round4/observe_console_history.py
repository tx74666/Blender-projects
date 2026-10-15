"""One deferred read of the observed Console history; no scene operations."""
import bpy
import hashlib
import json
from pathlib import Path

space = bpy.context.space_data
assert space.type == 'CONSOLE'
target = Path(r'D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\console_history_native.json')

def observe():
    tail = space.history[-1]
    target.write_text(json.dumps({'history_count': len(space.history),
        'tail_type': tail.type, 'tail_body_empty': tail.body == '',
        'tail_body_sha256': hashlib.sha256(tail.body.encode('utf-8')).hexdigest(),
        'tail_cursor': tail.current_character, 'scrollback_count': len(space.scrollback),
        'history_pointers': [line.as_pointer() for line in list(space.history)[-3:]],
        'scrollback_tail_types': [line.type for line in list(space.scrollback)[-3:]],
        'scene_operations': False}, indent=2), encoding='utf-8')
    return None

bpy.app.timers.register(observe, first_interval=0.25)
