import os
import sys
from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = Path(
    os.environ.get("CHARACTER_DESIGNER_ADDONS_ROOT", PROJECT_ROOT / "addons")
).resolve()
if str(ADDONS_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDONS_ROOT))

from character_designer import reference_views


def complete_manifest_path():
    explicit = os.environ.get("CHARACTER_DESIGNER_REFERENCE_MANIFEST", "").strip()
    candidates = (
        [Path(explicit).resolve()]
        if explicit
        else sorted((PROJECT_ROOT / "References" / "CDesigner").glob("**/reference-views.json"))
    )
    failures = []
    for candidate in candidates:
        try:
            manifest = reference_views.read_reference_view_manifest(str(candidate))
        except Exception as exc:
            failures.append(f"{candidate}: {exc}")
            continue
        if sum(view["configured"] for view in manifest["views"]) == 6:
            return candidate, manifest
    details = "\n".join(failures) if failures else "No manifests found."
    raise AssertionError(f"No complete six-view manifest is available.\n{details}")


def managed_views(scene, set_id):
    return {
        obj.get("cdesigner_reference_view"): obj
        for obj in scene.objects
        if obj.get("cdesigner_reference_set_id") == set_id
        and obj.get("cdesigner_reference_kind") == "VIEW"
    }


def main():
    manifest_path, manifest = complete_manifest_path()
    set_id = manifest["set_id"]
    expected_directions = set(reference_views.REFERENCE_VIEW_DIRECTIONS)

    first = reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
    views = managed_views(bpy.context.scene, set_id)
    if first["configured_views"] != 6 or first["enabled_views"] != 6:
        raise AssertionError(f"The complete manifest did not create six enabled views: {first}")
    if set(views) != expected_directions:
        raise AssertionError(f"Unexpected generated directions: {sorted(views)}")
    if any(
        obj.type != "EMPTY"
        or obj.empty_display_type != "IMAGE"
        or obj.data is None
        or not obj.hide_render
        for obj in views.values()
    ):
        raise AssertionError("Generated references are not safe non-rendering Image Empties")

    expected_distance = manifest["placement"]["distance_meters"]
    for direction, obj in views.items():
        if abs(obj.matrix_basis.translation.length - expected_distance) > 1.0e-5:
            raise AssertionError(f"{direction} is not placed at the manifest distance")

    second = reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
    if second["created_objects"] != 0 or second["updated_objects"] != 7:
        raise AssertionError(f"Second sync was not an idempotent in-place update: {second}")

    reference_views.set_reference_view_visibility(bpy.context.scene, set_id, False)
    if any(not obj.hide_viewport for obj in views.values()):
        raise AssertionError("Hide All left a managed reference visible")
    reference_views.set_reference_view_visibility(bpy.context.scene, set_id, True)
    if any(obj.hide_viewport for obj in views.values()):
        raise AssertionError("Show All left an enabled managed reference hidden")

    reference_views.clear_reference_view_set(bpy.context.scene, set_id)
    remaining = [
        obj.name
        for obj in bpy.context.scene.objects
        if obj.get("cdesigner_reference_set_id") == set_id
    ]
    if remaining:
        raise AssertionError(f"Safe clear left managed objects behind: {remaining}")

    print(
        "PASS real six-view manifest: "
        f"{manifest['set_name']} via {ADDONS_ROOT}"
    )


if __name__ == "__main__":
    main()
