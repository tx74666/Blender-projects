"""Freeze the reviewed 0.77.13 input; no Unity, Blender, or installed-copy writes."""
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REPO = Path("D:/MyRepository/Blender-addons-by-Randy")
sys.path.insert(0, str(REPO / "tools"))
from release_projection import load_source

BASE_MANIFEST = ROOT / "forearm_roll_07712_runtime/release_projection_07712.json"
BASE_SHA = "2c6e63bfe3919a2ed224da69aede0456315fcde35c49db187fcdf5872b8e34a6"
IMPORTER = Path("unity_runtime/Editor/ForearmCorrectionImporter.cs")
IMPORTER_SHA = "cde8a96d8b5fc191915f1eef58f1cb8349c4ba8ac769e7147737a005f7c8d719"
DEST = ROOT / "import_queue_07713_runtime/character_designer"
MANIFEST = DEST.parent / "release_projection_07713.json"


def sha(content):
    return hashlib.sha256(content).hexdigest()


if sha(BASE_MANIFEST.read_bytes()) != BASE_SHA:
    raise AssertionError("Approved baseline manifest changed")
base = load_source("character_designer", BASE_MANIFEST, root=REPO)
if base.version != "0.77.12" or len(base.files) != 152 or DEST.exists() or MANIFEST.exists():
    raise AssertionError("Wrong baseline or an existing candidate would be overwritten")
payload = dict(base.files)
source = REPO / "addons/character_designer" / IMPORTER
importer = source.read_bytes()
if sha(importer) != IMPORTER_SHA:
    raise AssertionError("Reviewed importer changed")
payload[IMPORTER] = importer
old_version = b'"version": (0, 77, 12)'
new_version = b'"version": (0, 77, 13)'
if payload[Path("__init__.py")].count(old_version) != 1:
    raise AssertionError("Expected one baseline version declaration")
payload[Path("__init__.py")] = payload[Path("__init__.py")].replace(old_version, new_version, 1)
changes = sorted(path.as_posix() for path in payload if payload[path] != base.files[path])
if changes != ["__init__.py", IMPORTER.as_posix()]:
    raise AssertionError("Unapproved package change")
for path, content in payload.items():
    if path.suffix == ".py":
        ast.parse(content, filename=str(path))
    target = DEST / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
manifest = {
    "schema_version": 1, "module": "character_designer", "version": "0.77.13",
    "source_root": str(DEST),
    "files": {path.as_posix(): sha(payload[path]) for path in sorted(payload)},
    "source_provenance": {
        "baseline_manifest": str(BASE_MANIFEST), "baseline_sha256": BASE_SHA,
        "canonical_importer": str(source), "canonical_importer_sha256": IMPORTER_SHA,
        "changed_files": changes,
        "scope": "Forearm pending import survives assembly reload, bounded retry, generated data main-object name.",
        "guards": str(ROOT / "unity_queue_patch_contract_20261010.json"),
        "unity_writer": "RandomRealm2 Character; native acceptance required before deployment.",
    },
}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
verified = load_source("character_designer", MANIFEST, root=REPO)
receipt = {
    "prepared": True, "version": verified.version, "files": len(verified.files),
    "manifest": str(MANIFEST), "manifest_sha256": verified.projection_sha256,
    "changed_files": changes, "python_ast_files": sum(path.suffix == ".py" for path in payload),
    "installed_copies_written": False, "unity_assets_written": False,
}
(DEST.parent / "preparation_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt))
