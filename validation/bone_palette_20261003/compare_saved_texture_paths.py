"""Compare immutable before/after texture reports without opening Blender.

Require saved-X evidence, absolute existing Eye/Hair texture paths, and the
same resolved file for every image whose file existed in the baseline. By
default require the runtime clean flag. --saved-verification-report instead
requires a passing strict disk readback and matching immutable fingerprints;
the native dirty flags remain observations and are never changed or fabricated.
Pre-existing unresolved files are reported separately and do not become new
failures. This script reads reports/files and writes only optional comparison
JSON; it never changes a .blend, image, material, or add-on.
"""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys


def absolute_path(value):
    return (isinstance(value, str) and bool(value)
            and not value.startswith('//')
            and (Path(value).is_absolute() or PureWindowsPath(value).is_absolute()))


def same_file(left, right):
    left_path, right_path = Path(left), Path(right)
    try:
        return left_path.samefile(right_path)
    except OSError:
        return left_path.resolve() == right_path.resolve()


def image_index(report, label):
    images = report.get('images')
    if not isinstance(images, list) or not isinstance(report.get('materials'), dict):
        raise ValueError(f'{label} has invalid images/materials fields.')
    result = {}
    for image in images:
        if (not isinstance(image, dict) or not isinstance(image.get('name'), str)
                or not isinstance(image.get('path'), str)
                or not isinstance(image.get('absolute'), str)
                or not isinstance(image.get('exists'), bool)):
            raise ValueError(f'{label} contains an invalid image record.')
        if image['name'] in result:
            raise ValueError(f'{label} repeats image name {image["name"]!r}.')
        result[image['name']] = image
    return result


def critical_groups(before, images):
    groups = {'Eye': set(), 'Hair': set()}
    for name, image in images.items():
        text = (name + ' ' + PureWindowsPath(image['path']).name).casefold()
        for group in groups:
            if group.casefold() in text:
                groups[group].add(name)
    # The Eye image can have a UUID filename; its material identifies its role.
    for material, names in before['materials'].items():
        if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
            raise ValueError(f'Invalid image bindings for material {material!r}.')
        for group in groups:
            if group.casefold() in material.casefold():
                groups[group].update(names)
    return groups


def disk_fingerprint(path):
    path = Path(path).resolve()
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    after = path.stat()
    return {
        'path': str(path), 'bytes': after.st_size, 'mtime_ns': after.st_mtime_ns,
        'sha256': digest.hexdigest(),
        'stable_during_hash': (before.st_size, before.st_mtime_ns)
                              == (after.st_size, after.st_mtime_ns),
    }


def saved_disk_evidence(after, verification):
    errors = []
    evidence = {'readback_passed': verification.get('passed') is True,
                'readback_input': verification.get('artist_input')}
    if (verification.get('passed') is not True or verification.get('mode') != 'verify'
            or verification.get('errors') != []
            or verification.get('artist_input_unchanged') is not True
            or verification.get('source_hash_unchanged') is not True):
        errors.append('Saved-file evidence must be a passing, unchanged-input strict verify-mode readback.')
    if (not absolute_path(verification.get('artist_input'))
            or not same_file(verification['artist_input'], after['blend'])):
        errors.append('Strict saved-file readback and texture audit must verify the same actual-X file.')
    integrity = after.get('input_integrity')
    if (not isinstance(integrity, dict) or integrity.get('unchanged') is not True
            or not isinstance(integrity.get('before'), dict)
            or integrity.get('before') != integrity.get('after')
            or integrity['before'].get('stable_during_hash') is not True):
        errors.append('Saved-file evidence requires unchanged audit SHA/mtime/size fingerprints.')
        return evidence, errors
    audited = integrity['after']
    observed = disk_fingerprint(after['blend'])
    evidence.update(audit_input_fingerprint=audited, current_disk_fingerprint=observed)
    if (observed != audited or not observed['stable_during_hash']
            or not same_file(audited['path'], after['blend'])):
        errors.append('Current actual-X disk fingerprint differs from the immutable texture audit.')
    expected = audited.get('sha256', '').casefold()
    if (len(expected) != 64
            or verification.get('input_sha256_before', '').casefold() != expected
            or verification.get('input_sha256_after', '').casefold() != expected):
        errors.append('Strict saved-file readback SHA must match both audit and current disk SHA.')
    evidence['verified_saved_sha256'] = expected
    return evidence, errors


def compare_reports(before, after, saved_verification=None):
    old_images, new_images = image_index(before, 'Baseline'), image_index(after, 'Saved report')
    errors, preserved, critical = [], [], {}
    if (not absolute_path(after.get('blend')) or not Path(after['blend']).is_file()
            or not same_file(before['blend'], after['blend'])):
        errors.append('Saved report must come from the same actual-X .blend path as the baseline.')
    save_evidence = None
    if saved_verification is None:
        if after.get('is_dirty') is not False:
            errors.append('Saved report must confirm is_dirty=false after saving/reopening actual X.')
    else:
        # Blender 5.1's rna_Main_is_dirty_get reads !WindowManager.file_saved,
        # not a disk fingerprint; retain the background runtime observation.
        # No scene, pose, geometry, or file-identity check is relaxed here.
        if not isinstance(saved_verification, dict):
            errors.append('Invalid strict saved-file verification report.')
        else:
            save_evidence, evidence_errors = saved_disk_evidence(after, saved_verification)
            errors.extend(evidence_errors)
    if 'input_integrity' in after:
        integrity = after['input_integrity']
        if (not isinstance(integrity, dict) or integrity.get('unchanged') is not True
                or integrity.get('before') != integrity.get('after')):
            errors.append('Saved texture audit changed its input file hash/mtime or could not verify input stability.')
    for group, names in critical_groups(before, old_images).items():
        if not names:
            errors.append(f'Baseline does not identify any {group} textures.')
        critical[group] = sorted(names)
        for name in sorted(names):
            image = new_images.get(name)
            if image is None:
                errors.append(f'{group} texture {name!r} is missing from the saved report.')
                continue
            if not absolute_path(image['path']):
                errors.append(f'{group} texture {name!r} still has a relative stored path: {image["path"]!r}.')
            if not absolute_path(image['absolute']) or not Path(image['absolute']).is_file():
                errors.append(f'{group} texture {name!r} does not resolve to an existing absolute file.')
            elif absolute_path(image['path']) and not same_file(image['path'], image['absolute']):
                errors.append(f'{group} texture {name!r} stored/resolved paths refer to different files.')
            if image['exists'] is not True:
                errors.append(f'{group} texture {name!r} was unresolved in the saved Blender report.')
    for name, image in sorted(old_images.items()):
        if not image['exists']:
            continue
        current = new_images.get(name)
        if current is None:
            errors.append(f'Originally existing image {name!r} is missing after saving.')
            continue
        if (current['exists'] is not True or not absolute_path(current['absolute'])
                or not Path(current['absolute']).is_file()):
            errors.append(f'Originally existing image {name!r} no longer resolves to an existing file.')
        elif not same_file(image['absolute'], current['absolute']):
            errors.append(f'Image {name!r} changed file: {image["absolute"]!r} -> {current["absolute"]!r}.')
        else:
            preserved.append(name)
    # Path conversion must not change which image an existing material uses.
    for material, names in before['materials'].items():
        if sorted(after['materials'].get(material, [])) != sorted(names):
            errors.append(f'Material {material!r} changed its image bindings after saving.')
    return {
        'passed': not errors,
        'validation_basis': 'strict_saved_disk_readback' if saved_verification is not None
                            else 'runtime_clean_flag',
        'dirty_observations': {
            'initial_is_dirty': after.get('initial_is_dirty'),
            'reopened_is_dirty': after.get('reopened_is_dirty'),
            'capture_is_dirty': after.get('is_dirty'),
        },
        'saved_file_evidence': save_evidence,
        'baseline_blend': before.get('blend'), 'saved_blend': after.get('blend'),
        'critical_textures': critical,
        'originally_existing_images': sum(image['exists'] for image in old_images.values()),
        'same_file_preserved_count': len(preserved), 'same_file_preserved': preserved,
        'pre_existing_unresolved': sorted(name for name, image in old_images.items()
                                        if not image['exists']),
        'saved_unresolved_unpacked': sorted(name for name, image in new_images.items()
                                           if not image['exists'] and not image.get('packed', False)),
        'errors': errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--saved-verification-report', type=Path,
                        help='Passing strict saved-X readback proving the exact audited disk SHA.')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    before_path, after_path = args.before.resolve(), args.after.resolve()
    if before_path == after_path:
        parser.error('Before and after must be separate report files.')
    protected_reports = {before_path, after_path}
    if args.saved_verification_report:
        protected_reports.add(args.saved_verification_report.resolve())
    if args.output and args.output.resolve() in protected_reports:
        parser.error('Comparison output must not overwrite a texture or saved-verification report.')
    if args.output and args.output.exists():
        parser.error('Comparison output already exists; preserve it and choose a fresh filename.')
    try:
        before = json.loads(before_path.read_text(encoding='utf-8'))
        after = json.loads(after_path.read_text(encoding='utf-8'))
        verification = (json.loads(args.saved_verification_report.read_text(encoding='utf-8'))
                        if args.saved_verification_report else None)
        result = compare_reports(before, after, verification)
        result.update(baseline_report=str(before_path), saved_report=str(after_path))
        if args.saved_verification_report:
            result['saved_verification_report'] = str(args.saved_verification_report.resolve())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {'passed': False, 'errors': [f'{type(exc).__name__}: {exc}']}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(text + '\n')
    print(text)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
