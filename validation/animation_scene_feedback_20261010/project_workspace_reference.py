"""Project only the readable-reference reader onto the verified 0.77.19 package.

No canonical, installed or baseline file is modified. Pure tests use this copy.
"""

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
from types import ModuleType
import unittest


HERE = Path(__file__).resolve().parent
REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
BASELINE = HERE / 'release_07719' / 'character_designer'
PROJECTED = HERE / 'reference_reader_projection' / 'character_designer'
CANONICAL = REPO / 'addons' / 'character_designer' / 'animation_workspace.py'
REPORT = HERE / 'reference_reader_projection.json'
FUNCTIONS = ('_decode_json', 'parse_workspace', '_uuid', '_parse_reference',
             '_read_bytes', '_load_reference', 'load_workspace')
DEPENDENCIES = ('AnimationWorkspaceError', '_text', '_hex', '_absolute_path',
                '_object', '_constant', '_float', '_validate')


def nodes(text):
    return {node.name: node for node in ast.parse(text).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


def segment(text, node):
    return ''.join(text.splitlines(keepends=True)[node.lineno - 1:node.end_lineno])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    baseline_path = BASELINE / 'animation_workspace.py'
    baseline = baseline_path.read_text(encoding='utf-8')
    source = CANONICAL.read_text(encoding='utf-8')
    old_nodes, new_nodes = nodes(baseline), nodes(source)
    for name in DEPENDENCIES:
        assert ast.dump(old_nodes[name], include_attributes=False) == ast.dump(new_nodes[name], include_attributes=False), name
    assert not set(FUNCTIONS) - {'parse_workspace', 'load_workspace'} & old_nodes.keys()
    lines = baseline.splitlines(keepends=True)
    start, end = old_nodes['parse_workspace'].lineno - 1, old_nodes['load_workspace'].end_lineno
    reader = '\n\n'.join(segment(source, new_nodes[name]).rstrip() for name in FUNCTIONS) + '\n'
    projected = ''.join(lines[:start]) + reader + ''.join(lines[end:])
    anchor = "MANIFEST_NAME = 'character_animation_workspace.json'\n"
    assert projected.count(anchor) == 1
    projected = projected.replace(anchor, anchor +
        "REFERENCE_SCHEMA = 'cdesigner.animation-workspace-reference/1'\nREFERENCE_SUFFIX = '.workspace.json'\n", 1)
    projected = projected.replace(
        'only this bounded index; selected-item operations own Link/packet validation.',
        'only the bounded index and, when chosen, its explicit readable reference;\nselected-item operations own Link/packet validation.', 1)
    assert ast.dump(ast.parse(projected), include_attributes=False) == ast.dump(ast.parse(source), include_attributes=False), 'Canonical has changes beyond this reader; review before packaging.'
    assert not PROJECTED.exists(), 'Use a fresh projection folder; baseline is never overwritten.'
    shutil.copytree(BASELINE, PROJECTED)
    (PROJECTED / 'animation_workspace.py').write_text(projected, encoding='utf-8')
    changed = [str(path.relative_to(BASELINE)) for path in BASELINE.rglob('*')
               if path.is_file() and digest(path) != digest(PROJECTED / path.relative_to(BASELINE))]
    assert changed == ['animation_workspace.py'], changed
    report = {'schema': 'cdesigner.workspace-reference-projection/1', 'baseline_package': str(BASELINE),
              'projected_package': str(PROJECTED), 'baseline_workspace_sha256': digest(baseline_path),
              'canonical_workspace_sha256': digest(CANONICAL),
              'projected_workspace_sha256': digest(PROJECTED / 'animation_workspace.py'),
              'constants': ['REFERENCE_SCHEMA', 'REFERENCE_SUFFIX'], 'functions': list(FUNCTIONS),
              'existing_baseline_dependencies': list(DEPENDENCIES), 'changed_package_files': changed, 'tests': []}
    failed = False
    for filename, root in (('test_animation_workspace.py', PROJECTED / 'animation_workspace.py'),
                           ('test_animation_worklist.py', PROJECTED)):
        path = REPO / 'tests' / filename
        text = path.read_text(encoding='utf-8')
        tree = ast.parse(text, filename=str(path))
        source_assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'SOURCE' for target in node.targets))
        source_assignment.value = ast.Call(func=ast.Name(id='Path', ctx=ast.Load()),
            args=[ast.Constant(str(root))], keywords=[])
        ast.fix_missing_locations(tree)
        module = ModuleType('projected_' + path.stem)
        module.__file__ = str(path)
        exec(compile(tree, str(path), 'exec'), module.__dict__)
        result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(module))
        report['tests'].append({'file': filename, 'count': result.testsRun, 'passed': result.wasSuccessful(),
                                'runtime_source': str(root)})
        failed |= not result.wasSuccessful()
    report['passed'] = not failed
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert not failed, 'Projected reader tests failed.'
    print('Workspace reference projection PASS:', REPORT)


if __name__ == '__main__':
    main()
