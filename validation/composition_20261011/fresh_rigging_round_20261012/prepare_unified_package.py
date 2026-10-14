"""Freeze and verify the complete source-only candidate; never deploy it."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
import zipfile


REPO = Path(r"D:\MyRepository\Blender-addons-by-Randy")
ROUND = Path(__file__).resolve().parent
PACKAGE = ROUND / "package_8a5f5018"
SOURCE = PACKAGE / "source" / "character_designer"
MANIFEST = PACKAGE / "python_projection.json"
FREEZE = ROUND.parent / "x_rigging_source_freeze_r3_b459668d.json"
EXPECTED_MAP = "8a5f5018e03806fa9a762dbafc4e31224eb19b68f52447c386b872dd2c43cc97"
EXPECTED_INIT = "d66a88023e93c3db64f1b64cfaf8089d4c956adc0f97896c591e34a54d8e4dd2"
EXPECTED_FREEZE = "c30d8b46c3d60723d64393740324f7c27dbcbf633c489c25c90cdae65e67ad6e"

sys.path.insert(0, str(REPO / "tools"))
from release_projection import load_source


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def file_map(source):
    return {relative.as_posix(): sha(data) for relative, data in sorted(source.files.items())}


def map_sha(files):
    return sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def immutable_write(path, content):
    path = path.resolve()
    if not path.is_relative_to(ROUND):
        raise RuntimeError(f"Target outside isolated round: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise RuntimeError(f"Existing frozen artifact differs: {path}")
    else:
        with path.open("xb") as stream:
            stream.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-archive", action="store_true")
    args = parser.parse_args()
    freeze_bytes = FREEZE.read_bytes()
    assert sha(freeze_bytes) == EXPECTED_FREEZE, "Frozen fifteen-source receipt changed"
    frozen = json.loads(freeze_bytes)
    for pin in frozen["source_pins"]:
        data = Path(pin["path"]).read_bytes()
        assert len(data) == pin["bytes"] and sha(data) == pin["sha256"], pin["path"]

    captured = load_source("character_designer", root=REPO)
    hashes = file_map(captured)
    assert captured.version == "0.77.25", "Parent-owned version changed"
    assert len(hashes) == 187 and sum(map(len, captured.files.values())) == 5546635
    assert hashes["__init__.py"] == EXPECTED_INIT
    assert map_sha(hashes) == EXPECTED_MAP, "Complete canonical payload changed; coordinate a new freeze"
    python_files = 0
    for relative, data in captured.files.items():
        if relative.suffix == ".py":
            tree = ast.parse(data, filename=relative.as_posix())
            compile(tree, relative.as_posix(), "exec")
            python_files += 1
        immutable_write(SOURCE / relative, data)

    manifest = {
        "schema_version": 1,
        "module": "character_designer",
        "version": captured.version,
        "source_root": str(SOURCE.resolve()),
        "source_provenance": {
            "purpose": "Source-only unified candidate for fresh isolated native acceptance",
            "date": "2026-10-12",
            "canonical_repository": str(REPO),
            "fifteen_source_receipt": str(FREEZE),
            "fifteen_source_receipt_sha256": EXPECTED_FREEZE,
            "complete_file_map_sha256": EXPECTED_MAP,
            "init_registration_sha256": EXPECTED_INIT,
            "review_scope": "Fifteen pinned source/test files plus reviewed initialization hooks; entire shipped payload content frozen",
            "native_acceptance": False,
            "deployment_authorized_by_this_manifest": False,
        },
        "files": hashes,
    }
    immutable_write(MANIFEST, encoded(manifest))
    verified = load_source("character_designer", MANIFEST, root=REPO)
    assert verified.files == captured.files
    assert file_map(load_source("character_designer", root=REPO)) == hashes, "Canonical drift during capture"

    receipt = {
        "schema": "cdesigner.unified-source-candidate/1",
        "status": "SOURCE_FROZEN_NATIVE_PENDING",
        "version": verified.version,
        "manifest": str(MANIFEST),
        "manifest_sha256": sha(MANIFEST.read_bytes()),
        "source_root": str(SOURCE),
        "file_count": len(hashes),
        "source_bytes": sum(map(len, verified.files.values())),
        "complete_file_map_sha256": map_sha(hashes),
        "syntax_compilation": {"python_files": python_files, "result": "PASS", "imports_executed": False},
        "key_source_pins": {name: hashes[name] for name in (
            "__init__.py", "unity_animation_rigging.py", "animation_rigging_contract.py",
            "unity_runtime/Editor/CharacterAnimationRigging.cs")},
        "fifteen_source_receipt_sha256": EXPECTED_FREEZE,
        "previous_pure_tests": 217,
        "native_acceptance": False,
        "limitations": [
            "Full package is frozen and syntax checked; runtime loading and native UI behavior remain pending.",
            "Fresh typed Link, actual prepared WorkID and model association must come from Unity Prepare.",
            "No weaponPreview exists in current actual capture; this cannot prove gun display.",
            "No artist scene was changed or saved during this source-only phase.",
        ],
        "boundaries": {
            "deployment_operations": 0, "blender_sdk_calls": 0, "gui_calls": 0,
            "native_workers": 0, "artist_writes": 0, "git_publish_operations": 0,
        },
    }
    if args.verify_archive:
        archive = REPO / "dist" / "character_designer-0.77.25.zip"
        with zipfile.ZipFile(archive) as package:
            entries = package.infolist()
            assert package.testzip() is None
            assert len(entries) == len(hashes)
            expected = {"character_designer/" + relative.as_posix(): data for relative, data in verified.files.items()}
            actual = {entry.filename: package.read(entry) for entry in entries}
            assert actual == expected and len(actual) == len(entries), "Archive differs or contains duplicate entries"
        archive_bytes = archive.read_bytes()
        frozen_archive = PACKAGE / archive.name
        immutable_write(frozen_archive, archive_bytes)
        receipt["archive"] = {"path": str(archive), "frozen_copy": str(frozen_archive), "sha256": sha(archive_bytes), "bytes": len(archive_bytes), "exact_payload": "PASS"}
        immutable_write(PACKAGE / "unified_package_receipt.json", encoded(receipt))
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
