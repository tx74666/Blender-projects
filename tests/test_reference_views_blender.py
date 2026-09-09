import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = PROJECT_ROOT / "addons"
if str(ADDONS_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDONS_ROOT))

import character_designer
from character_designer import reference_views


TOLERANCE = 1.0e-5


def assert_vector_close(actual, expected, tolerance=TOLERANCE):
    actual = Vector(actual)
    expected = Vector(expected)
    if (actual - expected).length > tolerance:
        raise AssertionError(f"Expected {tuple(expected)}, got {tuple(actual)}")


def reset_scene():
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for scene in tuple(bpy.data.scenes)[1:]:
        bpy.data.scenes.remove(scene)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
    bpy.context.scene.unit_settings.scale_length = 1.0


def write_png(path, color):
    image = bpy.data.images.new(f"Write_{path.stem}", width=4, height=2, alpha=True)
    try:
        pixels = tuple(color) * (4 * 2)
        image.pixels[:] = pixels
        image.filepath_raw = str(path)
        image.file_format = "PNG"
        image.save()
    finally:
        bpy.data.images.remove(image)


def manifest_payload(set_id, *, views, placement=None, name="Industrial Pump"):
    return {
        "schema": "blackunity.cdesigner.reference-view-set",
        "version": 1,
        "setId": set_id,
        "name": name,
        "updatedAt": "2026-08-04T08:00:00Z",
        "units": "METERS",
        "placement": placement
        or {
            "origin": [1.0, 2.0, 3.0],
            "displaySizeMeters": 2.0,
            "distanceMeters": 10.0,
            "opacity": 0.4,
            "showInFront": False,
        },
        "views": views,
        "unknownFutureField": {"isIgnored": True},
    }


def write_manifest(path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def make_directory_alias(link, target):
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return True
    try:
        os.symlink(target, link, target_is_directory=True)
        return True
    except (NotImplementedError, OSError):
        return False


def remove_directory_alias(path):
    if not os.path.lexists(path):
        return
    if os.name == "nt":
        os.rmdir(path)
    else:
        os.unlink(path)


def managed_set_objects(scene, set_id):
    root = None
    views = {}
    for obj in scene.objects:
        if obj.get("cdesigner_reference_generator") != reference_views.REFERENCE_GENERATOR_ID:
            continue
        if obj.get("cdesigner_reference_set_id") != set_id:
            continue
        if obj.get("cdesigner_reference_kind") == "ROOT":
            root = obj
        elif obj.get("cdesigner_reference_kind") == "VIEW":
            views[obj["cdesigner_reference_view"]] = obj
    return root, views


def make_selected_edit_object():
    mesh = bpy.data.meshes.new("UntouchedSourceMesh")
    mesh.from_pydata(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)), ((0, 1),), ())
    mesh.update()
    obj = bpy.data.objects.new("UntouchedSource", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    return obj


def test_all_six_direction_bases_follow_contract():
    expected = {
        "front": ((0.0, 2.0, 0.0), (0.0, -1.0, 0.0)),
        "back": ((0.0, -2.0, 0.0), (0.0, 1.0, 0.0)),
        "left": ((2.0, 0.0, 0.0), (-1.0, 0.0, 0.0)),
        "right": ((-2.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        "top": ((0.0, 0.0, -2.0), (0.0, 0.0, 1.0)),
        "bottom": ((0.0, 0.0, 2.0), (0.0, 0.0, -1.0)),
    }
    for direction, (translation, normal) in expected.items():
        matrix = reference_views._view_local_matrix(direction, 2.0)
        assert_vector_close(matrix.translation, translation)
        assert_vector_close(matrix.col[2].xyz, normal)
    flipped = reference_views._view_local_matrix("front", 2.0, True, True)
    assert_vector_close(flipped.col[0].xyz, (-1.0, 0.0, 0.0))
    assert_vector_close(flipped.col[1].xyz, (0.0, 0.0, -1.0))
    assert_vector_close(flipped.col[2].xyz, (0.0, -1.0, 0.0))


def test_contract_units_orientation_idempotency_and_edit_state():
    reset_scene()
    set_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        write_png(folder / "front.png", (1.0, 0.0, 0.0, 1.0))
        write_png(folder / "right.png", (0.0, 1.0, 0.0, 1.0))
        manifest_path = folder / "reference-views.json"
        write_manifest(
            manifest_path,
            manifest_payload(
                set_id,
                views={
                    "front": {
                        "file": "front.png",
                        "enabled": True,
                        "flipHorizontal": False,
                        "flipVertical": False,
                        "distanceMeters": None,
                        "displaySizeMeters": None,
                        "opacity": None,
                    },
                    "right": {
                        "file": "right.png",
                        "enabled": True,
                        "flipHorizontal": True,
                        "flipVertical": False,
                        "distanceMeters": 3.0,
                        "displaySizeMeters": 0.75,
                        "opacity": 0.8,
                    },
                },
            ),
        )

        # Neither a user's same-named collection nor object is treated as owned.
        foreign_collection = bpy.data.collections.new(reference_views.REFERENCE_COLLECTION_NAME)
        bpy.context.scene.collection.children.link(foreign_collection)
        foreign_name = f"CD_REF_{set_id}"
        foreign_object = bpy.data.objects.new(foreign_name, None)
        foreign_collection.objects.link(foreign_object)
        source = make_selected_edit_object()
        bpy.context.scene.unit_settings.scale_length = 0.01
        selected_before = tuple(bpy.context.selected_objects)

        first = reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        if first["configured_views"] != 2 or first["enabled_views"] != 2:
            raise AssertionError("Configured/enabled view counts include empty slots")
        if bpy.context.mode != "EDIT_MESH" or bpy.context.edit_object is not source:
            raise AssertionError("Reference sync changed Edit Mode or the active source")
        if tuple(bpy.context.selected_objects) != selected_before:
            raise AssertionError("Reference sync changed the object selection")

        root, views = managed_set_objects(bpy.context.scene, set_id)
        if root is None or set(views) != {"front", "right"}:
            raise AssertionError("The two configured Image Empties were not created")
        if root.name == foreign_object.name or foreign_object.get(
            "cdesigner_reference_generator"
        ):
            raise AssertionError("A same-named user object was overwritten or claimed")
        managed_collection = first["collection"]
        if managed_collection is foreign_collection or foreign_collection.get(
            "cdesigner_reference_generator"
        ):
            raise AssertionError("A same-named user collection was overwritten or claimed")

        assert_vector_close(root.matrix_world.translation, (100.0, 200.0, 300.0))
        front = views["front"]
        right = views["right"]
        assert_vector_close(front.matrix_basis.translation, (0.0, 1000.0, 0.0))
        assert_vector_close(front.matrix_basis.col[2].xyz, (0.0, -1.0, 0.0))
        assert_vector_close(right.matrix_basis.translation, (-300.0, 0.0, 0.0))
        assert_vector_close(right.matrix_basis.col[2].xyz, (1.0, 0.0, 0.0))
        if abs(front.empty_display_size - 200.0) > TOLERANCE:
            raise AssertionError("Global meter display size did not convert to Blender Units")
        if abs(right.empty_display_size - 75.0) > TOLERANCE:
            raise AssertionError("Per-view meter display size override was ignored")
        if (
            front.type != "EMPTY"
            or front.empty_display_type != "IMAGE"
            or front.empty_image_side != "FRONT"
            or front.show_in_front
            or not front.hide_render
            or abs(front.color[3] - 0.4) > TOLERANCE
            or abs(right.color[3] - 0.8) > TOLERANCE
        ):
            raise AssertionError("Image Empty display contract was not applied")

        pointers_before = {
            "root": root.as_pointer(),
            "front": front.as_pointer(),
            "right": right.as_pointer(),
            "front_image": front.data.as_pointer(),
            "right_image": right.data.as_pointer(),
        }
        object_count = len(bpy.data.objects)
        image_count = len(bpy.data.images)
        second = reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        root, views = managed_set_objects(bpy.context.scene, set_id)
        pointers_after = {
            "root": root.as_pointer(),
            "front": views["front"].as_pointer(),
            "right": views["right"].as_pointer(),
            "front_image": views["front"].data.as_pointer(),
            "right_image": views["right"].data.as_pointer(),
        }
        if (
            pointers_before != pointers_after
            or len(bpy.data.objects) != object_count
            or len(bpy.data.images) != image_count
            or second["created_objects"] != 0
        ):
            raise AssertionError("Repeated manifest sync was not idempotent")


def test_disabled_view_is_hidden_without_implicit_deletion():
    reset_scene()
    set_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        write_png(folder / "right.png", (0.2, 0.3, 0.4, 1.0))
        manifest_path = folder / "reference-views.json"
        payload = manifest_payload(
            set_id,
            views={
                "right": {
                    "file": "right.png",
                    "enabled": True,
                    "flipHorizontal": False,
                    "flipVertical": False,
                    "distanceMeters": None,
                    "displaySizeMeters": None,
                    "opacity": None,
                }
            },
        )
        write_manifest(manifest_path, payload)
        reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        _root, views = managed_set_objects(bpy.context.scene, set_id)
        right = views["right"]
        pointer = right.as_pointer()

        payload["views"]["right"] = {
            "file": None,
            "enabled": False,
            "flipHorizontal": False,
            "flipVertical": False,
            "distanceMeters": None,
            "displaySizeMeters": None,
            "opacity": None,
        }
        payload["updatedAt"] = "2026-08-04T08:01:00Z"
        write_manifest(manifest_path, payload)
        reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        _root, views = managed_set_objects(bpy.context.scene, set_id)
        if views["right"].as_pointer() != pointer or not views["right"].hide_viewport:
            raise AssertionError("Disabling a view deleted it or failed to hide it")
        reference_views.set_reference_view_visibility(bpy.context.scene, set_id, True)
        if not views["right"].hide_viewport:
            raise AssertionError("Show Set incorrectly revealed a manifest-disabled view")


def test_six_slot_partial_manifest_accepts_enabled_null_files():
    reset_scene()
    set_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        write_png(folder / "front.png", (0.8, 0.7, 0.6, 1.0))
        views = {}
        for direction in reference_views.REFERENCE_VIEW_DIRECTIONS:
            views[direction] = {
                "file": "front.png" if direction == "front" else None,
                # This deliberately preserves the early Console bug. The five
                # null slots must still behave as empty/unconfigured slots.
                "enabled": True,
                "flipHorizontal": False,
                "flipVertical": False,
                "distanceMeters": None,
                "displaySizeMeters": None,
                "opacity": None,
            }
        manifest_path = folder / "reference-views.json"
        write_manifest(manifest_path, manifest_payload(set_id, views=views))
        parsed = reference_views.read_reference_view_manifest(str(manifest_path))
        if sum(view["configured"] for view in parsed["views"]) != 1:
            raise AssertionError("Null image slots were counted as configured")
        summary = reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        _root, managed_views = managed_set_objects(bpy.context.scene, set_id)
        if (
            set(managed_views) != {"front"}
            or summary["configured_views"] != 1
            or summary["enabled_views"] != 1
        ):
            raise AssertionError("A partial six-slot manifest did not create only Front")


def test_image_replacement_reclaims_only_owned_orphan():
    reset_scene()
    set_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        write_png(folder / "front-a.png", (1.0, 0.0, 0.0, 1.0))
        write_png(folder / "front-b.png", (0.0, 0.0, 1.0, 1.0))
        manifest_path = folder / "reference-views.json"
        payload = manifest_payload(
            set_id,
            views={
                "front": {
                    "file": "front-a.png",
                    "enabled": True,
                    "flipHorizontal": False,
                    "flipVertical": False,
                    "distanceMeters": None,
                    "displaySizeMeters": None,
                    "opacity": None,
                }
            },
        )
        write_manifest(manifest_path, payload)
        reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        _root, views = managed_set_objects(bpy.context.scene, set_id)
        old_image = views["front"].data
        old_pointer = old_image.as_pointer()
        image_count = len(bpy.data.images)

        payload["views"]["front"]["file"] = "front-b.png"
        payload["updatedAt"] = "2026-08-04T08:02:00Z"
        write_manifest(manifest_path, payload)
        reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        _root, views = managed_set_objects(bpy.context.scene, set_id)
        if views["front"].data.as_pointer() == old_pointer:
            raise AssertionError("Changed image path did not replace the managed Image")
        if len(bpy.data.images) != image_count:
            raise AssertionError("Replacing an owned Image leaked an orphan data-block")


def test_scene_state_recovery_without_manifest_hide_show_clear():
    reset_scene()
    first_set_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        write_png(folder / "front.png", (0.7, 0.2, 0.4, 1.0))
        first_manifest = folder / "first-reference-views.json"
        write_manifest(
            first_manifest,
            manifest_payload(
                first_set_id,
                name="Recovered Prop",
                views={
                    "front": {
                        "file": "front.png",
                        "enabled": True,
                        "flipHorizontal": False,
                        "flipVertical": False,
                        "distanceMeters": None,
                        "displaySizeMeters": None,
                        "opacity": None,
                    }
                },
            ),
        )
        reference_views.sync_reference_view_set(bpy.context, str(first_manifest))
        first_root, first_views = managed_set_objects(bpy.context.scene, first_set_id)
        first_root_name = first_root.name
        user_object = bpy.data.objects.new("Unowned Recovery Sentinel", None)
        bpy.context.scene.collection.objects.link(user_object)

        settings = bpy.context.window_manager.character_designer_references
        settings.manifest_path = ""
        settings.active_set_id = ""
        settings.active_set_name = ""
        settings.configured_view_count = 0
        settings.enabled_view_count = 0
        settings.property_unset("scene_set_choice")
        first_manifest.unlink()

        summaries = reference_views._scene_managed_set_summaries(bpy.context.scene)
        if len(summaries) != 1 or summaries[0]["set_id"] != first_set_id:
            raise AssertionError("A saved exact-tagged set was not recovered from the Scene")
        if not bpy.ops.character_designer.reference_visibility.poll():
            raise AssertionError("Recovered single set cannot be hidden or shown")
        if bpy.ops.character_designer.reference_visibility(visible=False) != {"FINISHED"}:
            raise AssertionError("Recovered single set could not be hidden")
        if not first_views["front"].hide_viewport:
            raise AssertionError("Recovered set Hide did not affect its managed view")
        if bpy.ops.character_designer.reference_visibility(visible=True) != {"FINISHED"}:
            raise AssertionError("Recovered single set could not be shown")
        if first_views["front"].hide_viewport:
            raise AssertionError("Recovered set Show did not reveal its enabled view")
        if not bpy.ops.character_designer.clear_reference_views.poll():
            raise AssertionError("Clear still depends on a manifest or saved WindowManager state")
        if bpy.ops.character_designer.clear_reference_views() != {"FINISHED"}:
            raise AssertionError("Recovered single set could not be safely cleared")
        if (
            bpy.data.objects.get(first_root_name) is not None
            or managed_set_objects(bpy.context.scene, first_set_id)[1]
            or bpy.data.objects.get(user_object.name) is not user_object
        ):
            raise AssertionError("Recovered clear missed managed data or removed unowned data")

        # With multiple recovered sets there is deliberately no implicit first
        # choice. The dropdown sentinel keeps destructive actions disabled until
        # the artist chooses one exact UUID.
        set_ids = (str(uuid.uuid4()), str(uuid.uuid4()))
        for index, set_id in enumerate(set_ids):
            manifest = folder / f"set-{index}.json"
            write_manifest(
                manifest,
                manifest_payload(
                    set_id,
                    name=f"Recovered Set {index + 1}",
                    views={
                        "front": {
                            "file": "front.png",
                            "enabled": True,
                            "flipHorizontal": False,
                            "flipVertical": False,
                            "distanceMeters": None,
                            "displaySizeMeters": None,
                            "opacity": None,
                        }
                    },
                ),
            )
            reference_views.sync_reference_view_set(bpy.context, str(manifest))
        settings.manifest_path = ""
        settings.active_set_id = ""
        settings.active_set_name = ""
        settings.property_unset("scene_set_choice")
        if bpy.ops.character_designer.clear_reference_views.poll():
            raise AssertionError("Multiple recovered sets bypassed explicit selection")
        settings.scene_set_choice = set_ids[1]
        if not bpy.ops.character_designer.clear_reference_views.poll():
            raise AssertionError("The recovered-set dropdown did not select an exact set")
        if bpy.ops.character_designer.clear_reference_views() != {"FINISHED"}:
            raise AssertionError("The selected recovered set could not be cleared")
        if managed_set_objects(bpy.context.scene, set_ids[1]) != (None, {}):
            raise AssertionError("The chosen recovered set was not cleared")
        if managed_set_objects(bpy.context.scene, set_ids[0])[0] is None:
            raise AssertionError("Clearing one recovered set touched a different set")


def test_shared_scene_preflight_rejects_with_zero_changes():
    reset_scene()
    set_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        write_png(folder / "front.png", (0.3, 0.4, 0.9, 1.0))
        manifest_path = folder / "reference-views.json"
        payload = manifest_payload(
            set_id,
            views={
                "front": {
                    "file": "front.png",
                    "enabled": True,
                    "flipHorizontal": False,
                    "flipVertical": False,
                    "distanceMeters": None,
                    "displaySizeMeters": None,
                    "opacity": None,
                }
            },
        )
        write_manifest(manifest_path, payload)
        summary = reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        root, views = managed_set_objects(bpy.context.scene, set_id)
        front = views["front"]
        collection = summary["collection"]

        payload["placement"]["origin"] = [4.0, 5.0, 6.0]
        payload["placement"]["displaySizeMeters"] = 7.0
        payload["updatedAt"] = "2026-08-04T08:03:00Z"
        write_manifest(manifest_path, payload)
        other_scene = bpy.data.scenes.new("SharedReferenceScene")

        def state_signature():
            return {
                "objects": tuple(sorted(obj.as_pointer() for obj in bpy.data.objects)),
                "images": tuple(sorted(image.as_pointer() for image in bpy.data.images)),
                "collections": tuple(
                    sorted(item.as_pointer() for item in bpy.data.collections)
                ),
                "root_matrix": tuple(value for row in root.matrix_world for value in row),
                "front_matrix": tuple(value for row in front.matrix_world for value in row),
                "front_size": front.empty_display_size,
                "front_image": front.data.as_pointer(),
                "active": (
                    bpy.context.view_layer.objects.active.as_pointer()
                    if bpy.context.view_layer.objects.active
                    else 0
                ),
                "selected": tuple(
                    sorted(obj.as_pointer() for obj in bpy.context.selected_objects)
                ),
                "mode": bpy.context.mode,
            }

        other_scene.collection.children.link(collection)
        before_collection_failure = state_signature()
        try:
            reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        except reference_views.ReferenceViewError as exc:
            if "collection is shared by multiple Scenes" not in str(exc):
                raise
        else:
            raise AssertionError("A cross-Scene managed collection was synchronized")
        if state_signature() != before_collection_failure:
            raise AssertionError("Shared-collection preflight changed Blender data")
        other_scene.collection.children.unlink(collection)

        other_scene.collection.objects.link(front)
        before_object_failure = state_signature()
        try:
            reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        except reference_views.ReferenceViewError as exc:
            if "object" not in str(exc) or "shared by multiple Scenes" not in str(exc):
                raise
        else:
            raise AssertionError("A cross-Scene managed view was synchronized")
        if state_signature() != before_object_failure:
            raise AssertionError("Shared-object preflight changed Blender data")


def test_sync_failure_rolls_back_existing_and_new_data():
    reset_scene()
    set_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        write_png(folder / "front.png", (0.9, 0.1, 0.1, 1.0))
        write_png(folder / "right.png", (0.1, 0.9, 0.1, 1.0))
        manifest_path = folder / "reference-views.json"
        payload = manifest_payload(
            set_id,
            views={
                "front": {
                    "file": "front.png",
                    "enabled": True,
                    "flipHorizontal": False,
                    "flipVertical": False,
                    "distanceMeters": None,
                    "displaySizeMeters": None,
                    "opacity": None,
                }
            },
        )
        write_manifest(manifest_path, payload)
        reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        root, views = managed_set_objects(bpy.context.scene, set_id)
        front = views["front"]
        root_matrix = root.matrix_world.copy()
        front_matrix = front.matrix_world.copy()
        front_size = front.empty_display_size
        object_pointers = {obj.as_pointer() for obj in bpy.data.objects}
        image_pointers = {image.as_pointer() for image in bpy.data.images}

        payload["placement"]["origin"] = [9.0, 8.0, 7.0]
        payload["placement"]["displaySizeMeters"] = 5.0
        payload["views"]["right"] = {
            "file": "right.png",
            "enabled": True,
            "flipHorizontal": False,
            "flipVertical": False,
            "distanceMeters": None,
            "displaySizeMeters": None,
            "opacity": None,
        }
        write_manifest(manifest_path, payload)

        original_apply = reference_views._apply_view_object

        def fail_on_right(view_obj, root_obj, view, image, manifest, units_per_meter):
            if view["direction"] == "right":
                raise RuntimeError("injected Reference View failure")
            return original_apply(view_obj, root_obj, view, image, manifest, units_per_meter)

        reference_views._apply_view_object = fail_on_right
        try:
            try:
                reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
            except RuntimeError as exc:
                if "injected Reference View failure" not in str(exc):
                    raise
            else:
                raise AssertionError("Injected sync failure unexpectedly succeeded")
        finally:
            reference_views._apply_view_object = original_apply

        restored_root, restored_views = managed_set_objects(bpy.context.scene, set_id)
        if set(restored_views) != {"front"}:
            raise AssertionError("Failed transaction left a partially created direction")
        if (
            {obj.as_pointer() for obj in bpy.data.objects} != object_pointers
            or {image.as_pointer() for image in bpy.data.images} != image_pointers
            or restored_root.matrix_world != root_matrix
            or restored_views["front"].matrix_world != front_matrix
            or abs(restored_views["front"].empty_display_size - front_size) > TOLERANCE
        ):
            raise AssertionError("Failed sync did not restore its complete prior state")


def test_manifest_validation_containment_and_standard_scan():
    reset_scene()
    set_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary)
        set_folder = project / "References" / "CDesigner" / "Pump"
        set_folder.mkdir(parents=True)
        outside = project / "outside.png"
        write_png(outside, (0.1, 0.2, 0.3, 1.0))
        manifest_path = set_folder / "reference-views.json"
        payload = manifest_payload(
            set_id,
            views={
                "front": {
                    "file": "../../../outside.png",
                    "enabled": True,
                    "flipHorizontal": False,
                    "flipVertical": False,
                    "distanceMeters": None,
                    "displaySizeMeters": None,
                    "opacity": None,
                }
            },
        )
        write_manifest(manifest_path, payload)
        try:
            reference_views.read_reference_view_manifest(str(manifest_path))
        except reference_views.ReferenceViewError as exc:
            if "escape" not in str(exc) and "'..'" not in str(exc):
                raise
        else:
            raise AssertionError("A manifest image escaped its set folder")

        write_png(set_folder / "front.png", (0.4, 0.5, 0.6, 1.0))
        payload["views"]["front"]["file"] = "front.png"
        payload["views"]["futureObliqueView"] = {"producerMetadata": 7}
        write_manifest(manifest_path, payload)
        parsed = reference_views.read_reference_view_manifest(str(manifest_path))
        if parsed["set_id"] != set_id:
            raise AssertionError("A valid contract manifest did not parse")
        found = reference_views.discover_reference_view_manifests(str(project))
        if found != (str(manifest_path.resolve()),):
            raise AssertionError("Standard Reference View Set discovery returned the wrong files")

        external_folder = project / "ExternalReferenceSets"
        external_folder.mkdir()
        external_manifest = external_folder / "reference-views.json"
        external_manifest.write_text("{}", encoding="utf-8")
        scan_root = project / "References" / "CDesigner"
        alias = scan_root / "LinkedOutside"
        alias_created = make_directory_alias(alias, external_folder)
        if os.name == "nt" and not alias_created:
            raise AssertionError("Windows test could not create a Junction or directory symlink")
        try:
            found = reference_views.discover_reference_view_manifests(str(project))
            if found != (str(manifest_path.resolve()),):
                raise AssertionError("Discovery followed an external directory alias")
            if reference_views._realpath_is_within(scan_root, external_manifest):
                raise AssertionError("Realpath containment accepted an external manifest")
            if alias_created and not reference_views._is_reparse_directory(alias):
                raise AssertionError("A symlink/Junction was not recognized as a reparse directory")
        finally:
            if alias_created:
                remove_directory_alias(alias)

        if not bpy.data.filepath and reference_views.discover_reference_view_manifests():
            raise AssertionError("Unsaved blend discovery incorrectly scanned the process cwd")

        for invalid_file in ("images\\front.png", "C:front.png"):
            payload["views"]["front"]["file"] = invalid_file
            write_manifest(manifest_path, payload)
            try:
                reference_views.read_reference_view_manifest(str(manifest_path))
            except reference_views.ReferenceViewError:
                pass
            else:
                raise AssertionError(f"Non-POSIX image path {invalid_file!r} was accepted")
        payload["views"]["front"]["file"] = "front.png"

        invalid_contracts = (
            ("floating version", lambda value: value.__setitem__("version", 1.0)),
            (
                "null enabled",
                lambda value: value["views"]["front"].__setitem__("enabled", None),
            ),
            (
                "null horizontal flip",
                lambda value: value["views"]["front"].__setitem__(
                    "flipHorizontal",
                    None,
                ),
            ),
        )
        for label, mutate in invalid_contracts:
            invalid_payload = json.loads(json.dumps(payload))
            mutate(invalid_payload)
            write_manifest(manifest_path, invalid_payload)
            try:
                reference_views.read_reference_view_manifest(str(manifest_path))
            except reference_views.ReferenceViewError:
                pass
            else:
                raise AssertionError(f"Manifest accepted {label}")
        write_manifest(manifest_path, payload)

        hypothetical_blend = project / "scene.blend"
        standard_image = set_folder / "front.png"
        if reference_views._portable_image_filepath(
            str(standard_image),
            str(hypothetical_blend),
        ) != "//References/CDesigner/Pump/front.png":
            raise AssertionError("A project-local image was not stored as a // path")
        if reference_views._portable_image_filepath(
            str(outside),
            str(set_folder / "scene.blend"),
        ).startswith("//"):
            raise AssertionError("A project-external image was incorrectly made relative")

        payload["setId"] = "not-a-uuid"
        write_manifest(manifest_path, payload)
        try:
            reference_views.read_reference_view_manifest(str(manifest_path))
        except reference_views.ReferenceViewError:
            pass
        else:
            raise AssertionError("An invalid setId was accepted")

        payload["setId"] = set_id
        payload["placement"]["distanceMeters"] = float("nan")
        write_manifest(manifest_path, payload)
        try:
            reference_views.read_reference_view_manifest(str(manifest_path))
        except reference_views.ReferenceViewError:
            pass
        else:
            raise AssertionError("A non-finite placement value was accepted")


def test_temp_relative_image_path_recovers_from_owned_absolute_metadata():
    reset_scene()
    set_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        source_image = folder / "front.png"
        write_png(source_image, (0.35, 0.15, 0.85, 1.0))
        manifest_path = folder / "reference-views.json"
        write_manifest(
            manifest_path,
            manifest_payload(
                set_id,
                views={
                    "front": {
                        "file": "front.png",
                        "enabled": True,
                        "flipHorizontal": False,
                        "flipVertical": False,
                        "distanceMeters": None,
                        "displaySizeMeters": None,
                        "opacity": None,
                    }
                },
            ),
        )
        reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        _root, views = managed_set_objects(bpy.context.scene, set_id)
        front = views["front"]
        managed_image = front.data
        absolute_source = str(source_image.resolve())

        # Reproduce what happens when a project-relative image is read from a
        # Temp recovery file: // is now based beside quit.blend/autosave, not
        # beside the project.  The absolute ownership metadata survives.
        missing_relative = f"//missing-{uuid.uuid4()}/front.png"
        managed_image.filepath = missing_relative
        if reference_views._existing_absolute_image_path(managed_image.filepath):
            raise AssertionError("The recovery test's relative path unexpectedly exists")

        user_image = bpy.data.images.new("Unowned Relative Image", width=2, height=2)
        user_image.filepath = missing_relative
        user_empty = bpy.data.objects.new("Unowned Relative Image Empty", None)
        user_empty.empty_display_type = "IMAGE"
        user_empty.data = user_image
        bpy.context.scene.collection.objects.link(user_empty)

        reference_views._reference_images_load_post(None)
        if (
            reference_views._normalized_path(managed_image.filepath)
            != reference_views._normalized_path(absolute_source)
            or user_image.filepath != missing_relative
        ):
            raise AssertionError("The persistent load handler did not safely reconnect the Image")

        # Exercise the reporting API separately after the handler path above.
        managed_image.filepath = missing_relative
        result = reference_views.reconcile_managed_reference_images()
        if (
            result["reconnected"] != 1
            or result["reloaded"] != 1
            or result["unresolved"]
            or reference_views._normalized_path(managed_image.filepath)
            != reference_views._normalized_path(absolute_source)
            or managed_image.get("cdesigner_reference_image") != absolute_source
            or front.get("cdesigner_reference_image") != absolute_source
        ):
            raise AssertionError(
                "A managed Temp-relative Image was not reconnected exactly: "
                f"result={result!r}, filepath={managed_image.filepath!r}, "
                f"image_meta={managed_image.get('cdesigner_reference_image')!r}, "
                f"view_meta={front.get('cdesigner_reference_image')!r}, "
                f"expected={absolute_source!r}"
            )
        if user_image.filepath != missing_relative:
            raise AssertionError("Image recovery changed an unowned user Image")

        second = reference_views.reconcile_managed_reference_images()
        if second["reconnected"] or second["unresolved"]:
            raise AssertionError("Repeated managed Image recovery was not idempotent")

        # A valid current filepath is an intentional artist choice even when
        # older ownership metadata still names the originally synced file.
        alternate_source = folder / "artist-override.png"
        write_png(alternate_source, (0.1, 0.8, 0.3, 1.0))
        alternate_absolute = str(alternate_source.resolve())
        original_image_metadata = managed_image.get("cdesigner_reference_image")
        original_view_metadata = front.get("cdesigner_reference_image")
        managed_image.filepath = alternate_absolute
        valid_override = reference_views.reconcile_managed_reference_images()
        if (
            valid_override["reconnected"]
            or valid_override["unresolved"]
            or reference_views._normalized_path(managed_image.filepath)
            != reference_views._normalized_path(alternate_absolute)
            or managed_image.get("cdesigner_reference_image") != original_image_metadata
            or front.get("cdesigner_reference_image") != original_view_metadata
        ):
            raise AssertionError("Image recovery reverted a valid artist-selected filepath")

        if reference_views._reference_images_load_post not in bpy.app.handlers.load_post:
            raise AssertionError("The persistent managed Image load handler is not registered")
        if not bpy.app.timers.is_registered(
            reference_views._reference_images_reconcile_deferred
        ):
            raise AssertionError("The post-registration Image reconcile retry is not registered")


def test_reference_recovery_registration_is_restrict_data_safe():
    from _bpy_restrict_state import RestrictBlend

    reference_views.unregister_reference_view_handlers()
    with RestrictBlend():
        result = reference_views.reconcile_managed_reference_images()
        if result != {"reconnected": 0, "reloaded": 0, "unresolved": ()}:
            raise AssertionError("Restricted-data reconciliation returned mutable state")
        reference_views.register_reference_view_handlers()

    if reference_views._reference_images_load_post not in bpy.app.handlers.load_post:
        raise AssertionError("Restricted add-on registration lost the load handler")
    if not bpy.app.timers.is_registered(
        reference_views._reference_images_reconcile_deferred
    ):
        raise AssertionError("Restricted add-on registration lost its deferred retry")


def test_clear_only_owned_objects_and_protects_external_relationships():
    reset_scene()
    set_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        write_png(folder / "front.png", (0.6, 0.2, 0.7, 1.0))
        write_png(folder / "right.png", (0.2, 0.6, 0.7, 1.0))
        manifest_path = folder / "reference-views.json"
        write_manifest(
            manifest_path,
            manifest_payload(
                set_id,
                views={
                    "front": {
                        "file": "front.png",
                        "enabled": True,
                        "flipHorizontal": False,
                        "flipVertical": False,
                        "distanceMeters": None,
                        "displaySizeMeters": None,
                        "opacity": None,
                    },
                    "right": {
                        "file": "right.png",
                        "enabled": True,
                        "flipHorizontal": False,
                        "flipVertical": False,
                        "distanceMeters": None,
                        "displaySizeMeters": None,
                        "opacity": None,
                    },
                },
            ),
        )
        reference_views.sync_reference_view_set(bpy.context, str(manifest_path))
        root, views = managed_set_objects(bpy.context.scene, set_id)
        shared_front_image = views["front"].data

        other_set_id = str(uuid.uuid4())
        other_manifest_path = folder / "other-reference-views.json"
        write_manifest(
            other_manifest_path,
            manifest_payload(
                other_set_id,
                name="Unrelated Set",
                views={
                    "front": {
                        "file": "front.png",
                        "enabled": True,
                        "flipHorizontal": False,
                        "flipVertical": False,
                        "distanceMeters": None,
                        "displaySizeMeters": None,
                        "opacity": None,
                    }
                },
            ),
        )
        reference_views.sync_reference_view_set(bpy.context, str(other_manifest_path))
        other_root, other_views = managed_set_objects(bpy.context.scene, other_set_id)

        user_empty = bpy.data.objects.new("User Reference", None)
        user_empty.empty_display_type = "IMAGE"
        user_empty.data = shared_front_image
        bpy.context.scene.collection.objects.link(user_empty)
        user_child = bpy.data.objects.new("User Child", None)
        bpy.context.scene.collection.objects.link(user_child)
        user_child.parent = root

        first = reference_views.clear_reference_view_set(bpy.context.scene, set_id)
        if (
            first["deleted_objects"] != 2
            or root.name not in first["protected"]
            or bpy.data.objects.get(root.name) is not root
            or bpy.data.objects.get(user_empty.name) is not user_empty
            or bpy.data.objects.get(user_child.name) is not user_child
            or bpy.data.images.get(shared_front_image.name) is not shared_front_image
            or bpy.data.objects.get(other_root.name) is not other_root
            or bpy.data.objects.get(other_views["front"].name) is not other_views["front"]
        ):
            raise AssertionError("Safe clear removed user data or failed to protect the root")
        _root, remaining_views = managed_set_objects(bpy.context.scene, set_id)
        if remaining_views:
            raise AssertionError("Safe clear failed to remove exclusively owned views")

        user_child.parent = None
        second = reference_views.clear_reference_view_set(bpy.context.scene, set_id)
        if second["protected"] or second["deleted_objects"] != 1:
            raise AssertionError("An unshared managed root was not cleared on retry")


def main():
    character_designer.register()
    tests = (
        test_all_six_direction_bases_follow_contract,
        test_contract_units_orientation_idempotency_and_edit_state,
        test_disabled_view_is_hidden_without_implicit_deletion,
        test_six_slot_partial_manifest_accepts_enabled_null_files,
        test_image_replacement_reclaims_only_owned_orphan,
        test_scene_state_recovery_without_manifest_hide_show_clear,
        test_shared_scene_preflight_rejects_with_zero_changes,
        test_sync_failure_rolls_back_existing_and_new_data,
        test_manifest_validation_containment_and_standard_scan,
        test_temp_relative_image_path_recovers_from_owned_absolute_metadata,
        test_reference_recovery_registration_is_restrict_data_safe,
        test_clear_only_owned_objects_and_protects_external_relationships,
    )
    try:
        for test in tests:
            test()
            print(f"PASS {test.__name__}")
    finally:
        if hasattr(bpy.types.WindowManager, "character_designer"):
            character_designer.unregister()
        if reference_views._reference_images_load_post in bpy.app.handlers.load_post:
            raise AssertionError("Reference Image load handler survived add-on unregister")
        if bpy.app.timers.is_registered(reference_views._reference_images_reconcile_deferred):
            raise AssertionError("Reference Image reconcile timer survived add-on unregister")
    print(f"PASS Reference Views {len(tests)} tests")


if __name__ == "__main__":
    main()
