"""Check 0.77.14 disk delivery without importing Blender or invoking Unity.

The only write is delivery_07714.json beside this script. A PASS means the
specified disk payload, hashes and asset identities match. It does not prove
loaded add-on version, automatic import drain, generated names, live scenes,
Animator state, or Play Mode. Those need Character's native receipts.
"""

from datetime import datetime, timezone
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent
UNITY = Path("D:/Unity Projects/RandomRealm2")
MANIFEST = ROOT / "import_queue_07714_runtime/release_projection_07714.json"
MANIFEST_SHA = "17a62f31b1b7c71ced1add9aae18465363420a63942f777b9f51422af851b6eb"
BASE_MANIFEST = ROOT / "forearm_roll_07712_runtime/release_projection_07712.json"
BASE_MANIFEST_SHA = "2c6e63bfe3919a2ed224da69aede0456315fcde35c49db187fcdf5872b8e34a6"
FROZEN = ROOT / "import_queue_07714_runtime/character_designer"
TARGETS = {
    "blender_5_2": Path(
        "C:/Users/Randy/AppData/Roaming/Blender Foundation/Blender/5.2/scripts/addons/character_designer"
    ),
    "x_project": PROJECT / "addons/character_designer",
}
IMPORTER_REL = "unity_runtime/Editor/ForearmCorrectionImporter.cs"
IMPORTER_SHA = "906fa8c3f9a21e2321cc0fa15d1701091b3b3176dd4a249ffdb8e24be017364d"
UNITY_IMPORTER = UNITY / "Assets/CharacterDesigner/Editor/ForearmCorrectionImporter.cs"
BUNDLE_RECEIPT = ROOT / "unity_bundle_disk_check_20261010.json"
BUNDLE_RECEIPT_SHA = "8cb6f728530a701bf2a95c44205860f2e0e812bea5ef10b1b54c1958f1cdd785"
PUBLISHED = ROOT / "published_export_07712"
UNITY_BUNDLE = UNITY / "Assets/Art/Character/Cosha"
FBX_SHA = "0e88a931b3943aef7ae1b59e12b1340479afc71dcd47c690e88cb574c3a9342c"
PROTECTED = {
    "artist_blend": (
        PROJECT / "X.blend",
        "17a9312f6ec7f3ec0d709ca89fb2bc918aa94856af0fef544c3ce6ca83bded86",
    ),
    "adventure_scene_disk": (
        UNITY / "Assets/Scenes/Main/Adventure.unity",
        "b301696228b50e7e2838749a29bfd3b3599db59531489b702eea3ada0477715e",
    ),
}
IDENTITIES = {
    "production_avatar": (
        UNITY / "Assets/Prefabs/Characters/Cosha/Cosha.Avatar.asset",
        "874ce658cb6c4b54a8203998231760cd",
    ),
    "runtime": (
        UNITY / "Assets/Art/Character/Cosha/Cosha.Runtime.prefab",
        "e28dbe21db8321b4e83d7852fb995ccf",
    ),
    "setup": (
        UNITY / "Assets/Prefabs/Characters/Cosha/Cosha.Setup.asset",
        "8c0e5e8769cb2b1478cf7114ae52edf6",
    ),
    "player": (
        UNITY / "Assets/Prefabs/Characters/Cosha/Cosha.Player.prefab",
        "3207a6768cff4594fb4b180b85f70a37",
    ),
    "fbx": (
        UNITY_BUNDLE / "Cosha.fbx",
        "d4f6e98918e246f418652325947d97f3",
    ),
}
SHA_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REPORT = ROOT / "delivery_07714.json"


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_check(path, expected):
    result = {"path": str(path), "expected_sha256": expected, "matches": False}
    try:
        result.update(actual_sha256=hash_file(path), bytes=path.stat().st_size)
        result["matches"] = result["actual_sha256"] == expected
    except OSError as error:
        result["error"] = str(error)
    return result


def locked_json(path, expected, report, key):
    check = hash_check(path, expected)
    report["input_locks"][key] = check
    if not check["matches"]:
        raise ValueError(f"Locked input differs or is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def safe_relative(name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError(f"Invalid projection path: {name!r}")
    value = PurePosixPath(name)
    if (
        value.is_absolute()
        or value.as_posix() != name
        or any(part in {"", ".", "..", "__pycache__"} or part.startswith(".") for part in value.parts)
        or value.suffix in {".pyc", ".pyo"}
    ):
        raise ValueError(f"Invalid projection path: {name!r}")
    return Path(*value.parts)


def file_table(manifest, version):
    if (
        manifest.get("schema_version") != 1
        or manifest.get("module") != "character_designer"
        or manifest.get("version") != version
        or not isinstance(manifest.get("files"), dict)
        or len(manifest["files"]) != 152
    ):
        raise ValueError(f"Unexpected {version} projection schema or file count")
    for name, digest in manifest["files"].items():
        safe_relative(name)
        if not isinstance(digest, str) or not SHA_PATTERN.fullmatch(digest):
            raise ValueError(f"Invalid projection digest: {name}")
    return manifest["files"]


def is_reparse(path):
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def inventory(folder):
    """Use official release_projection.shipped_files exclusions, without imports."""
    found = set()
    if not folder.is_dir():
        raise FileNotFoundError(f"Missing payload directory: {folder}")
    if is_reparse(folder):
        raise ValueError(f"Payload directory is a reparse point: {folder}")
    for parent, directories, files in os.walk(folder, followlinks=False):
        current = Path(parent)
        for name in (*directories, *files):
            if is_reparse(current / name):
                raise ValueError(f"Payload contains a reparse point: {current / name}")
        directories[:] = [name for name in directories if not name.startswith(".") and name != "__pycache__"]
        for name in files:
            path = current / name
            if name.startswith(".") or path.suffix in {".pyc", ".pyo"}:
                continue
            found.add(path.relative_to(folder).as_posix())
    return found


def version_on_disk(path):
    tree = ast.parse(path.read_bytes(), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "bl_info" for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            return ".".join(str(part) for part in value["version"])
    raise ValueError(f"Missing bl_info version: {path}")


def payload_check(folder, expected):
    rows = {}
    result = {"path": str(folder), "expected_count": len(expected), "files": rows, "passed": False}
    try:
        actual_names = inventory(folder)
        result.update(
            actual_count=len(actual_names),
            missing=sorted(set(expected) - actual_names),
            extra=sorted(actual_names - set(expected)),
        )
        for name, digest in sorted(expected.items()):
            rows[name] = hash_check(folder / safe_relative(name), digest)
        result["version_on_disk"] = version_on_disk(folder / "__init__.py")
        result["difference_count"] = len(result["extra"]) + sum(not row["matches"] for row in rows.values())
        result["passed"] = (
            not result["missing"]
            and not result["extra"]
            and all(row["matches"] for row in rows.values())
            and result["version_on_disk"] == "0.77.14"
        )
    except (OSError, ValueError, SyntaxError) as error:
        result["error"] = str(error)
    return result


def identity_check(asset, expected):
    meta = asset.with_name(asset.name + ".meta")
    row = {"asset_path": str(asset), "meta_path": str(meta), "expected_guid": expected, "matches": False}
    try:
        values = re.findall(r"^guid:\s*([0-9a-f]{32})\s*$", meta.read_text(encoding="utf-8-sig"), re.MULTILINE)
        row.update(asset_exists=asset.is_file(), observed_guids=values, meta_sha256=hash_file(meta))
        if asset.is_file():
            row["asset_sha256"] = hash_file(asset)
        row["matches"] = row["asset_exists"] and values == [expected]
    except OSError as error:
        row["error"] = str(error)
    return row


def verify(report):
    manifest = locked_json(MANIFEST, MANIFEST_SHA, report, "release_projection_07714")
    baseline = locked_json(BASE_MANIFEST, BASE_MANIFEST_SHA, report, "release_projection_07712")
    bundle_receipt = locked_json(BUNDLE_RECEIPT, BUNDLE_RECEIPT_SHA, report, "prior_bundle_disk_receipt")
    files = file_table(manifest, "0.77.14")
    base_files = file_table(baseline, "0.77.12")
    changed = sorted(name for name in set(files) | set(base_files) if files.get(name) != base_files.get(name))
    version_marker = b'"version": (0, 77, 12)'
    base_init = (ROOT / "forearm_roll_07712_runtime/character_designer/__init__.py").read_bytes()
    frozen_init = (FROZEN / "__init__.py").read_bytes()
    report["projection_delta"] = {
        "baseline_version": "0.77.12",
        "target_version": "0.77.14",
        "changed_files": changed,
        "same_file_inventory": set(files) == set(base_files),
        "only_approved_two_files_changed": changed == ["__init__.py", IMPORTER_REL],
        "frozen_source_root_matches": Path(manifest["source_root"]).resolve() == FROZEN.resolve(),
        "baseline_init_hash_matches": hashlib.sha256(base_init).hexdigest() == base_files["__init__.py"],
        "init_change_is_version_only": version_marker in base_init and base_init.count(version_marker) == 1
        and frozen_init == base_init.replace(version_marker, b'"version": (0, 77, 14)', 1),
        "frozen_importer_is_reviewed_hash": files[IMPORTER_REL] == IMPORTER_SHA,
    }
    report["frozen_payload"] = payload_check(FROZEN, files)
    report["installed_payloads"] = {name: payload_check(path, files) for name, path in TARGETS.items()}
    report["unity_importer"] = hash_check(UNITY_IMPORTER, IMPORTER_SHA)
    receipt_rows = bundle_receipt.get("files", [])
    expected_bundle = {row["name"]: row["expected"] for row in receipt_rows}
    expected_names = {
        "Cosha.fbx", "Cosha.cdesigner.json", "Cosha.forearm.json", "Cosha.hair-motion.json",
        "Textures/1d63a26f-110a-4ff2-9145-a350633c3dd5_eb4ef512.png", "Textures/Hair_d06dd5ee.png",
    }
    if len(receipt_rows) != 6 or set(expected_bundle) != expected_names or expected_bundle["Cosha.fbx"] != FBX_SHA:
        raise ValueError("Unexpected six-file export receipt")
    bundle_rows = []
    for name, digest in sorted(expected_bundle.items()):
        relative = safe_relative(name)
        source = hash_check(PUBLISHED / relative, digest)
        target = hash_check(UNITY_BUNDLE / relative, digest)
        bundle_rows.append({"name": name, "published": source, "unity": target, "matches": source["matches"] and target["matches"]})
    published_inventory = inventory(PUBLISHED)
    report["export_bundle"] = {
        "published_root": str(PUBLISHED), "unity_root": str(UNITY_BUNDLE), "expected_count": 6,
        "published_inventory_matches": published_inventory == expected_names,
        "published_missing": sorted(expected_names - published_inventory),
        "published_extra": sorted(published_inventory - expected_names),
        "files": bundle_rows,
        "passed": published_inventory == expected_names and all(row["matches"] for row in bundle_rows),
    }
    report["protected_disk_files"] = {name: hash_check(path, digest) for name, (path, digest) in PROTECTED.items()}
    report["production_asset_identities"] = {name: identity_check(path, guid) for name, (path, guid) in IDENTITIES.items()}
    delta = report["projection_delta"]
    report["checks"] = {
        "locked_inputs": all(row["matches"] for row in report["input_locks"].values()),
        "approved_two_file_delta": all(delta[key] for key in (
            "same_file_inventory", "only_approved_two_files_changed", "frozen_source_root_matches",
            "baseline_init_hash_matches", "init_change_is_version_only", "frozen_importer_is_reviewed_hash",
        )),
        "frozen_152_files": report["frozen_payload"]["passed"],
        "both_installed_152_file_payloads": all(row["passed"] for row in report["installed_payloads"].values()),
        "unity_importer_reviewed_hash": report["unity_importer"]["matches"],
        "published_six_file_bundle_equals_unity": report["export_bundle"]["passed"],
        "artist_and_adventure_disk_protected": all(row["matches"] for row in report["protected_disk_files"].values()),
        "five_production_guids_retained": all(row["matches"] for row in report["production_asset_identities"].values()),
    }
    report["passed"] = all(report["checks"].values())


def main():
    report = {
        "schema_version": 1,
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "version": "0.77.14",
        "scope": "Read-only disk delivery and protected-file/asset-identity verification",
        "method": "Streaming SHA-256, locked JSON manifests, shipped-file inventory, static bl_info AST and .meta GUID reads",
        "script": {"path": str(Path(__file__).resolve()), "sha256": hash_file(Path(__file__))},
        "input_locks": {},
        "passed": False,
        "unity_invoked": False,
        "blender_invoked": False,
        "assets_written": False,
        "canonical_sources_written": False,
        "loaded_addon_version_verified": False,
        "live_scene_or_play_verified": False,
        "native_import_drain_or_generated_names_verified": False,
        "native_acceptance": "Not evaluated by this script. Consult Character's native automatic-drain/name/GUID receipts.",
        "only_write": str(REPORT),
        "limits": [
            "Disk .blend and .unity hashes do not describe unsaved contents or prove live scene/Play preservation.",
            "Installed version is read from disk; the already-open Blender session may still have another loaded version.",
            "GUID checks prove disk asset identities, not loaded references, Avatar retargeting or correction execution.",
            "PASS is disk scope only; it does not replace native Unity acceptance or Blender saved-state verification.",
        ],
    }
    try:
        verify(report)
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    report["status"] = "PASS" if report["passed"] else "FAIL"
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "scope": report["scope"], "report": str(REPORT), "checks": report.get("checks"), "error": report.get("error")}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
