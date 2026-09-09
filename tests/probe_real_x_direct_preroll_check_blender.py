"""Read-only Direct Pre-Roll feasibility report for the real X armature.

The probe opens the supplied Blend in a disposable background process, runs
only Analyze + Check Pre-Roll, verifies the input fingerprint, and never saves.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for root in (PROJECT_ROOT / "addons", PROJECT_ROOT / "tests"):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

import character_designer
from character_designer import limb_ik
import test_real_x_pole_direction_migration_blender as migration


SELECTIONS = {
    ("ARM", "L"): "LEFT_ARM",
    ("ARM", "R"): "RIGHT_ARM",
    ("LEG", "L"): "LEFT_LEG",
    ("LEG", "R"): "RIGHT_LEG",
}


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "sha256": digest.hexdigest().upper(),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) != 1:
        raise SystemExit("Expected exactly one X.blend path after --")
    path = Path(args[0]).resolve()
    disk_before = fingerprint(path)
    if bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False) != {"FINISHED"}:
        raise AssertionError(f"Could not open {path}")
    character_designer.register()
    armature = migration._find_real_armature()
    migration._mode_set(bpy.context, armature, "POSE")
    analyze = bpy.ops.character_designer.limb_ik_analyze()
    settings = bpy.context.window_manager.character_designer_limb_ik
    payload = json.loads(settings.analysis_json) if settings.analysis_json else {}
    results = {}
    for key, selection in SELECTIONS.items():
        kind, side = key
        detected = payload.get("limbs", {}).get(kind, {}).get(side, {})
        label = f"{kind}.{side}"
        if detected.get("status") not in {"READY", "WARNING"}:
            results[label] = {"detected": detected, "check": None}
            continue
        settings.selected_limb = selection
        setattr(
            settings,
            limb_ik._pole_direction_field(kind, side),
            limb_ik.DEFAULT_POLE_DIRECTIONS[key],
        )
        operator_result = bpy.ops.character_designer.limb_ik_direct_preroll_check()
        check_payload = json.loads(settings.direct_preroll_json) if settings.direct_preroll_json else {}
        results[label] = {
            "detected": detected,
            "operator_result": sorted(operator_result),
            "message": settings.last_message,
            "check": check_payload.get("result"),
        }
    disk_after = fingerprint(path)
    report = {
        "blender": bpy.app.version_string,
        "addon": list(character_designer.bl_info["version"]),
        "armature": armature.name,
        "analyze_result": sorted(analyze),
        "results": results,
        "blend_dirty_after_checks": bool(bpy.data.is_dirty),
        "disk_before": disk_before,
        "disk_after": disk_after,
        "disk_unchanged": disk_after == disk_before,
    }
    if not report["disk_unchanged"]:
        raise AssertionError(f"Input Blend changed: {disk_before} -> {disk_after}")
    print("REAL_X_DIRECT_PREROLL_JSON=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
    print("PASS read-only real-X Direct Pre-Roll check")


if __name__ == "__main__":
    main()
