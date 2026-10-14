"""Freeze the colon-path-only Source successor and verify an official local ZIP."""
import argparse
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

REPO = Path(r"D:\MyRepository\Blender-addons-by-Randy")
ROUND = Path(__file__).resolve().parent
ROOT = ROUND.parent
OLD_PACKAGE = ROUND / "package_8a5f5018"
OLD_FREEZE = ROOT / "x_rigging_source_freeze_r3_b459668d.json"
FREEZE = ROOT / "x_rigging_source_freeze_r4_bff52cbe.json"
CONTRACT_RECEIPT = ROUND / "transform_colon_contract_source_receipt.json"
OLD_FREEZE_SHA = "c30d8b46c3d60723d64393740324f7c27dbcbf633c489c25c90cdae65e67ad6e"
OLD_MANIFEST_SHA = "eab6da890fe8a57cbca61d130e70faf552e678bc734900c41e87ba62fb41caf2"
OLD_ZIP_SHA = "42ee4dbe4df41875a6923e4ce73e7883374b4ac39a94a84b28b70f7e75bdbaf5"
REPAIR_RECEIPT_SHA = "fb0e118d5ec9f0b3c459c85b7ed7f08f34885d87e8e7aa3c565b8f7b34637a6f"
INIT_SHA = "d66a88023e93c3db64f1b64cfaf8089d4c956adc0f97896c591e34a54d8e4dd2"
CHANGED = {
    "animation_rigging_contract.py": ("bff52cbe97530662fcee5e4ca248c1fe09e781f73588627cecda62c777d3c179", 23545),
    "test_animation_rigging_contract.py": ("5823df371bfa47f44d46e55426b7cabb5525ac6e96e1e2724842455fac8d69ad", 30589),
}
ARCHIVED_DIST = REPO / "dist/archived_candidates/character_designer-0.77.25-source-8a5f5018-42ee4dbe.zip"
sys.path.insert(0, str(REPO / "tools"))
from release_projection import load_source


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")


def record(path, checksum=None):
    path = Path(path).resolve()
    content = path.read_bytes()
    require(checksum is None or sha(content) == checksum, "Changed required Source pin: " + str(path))
    return {"path": str(path), "sha256": sha(content), "bytes": len(content)}


def file_map(source):
    return {relative.as_posix(): sha(data) for relative, data in sorted(source.files.items())}


def map_sha(files):
    return sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def write_new(path, content):
    path = path.resolve()
    require(path == FREEZE.resolve() or path.is_relative_to(ROUND), "New artifact leaves the authorized Source scope.")
    require(not path.exists(), "Refuse to overwrite a frozen artifact: " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)


def inputs():
    old_freeze_pin = record(OLD_FREEZE, OLD_FREEZE_SHA)
    old_manifest_pin = record(OLD_PACKAGE / "python_projection.json", OLD_MANIFEST_SHA)
    old_zip_pin = record(OLD_PACKAGE / "character_designer-0.77.25.zip", OLD_ZIP_SHA)
    repair_pin = record(CONTRACT_RECEIPT, REPAIR_RECEIPT_SHA)
    old = json.loads(OLD_FREEZE.read_bytes())
    repair = json.loads(CONTRACT_RECEIPT.read_bytes())
    require(old["schema"] == "cdesigner.x-rigging-source-freeze/1" and len(old["source_pins"]) == 15,
            "The original fifteen-source receipt changed.")
    require(repair["schema"] == "x.validation.transform-colon-contract-source/1"
            and repair["pure_tests"]["tests"] == 32 and repair["pure_tests"]["result"] == "PASS"
            and len(repair["actual_qa923_packets"]) == 4
            and all(row["result"] == "PASS" for row in repair["actual_qa923_packets"]), "Repair Source evidence is incomplete.")
    record(repair["pure_tests"]["log"]["path"], repair["pure_tests"]["log"]["sha256"])
    updated = []
    for pin in old["source_pins"]:
        path = Path(pin["path"])
        actual = record(path)
        expected_sha, expected_bytes = CHANGED.get(path.name, (pin["sha256"], pin["bytes"]))
        require(actual["sha256"] == expected_sha and actual["bytes"] == expected_bytes, "Unauthorized fifteen-source change: " + str(path))
        tree = ast.parse(path.read_bytes(), filename=str(path))
        compile(tree, str(path), "exec")
        updated.append({**actual, "syntax": "PASS"})
    require({Path(row["path"]).name for row in updated if row["sha256"] !=
            next(x["sha256"] for x in old["source_pins"] if x["path"] == row["path"])} == set(CHANGED), "Expected only two Source/test replacements.")
    for row in repair["source_files"].values():
        actual = record(row["path"], row["sha256"])
        require(actual == row, "Repair receipt Source pin is not exact.")
    old_source = load_source("character_designer", OLD_PACKAGE / "python_projection.json", root=REPO)
    captured = load_source("character_designer", root=REPO)
    old_hashes, hashes = file_map(old_source), file_map(captured)
    require(captured.version == old_source.version == "0.77.25" and len(hashes) == 187
            and set(hashes) == set(old_hashes) and hashes["__init__.py"] == INIT_SHA, "Version, init or complete shipped file set changed.")
    require([name for name in hashes if hashes[name] != old_hashes[name]] == ["animation_rigging_contract.py"]
            and hashes["animation_rigging_contract.py"] == CHANGED["animation_rigging_contract.py"][0], "Runtime delta exceeds the one approved contract leaf.")
    python_count = 0
    for relative, data in captured.files.items():
        if relative.suffix == ".py":
            compile(ast.parse(data, filename=relative.as_posix()), relative.as_posix(), "exec")
            python_count += 1
    require(python_count == 155, "Expected the complete 155-Python package.")
    return old, repair, updated, captured, hashes, python_count, {
        "old_source_freeze": old_freeze_pin, "old_manifest": old_manifest_pin,
        "old_frozen_archive": old_zip_pin, "contract_fix_receipt": repair_pin,
        "producer": record(__file__), "official_resolver": record(REPO / "tools/release_projection.py"),
        "official_builder": record(REPO / "tools/build_releases.py")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--verify-archive", action="store_true")
    args = parser.parse_args()
    old, repair, updated, captured, hashes, python_count, provenance = inputs()
    package = ROUND / ("package_" + map_sha(hashes)[:8])
    source_root, manifest_path = package / "source/character_designer", package / "python_projection.json"
    if args.capture:
        require(not FREEZE.exists() and not package.exists(), "Use fresh r4 freeze/package targets.")
        frozen = deepcopy(old)
        frozen.update(created_utc=datetime.now(timezone.utc).isoformat(), source_only=True,
            native_execution_performed=False, source_pins=updated, pure_tests_total=222,
            previous_source_freeze=provenance["old_source_freeze"], contract_fix_source_receipt=provenance["contract_fix_receipt"],
            source_delta={"source_pins_changed": sorted(CHANGED), "source_pins_unchanged": 13,
                          "runtime_payload_changed": ["animation_rigging_contract.py"], "other_186_runtime_files_unchanged": True},
            syntax_compilation={"fifteen_source_files": 15, "result": "PASS", "target_imports_executed": False},
            contract_actual_packet_validation=repair["actual_qa923_packets"],
            root_additional_recheck={"tests": 21, "result": "PASS", "seconds": 0.601,
                "files": ["test_animation_rigging_export.py", "test_animation_rigging_weapon.py"],
                "evidence": "Root reported actual tool stdout in this task; no durable raw log was saved.",
                "raw_log": None, "unique_tests_added": 0, "executed_by_this_producer": False})
        for row in frozen["pure_tests"]:
            if row["file"] == "test_animation_rigging_contract.py":
                row.update(tests=32, provenance=provenance["contract_fix_receipt"], executions_by_this_producer=0,
                           evidence_scope="current bff52 contract: 27 existing plus 5 new tests; actual four packets PASS")
            else:
                row.update(provenance=provenance["old_source_freeze"], executions_by_this_producer=0,
                           evidence_scope="Historical exact unchanged Source tests; not rerun by this producer")
        frozen["wire"]["evidence_scope"] = "Historical R3 illustrative validation; not rerun by r4 producer."
        frozen["limitations"] = frozen["limitations"] + [
            "R4 changes only legal Transform-colon path admission; no protocol fields or version change.",
            "Soldier literal-root mapping remains a separately recorded native-pending boundary."]
        require(sum(row["tests"] for row in frozen["pure_tests"]) == 222, "Unique test count is not 217+5.")
        require(file_map(load_source("character_designer", root=REPO)) == hashes, "Canonical drift before exclusive writes.")
        for row in updated:
            require(record(row["path"]) == {key: row[key] for key in ("path", "sha256", "bytes")}, "Fifteen-source drift before write.")
        write_new(FREEZE, encoded(frozen))
        package.mkdir()
        for relative, data in captured.files.items():
            write_new(source_root / relative, data)
        manifest = {"schema_version": 1, "module": "character_designer", "version": captured.version,
            "source_root": str(source_root), "source_provenance": {
                "purpose": "Source-only r4 legal Transform-colon candidate; native acceptance pending",
                "date": "2026-10-12", "fifteen_source_receipt": record(FREEZE),
                "previous_frozen_candidate": provenance["old_manifest"], "contract_fix_source_receipt": provenance["contract_fix_receipt"],
                "complete_file_map_sha256": map_sha(hashes), "init_registration_sha256": INIT_SHA,
                "runtime_payload_delta": ["animation_rigging_contract.py"], "other_runtime_files_unchanged": 186,
                "producer": provenance["producer"], "native_acceptance": False,
                "deployment_authorized_by_this_manifest": False}, "files": hashes}
        write_new(manifest_path, encoded(manifest))
        verified = load_source("character_designer", manifest_path, root=REPO)
        require(verified.files == captured.files, "Frozen payload differs from the admitted snapshot.")
        print(json.dumps({"freeze": record(FREEZE), "manifest": record(manifest_path),
            "source_root": str(source_root), "complete_file_map_sha256": map_sha(hashes),
            "file_count": 187, "source_bytes": sum(map(len, captured.files.values())),
            "python_files": python_count, "source_only": True, "native_acceptance": False}))
        return
    freeze = json.loads(FREEZE.read_bytes())
    require(freeze["source_pins"] == updated and freeze["pure_tests_total"] == 222
            and freeze["contract_fix_source_receipt"] == provenance["contract_fix_receipt"], "Current r4 Source receipt differs.")
    verified = load_source("character_designer", manifest_path, root=REPO)
    require(verified.files == captured.files, "Canonical/projection drift before ZIP readback.")
    relocated = record(ARCHIVED_DIST, OLD_ZIP_SHA)
    require(Path(relocated["path"]).read_bytes() == (OLD_PACKAGE / "character_designer-0.77.25.zip").read_bytes(), "Archived dist differs from original immutable ZIP.")
    archive = REPO / "dist/character_designer-0.77.25.zip"
    payload = {"character_designer/" + relative.as_posix(): data for relative, data in verified.files.items()}
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        require(zipped.testzip() is None and len(entries) == 187
                and len({entry.filename for entry in entries}) == 187
                and not any(entry.is_dir() for entry in entries), "ZIP CRC, duplicate or complete-entry count failure.")
        require({entry.filename: zipped.read(entry) for entry in entries} == payload, "Official ZIP differs from every manifested byte.")
    frozen_archive = package / archive.name
    write_new(frozen_archive, archive.read_bytes())
    receipt = {"schema": "cdesigner.unified-source-candidate/1", "status": "SOURCE_FROZEN_NATIVE_PENDING",
        "source_only": True, "native_execution_performed": False, "native_acceptance": False,
        "version": verified.version, "manifest": record(manifest_path), "source_root": str(source_root),
        "file_count": 187, "source_bytes": sum(map(len, verified.files.values())),
        "complete_file_map_sha256": map_sha(hashes), "fifteen_source_receipt": record(FREEZE),
        "syntax_compilation": {"python_files": 155, "fifteen_source_files": 15, "result": "PASS", "target_imports_executed": False},
        "key_source_pins": {name: hashes[name] for name in hashes if name in
            ("__init__.py", "unity_animation_rigging.py", "animation_rigging_contract.py") or name.endswith(".cs")},
        "unique_pure_tests": 222, "tests_executed_by_this_producer": 0,
        "prior_tests": {"old_freeze": provenance["old_source_freeze"], "contract32_current": provenance["contract_fix_receipt"],
            "root21_recheck": freeze["root_additional_recheck"]},
        "old_candidate_provenance": provenance,
        "old_dist_relocation": {"original_path": str(archive), "archived": relocated,
            "immutable_old_frozen_copy": provenance["old_frozen_archive"], "old_bytes_equal": True,
            "operation": "Normal Move-Item after verified resolved dist containment; no overwrite/delete of old ZIP."},
        "archive": {"dist": record(archive), "frozen_copy": record(frozen_archive), "exact_187_payload": "PASS",
            "testzip": "PASS", "duplicate_entries": 0},
        "official_build": {"command": [str(REPO / "tools/build_releases.py"), "--module", "character_designer",
            "--projection", str(manifest_path)], "exit_code": 0, "performed": True, "local_candidate_only": True},
        "boundaries": {"deployments": 0, "blender_native_calls": 0, "sdk_calls": 0, "gui_calls": 0,
            "export_workers": 0, "artist_writes": 0, "git_publish_operations": 0, "version_changes": 0},
        "limitations": ["Pure/syntax/package validation only; no native/solver/physical worker/Unity Apply acceptance.",
            "Fresh typed Link, real WorkID and model must still come from actual Prepare.",
            "Old 8a candidate, source freeze, complete Source payload and ZIP remain immutable."]}
    write_new(package / "unified_package_receipt.json", encoded(receipt))
    print(json.dumps({"receipt": record(package / "unified_package_receipt.json"), "freeze": record(FREEZE),
        "manifest": record(manifest_path), "new_dist": record(archive), "frozen_archive": record(frozen_archive),
        "relocated_old_dist": relocated, "file_count": 187, "source_only": True, "native_acceptance": False}))


if __name__ == "__main__":
    main()
