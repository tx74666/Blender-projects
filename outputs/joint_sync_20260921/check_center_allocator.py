"""Compare the runtime ordered allocator against exhaustive small cases."""
import ast, itertools, math, random
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
source = Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/finger_joint_plan.py')
node = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == '_allocate')
env = {'lru_cache': lru_cache, 'math': math, 'layout': SimpleNamespace(EPS=1e-6)}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), env)
rng = random.Random(6145)
for case in range(1000):
    size = rng.randrange(3, 11)
    ts = [i/(size-1) for i in range(size)]
    count = rng.randrange(1, min(size, 5))
    target = sorted(rng.sample([i/100 for i in range(1, 100)], count))
    protected = {i for i in range(1, size-1) if rng.random() < .3}
    choices = []
    for rows in itertools.combinations(range(1, size-1), count):
        final = list(ts)
        if any(i in protected and abs(ts[i]-t) >= 1e-6 for i, t in zip(rows, target)): continue
        for i, t in zip(rows, target): final[i] = t
        if any(b-a <= 1e-6 for a, b in zip(final, final[1:])): continue
        choices.append((sum(abs(ts[i]-t) for i, t in zip(rows, target)), rows))
    try:
        actual = env['_allocate'](ts, [{'t': t} for t in target], protected)
    except ValueError:
        assert not choices, (case, ts, target, protected, min(choices))
    else:
        assert choices, (case, actual)
        score = sum(abs(ts[i]-t) for i, t in zip(actual, target))
        assert abs(score-min(choices)[0]) < 1e-12, (case, actual, min(choices))
        assert any(rows == actual for _, rows in choices), (case, actual)
print('CENTER_ALLOCATION_EXHAUSTIVE_ORACLE_PASS 1000')
