"""Read-only regression check for Hair2_Centerline.003's outward front.

Run with Blender 5.2::

    blender --background --factory-startup --disable-autoexec \
        --python tests/verify_real_hair2_outward_blender.py -- X.blend

The source file is never saved. Temporary in-memory Curves cover Centered,
Surface, and several Blend Mix values, then are removed after validation.
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
CURVE_NAME = "Hair2_Centerline.003"
EXPECTED_FRONT_FACES = ((16,), (16, 19), (19, 33), (33, 36), (36,))
FRONT_TOLERANCE = 4.0e-4
BLEND_FACTORS = (0.1, 0.37, 0.83)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_addon():
    module_name = "character_designer_real_hair2_verifier"
    spec = importlib.util.spec_from_file_location(
        module_name,
        ADDON_ROOT / "__init__.py",
        submodule_search_locations=[str(ADDON_ROOT)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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


def evaluated_rings(curve):
    evaluated = curve.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        vertices = tuple(vertex.co.copy() for vertex in mesh.vertices)
    finally:
        evaluated.to_mesh_clear()
    point_count = len(curve.data.splines[0].points)
    if not vertices or len(vertices) % point_count:
        raise AssertionError("Hair2 evaluated profile cannot be divided into point rings")
    ring_size = len(vertices) // point_count
    return tuple(
        vertices[index * ring_size : (index + 1) * ring_size]
        for index in range(point_count)
    )


def assert_outward_profile(curve, sections):
    rings = evaluated_rings(curve)
    for index, (point, ring, section) in enumerate(
        zip(curve.data.splines[0].points, rings, sections)
    ):
        axis = point.co.xyz
        normal = Vector(section["shape_normal_local"]).normalized()
        projections = tuple((vertex - axis).dot(normal) for vertex in ring)
        expected = float(curve.data.bevel_depth) * float(point.radius)
        if max(projections) <= max(1.0e-7, expected * 0.25):
            raise AssertionError(f"Hair2 placement {index} has no outward bulge")
        if abs(min(projections)) > max(projections) + FRONT_TOLERANCE:
            raise AssertionError(f"Hair2 placement {index} faces inward")


def remove_curve(curve):
    data = curve.data
    bpy.data.objects.remove(curve, do_unlink=True)
    if data.users == 0:
        bpy.data.curves.remove(data)


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ()
    if len(args) != 1:
        raise SystemExit("Pass exactly one X.blend path after --")
    source_path = Path(args[0]).resolve()
    before_file = (
        source_path.stat().st_size,
        source_path.stat().st_mtime_ns,
        sha256(source_path),
    )
    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    cd = load_addon()
    recorded = bpy.data.objects.get(CURVE_NAME)
    if recorded is None:
        raise AssertionError(f"Missing {CURVE_NAME}")
    before_curve = object_fingerprint(recorded)

    source, layers, centers, metadata = cd._metadata_from_recorded_source(recorded)
    if source.name != "Hair2":
        raise AssertionError("Hair2 centerline resolved the wrong source")
    if tuple(len(layer) for layer in layers) != (8, 8, 8, 8, 8):
        raise AssertionError("Hair2 rounded-rectangle topology changed")
    if metadata.get("version") != cd.METADATA_VERSION:
        raise AssertionError("Hair2 refresh did not build current metadata")
    sections = metadata["sections"]
    if any(section["shape_source"] != "FRONT_WIDE_FACE" for section in sections):
        raise AssertionError("Hair2 did not use its dominant broad-face ribbon")
    front_faces = tuple(tuple(section["front_face_indices"]) for section in sections)
    if front_faces != EXPECTED_FRONT_FACES:
        raise AssertionError(f"Hair2 chose the wrong ribbon faces: {front_faces}")

    segment_tangents = tuple(
        (second - first).normalized() for first, second in zip(centers, centers[1:])
    )
    curvature_dots = []
    for index, section in enumerate(sections):
        if index == 0:
            outward = segment_tangents[0] - segment_tangents[1]
        elif index == len(sections) - 1:
            outward = segment_tangents[-2] - segment_tangents[-1]
        else:
            outward = segment_tangents[index - 1] - segment_tangents[index]
        tangent = Vector(section["tangent_local"]).normalized()
        outward -= tangent * outward.dot(tangent)
        outward.normalize()
        normal = Vector(section["shape_normal_local"]).normalized()
        curvature_dots.append(normal.dot(outward))
    if min(curvature_dots) < 0.5:
        raise AssertionError(f"Hair2 front is not on the curvature outside: {curvature_dots}")

    target = cd._automatic_centerline_target(
        bpy.context,
        source,
        layers,
    )
    if target is not recorded:
        raise AssertionError(f"One-action matching chose {getattr(target, 'name', None)}")

    temporaries = []
    edit_curve_live = False
    try:
        centered_curve = cd._create_centerline_object(
            bpy.context,
            source,
            layers,
            centers,
            metadata,
            alignment=cd.HAIR_ALIGNMENT_CENTERED,
        )
        temporaries.append(centered_curve)
        surface_curve = cd._create_centerline_object(
            bpy.context,
            source,
            layers,
            centers,
            metadata,
            alignment=cd.HAIR_ALIGNMENT_FRONT_FLUSH,
        )
        temporaries.append(surface_curve)
        blend_curves = {}
        for factor in BLEND_FACTORS:
            blend_curve = cd._create_centerline_object(
                bpy.context,
                source,
                layers,
                centers,
                metadata,
                alignment=cd.HAIR_ALIGNMENT_BLEND,
                blend_factor=factor,
            )
            temporaries.append(blend_curve)
            blend_curves[factor] = blend_curve
        for temporary in temporaries:
            assert_outward_profile(temporary, sections)

        centered = tuple(
            point.co.xyz.copy()
            for point in centered_curve.data.splines[0].points
        )
        surface = tuple(
            point.co.xyz.copy()
            for point in surface_curve.data.splines[0].points
        )
        for index, (center, centered_point) in enumerate(zip(centers, centered)):
            if (centered_point - center).length > 2.0e-5:
                raise AssertionError(f"Hair2 Centered point {index} left its source mean")
        for factor, blend_curve in blend_curves.items():
            blended = tuple(
                point.co.xyz.copy() for point in blend_curve.data.splines[0].points
            )
            if abs(float(blend_curve[cd.HAIR_BLEND_FACTOR_KEY]) - factor) > 1.0e-8:
                raise AssertionError(f"Hair2 Blend {factor} was not persisted")
            for index, (centered_point, blend_point, surface_point) in enumerate(
                zip(centered, blended, surface)
            ):
                expected_blend = centered_point + (surface_point - centered_point) * factor
                if (blend_point - expected_blend).length > 2.0e-5:
                    raise AssertionError(
                        f"Hair2 Blend point {index} does not use Mix {factor}"
                    )

        edit_curve = recorded.copy()
        edit_curve.data = recorded.data.copy()
        edit_curve.name = f"{recorded.name}_LiveEditVerifier"
        bpy.context.scene.collection.objects.link(edit_curve)
        temporaries.append(edit_curve)
        if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        edit_curve.select_set(True)
        bpy.context.view_layer.objects.active = edit_curve
        if bpy.ops.object.mode_set(mode="EDIT") != {"FINISHED"}:
            raise AssertionError("Hair2 verifier could not enter Curve Edit Mode")
        for index, point in enumerate(edit_curve.data.splines[0].points):
            point.select = index % 2 == 0
        edit_selection = tuple(
            bool(point.select) for point in edit_curve.data.splines[0].points
        )
        edit_data_pointer = edit_curve.data.as_pointer()
        for alignment, factor in (
            (cd.HAIR_ALIGNMENT_FRONT_FLUSH, 1.0),
            (cd.HAIR_ALIGNMENT_CENTERED, 0.0),
            (cd.HAIR_ALIGNMENT_BLEND, 0.23),
            (cd.HAIR_ALIGNMENT_BLEND, 0.77),
        ):
            cd._commit_existing_centerline(
                edit_curve,
                None,
                layers,
                metadata,
                alignment,
                blend_factor=factor,
            )
            expected_points = cd._curve_profile_solution(
                metadata,
                alignment,
                blend_factor=factor,
            )[0]
            actual_points = tuple(
                point.co.xyz.copy() for point in edit_curve.data.splines[0].points
            )
            if any(
                (actual - expected).length > 2.0e-5
                for actual, expected in zip(actual_points, expected_points)
            ):
                raise AssertionError(
                    f"Hair2 Edit Curve placement failed for {alignment} {factor}"
                )
            if (
                bpy.context.mode != "EDIT_CURVE"
                or bpy.context.edit_object is not edit_curve
                or edit_curve.data.as_pointer() != edit_data_pointer
                or tuple(
                    bool(point.select)
                    for point in edit_curve.data.splines[0].points
                ) != edit_selection
            ):
                raise AssertionError(
                    "Hair2 Edit Curve placement changed its mode, data, or selection"
                )
        edit_curve_live = True

        rings = evaluated_rings(surface_curve)
        plane_errors = []
        inward_offsets = []
        for point, ring, center, section in zip(
            surface_curve.data.splines[0].points,
            rings,
            centers,
            sections,
        ):
            target_point = Vector(section["front_target_local"])
            normal = Vector(section["shape_normal_local"]).normalized()
            plane_errors.append(max((vertex - target_point).dot(normal) for vertex in ring))
            inward_offsets.append((point.co.xyz - center).dot(normal))
        if max(abs(value) for value in plane_errors) > FRONT_TOLERANCE:
            raise AssertionError(f"Hair2 front-plane miss: {plane_errors}")
        if max(inward_offsets) >= 0.0:
            raise AssertionError(f"Hair2 Curve axis did not move behind the front: {inward_offsets}")
    finally:
        if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for temporary in tuple(temporaries):
            if temporary.name in bpy.data.objects:
                remove_curve(temporary)

    if object_fingerprint(recorded) != before_curve:
        raise AssertionError("Verification changed Hair2_Centerline.003 in memory")
    after_file = (
        source_path.stat().st_size,
        source_path.stat().st_mtime_ns,
        sha256(source_path),
    )
    if after_file != before_file:
        raise AssertionError("Verification changed X.blend on disk")
    print(
        "PASS Real Hair2 Outward",
        json.dumps(
            {
                "target": target.name,
                "front_faces": front_faces,
                "curvature_dots": curvature_dots,
                "placements": ["CENTERED", "FRONT_FLUSH"],
                "blend_factors": BLEND_FACTORS,
                "edit_curve_live": edit_curve_live,
                "sha256": before_file[2],
            },
            separators=(",", ":"),
        ),
    )


if __name__ == "__main__":
    main()
