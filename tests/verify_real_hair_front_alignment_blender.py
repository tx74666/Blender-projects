"""Read-only real-scene verification for Hair Centerline front alignment.

Run with Blender 5.2::

    blender --background --factory-startup \
        --python tests/verify_real_hair_front_alignment_blender.py -- AUTOSAVE.blend

The source ``.blend`` is opened with UI loading disabled and is never saved.
Only temporary in-memory Curve objects are created, verified, and removed.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDON_ROOT = PROJECT_ROOT / "addons" / "character_designer"
CURVE_NAMES = ("Hair1_Centerline", "Hair1_Centerline.001")
FRONT_TOLERANCE = 4.0e-4
CENTER_TOLERANCE = 2.0e-6


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_addon():
    module_name = "character_designer_real_front_verifier"
    spec = importlib.util.spec_from_file_location(
        module_name,
        ADDON_ROOT / "__init__.py",
        submodule_search_locations=[str(ADDON_ROOT)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def evaluated_rings(curve):
    evaluated = curve.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        vertices = tuple(vertex.co.copy() for vertex in mesh.vertices)
    finally:
        evaluated.to_mesh_clear()
    point_count = len(curve.data.splines[0].points)
    if not vertices or len(vertices) % point_count:
        raise AssertionError(
            f"{curve.name}: evaluated vertices do not divide into control-point rings"
        )
    ring_size = len(vertices) // point_count
    return tuple(
        vertices[index * ring_size : (index + 1) * ring_size]
        for index in range(point_count)
    )


def object_fingerprint(obj):
    return (
        obj.as_pointer(),
        obj.data.as_pointer(),
        tuple(float(value) for row in obj.matrix_world for value in row),
        tuple(sorted((str(key), repr(obj[key])) for key in obj.keys())),
        tuple(
            (
                tuple(float(value) for value in point.co),
                float(point.radius),
                float(point.tilt),
            )
            for spline in obj.data.splines
            for point in spline.points
        ),
    )


def remove_curve(curve):
    data = curve.data
    bpy.data.objects.remove(curve, do_unlink=True)
    if data.users == 0:
        bpy.data.curves.remove(data)


def verify_curve(cd, source, recorded):
    source_obj, layers, centers, metadata = cd._metadata_from_recorded_source(recorded)
    if source_obj is not source:
        raise AssertionError(f"{recorded.name}: resolved the wrong source object")
    if metadata.get("version") != cd.METADATA_VERSION:
        raise AssertionError(f"{recorded.name}: source refresh did not build current metadata")

    temporary = cd._create_centerline_object(
        bpy.context,
        source,
        layers,
        centers,
        metadata,
        align_front_surface=True,
    )
    try:
        if temporary.get("character_designer_alignment") != cd.HAIR_ALIGNMENT_FRONT_FLUSH:
            raise AssertionError(f"{recorded.name}: temporary output was not Front Surface")
        rings = evaluated_rings(temporary)
        errors = []
        for ring, section in zip(rings, metadata["sections"]):
            target = Vector(section["front_target_local"])
            normal = Vector(section["shape_normal_local"]).normalized()
            errors.append(max((vertex - target).dot(normal) for vertex in ring))
        maximum_error = max(abs(error) for error in errors)
        if maximum_error > FRONT_TOLERANCE:
            raise AssertionError(
                f"{recorded.name}: front-plane error {maximum_error} exceeds "
                f"{FRONT_TOLERANCE}"
            )

        changed = cd._commit_existing_centerline(
            temporary,
            source,
            layers,
            metadata,
            cd.HAIR_ALIGNMENT_CENTERED,
        )
        if not changed:
            raise AssertionError(f"{recorded.name}: Reset Centered unexpectedly did nothing")
        if temporary.get("character_designer_alignment") != cd.HAIR_ALIGNMENT_CENTERED:
            raise AssertionError(f"{recorded.name}: Reset did not persist CENTERED")
        reset_errors = tuple(
            (point.co.xyz - center).length
            for point, center in zip(temporary.data.splines[0].points, centers)
        )
        maximum_reset_error = max(reset_errors, default=0.0)
        if maximum_reset_error > CENTER_TOLERANCE:
            raise AssertionError(
                f"{recorded.name}: Reset center error {maximum_reset_error} exceeds "
                f"{CENTER_TOLERANCE}"
            )
        print(
            "REAL_HAIR_FRONT_PASS",
            recorded.name,
            "layers",
            len(layers),
            "max_front_error",
            f"{maximum_error:.12g}",
            "max_reset_error",
            f"{maximum_reset_error:.12g}",
            "front_sources",
            json.dumps(
                [section["front_target_source"] for section in metadata["sections"]],
                separators=(",", ":"),
            ),
        )
    finally:
        if temporary.name in bpy.data.objects:
            remove_curve(temporary)


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ()
    if len(args) != 1:
        raise SystemExit("Pass exactly one autosave path after --")
    source_path = Path(args[0]).resolve()
    before_file = (
        source_path.stat().st_size,
        source_path.stat().st_mtime_ns,
        sha256(source_path),
    )
    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    cd = load_addon()
    source = bpy.data.objects.get("Hair1")
    if source is None or source.type != "MESH":
        raise AssertionError("The autosave has no Hair1 mesh")
    recorded = tuple(bpy.data.objects.get(name) for name in CURVE_NAMES)
    if any(curve is None for curve in recorded):
        raise AssertionError("The autosave is missing a primary recorded Hair1 centerline")
    before_objects = {curve.name: object_fingerprint(curve) for curve in recorded}
    for curve in recorded:
        verify_curve(cd, source, curve)
    after_objects = {curve.name: object_fingerprint(curve) for curve in recorded}
    if after_objects != before_objects:
        raise AssertionError("Verification changed an original Hair1 centerline in memory")
    after_file = (
        source_path.stat().st_size,
        source_path.stat().st_mtime_ns,
        sha256(source_path),
    )
    if after_file != before_file:
        raise AssertionError("Verification changed the autosave on disk")
    print("FILE_UNCHANGED", True, "sha256", before_file[2])
    print("PASS Real Hair1 Front Alignment", len(recorded), "curves")


if __name__ == "__main__":
    main()
