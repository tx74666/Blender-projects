from pathlib import Path
import hashlib, json, re, subprocess, sys
evidence = Path(__file__).resolve().parent
repo = Path(r'D:\MyRepository\Blender-addons-by-Randy')
manifest = json.loads((evidence/'release_projection_07724.json').read_text())
for name, expected in manifest['source_provenance']['canonical_overlays'].items():
    assert hashlib.sha256((repo/'addons/character_designer'/name).read_bytes()).hexdigest() == expected
patterns = ['test_unity_animation_dress.py', 'test_control_source_rest_view.py',
            'test_unity_animation_bake_runtime_guard.py', 'test_limb_ik_worklist_users.py',
            'test_unity_animation_controls_rest_view.py', 'test_animation_worklist_target.py',
            'test_animation_worklist.py', 'test_animation_worklist_collection.py',
            'test_animation_worklist_ui.py']
rows = []
for pattern in patterns:
    run = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern],
                         cwd=repo, capture_output=True, text=True)
    output = run.stdout + run.stderr
    count = re.search(r'Ran (\d+) tests?', output)
    rows.append({'pattern': pattern, 'exit_code': run.returncode, 'tests': int(count.group(1)) if count else 0,
                 'output': output})
report = {'passed': all(row['exit_code'] == 0 and row['tests'] > 0 for row in rows),
          'total_tests': sum(row['tests'] for row in rows),
          'projection_sha256': hashlib.sha256((evidence/'release_projection_07724.json').read_bytes()).hexdigest(),
          'canonical_overlay_hashes_match': True, 'suites': rows}
(evidence/'pure_test_receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({key: report[key] for key in ('passed','total_tests','canonical_overlay_hashes_match')}))
if not report['passed']: raise SystemExit(1)
