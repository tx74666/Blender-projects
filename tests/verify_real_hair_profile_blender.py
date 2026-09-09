"""Read-only Character Designer hair-profile acceptance test for a real autosave.

The verifier reconstructs v3 metadata from Hair1 and the layer sets already
stored on its generated center Curves, then creates new shaped Curves only in
memory.  It never saves the loaded file.

Examples::

    blender X_123_autosave.blend --background --python tests/verify_real_hair_profile_blender.py
    blender --background --factory-startup --python tests/verify_real_hair_profile_blender.py -- X_123_autosave.blend
    blender X_123_autosave.blend --background --python tests/verify_real_hair_profile_blender.py -- --hair Hair1
"""

import argparse
import bmesh
import bpy
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDON_ROOT = PROJECT_ROOT / "addons" / "character_designer"
GENERATOR_ID = "character_designer_centerline_v1"
TOLERANCE = 1.0e-5
ORIENTATION_TOLERANCE = 0.999
EXPECTED_PRIMARY_WIDTHS = (
    0.404089,
    0.352441,
    0.288051,
    0.198593,
    0.148427,
    0.117228,
    0.083157,
)
EXPECTED_SECONDARY_WIDTHS = (
    0.396728,
    0.420892,
    0.379845,
    0.331270,
    0.223211,
    0.086463,
)


def parse_args():
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("autosave", nargs="?")
    parser.add_argument("--hair", default="Hair1")
    return parser.parse_args(arguments)


def load_source_addon():
    """Load the workspace source under an isolated package name.

    A user's autosave can enable an older installed Character Designer.  The
    alias keeps this verifier tied to the source under test without registering
    duplicate Blender classes or changing the user's add-on session.
    """

    package_name = "character_designer_real_hair_verify"
    spec = importlib.util.spec_from_file_location(
        package_name,
        ADDON_ROOT / "__init__.py",
        submodule_search_locations=[str(ADDON_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Could not load the workspace Character Designer source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_close(actual, expected, tolerance=TOLERANCE, message=""):
    if abs(float(actual) - float(expected)) > tolerance:
        raise AssertionError(message or f"Expected {expected}, got {actual}")


def read_layer_set(curve_obj, vertex_count):
    try:
        layers = json.loads(curve_obj["character_designer_layer_vertices"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise AssertionError(f"{curve_obj.name} has no readable stored layer set") from exc
    if (
        not isinstance(layers, list)
        or len(layers) < 2
        or any(not isinstance(layer, list) or not layer for layer in layers)
        or any(
            not isinstance(index, int)
            or isinstance(index, bool)
            or index < 0
            or index >= vertex_count
            for layer in layers
            for index in layer
        )
        or len({index for layer in layers for index in layer})
        != sum(len(layer) for layer in layers)
    ):
        raise AssertionError(f"{curve_obj.name} has an invalid stored layer set")
    return tuple(tuple(layer) for layer in layers)


def find_stored_layer_sets(hair_obj):
    curves = sorted(
        (
            obj
            for obj in bpy.data.objects
            if obj.type == "CURVE"
            and obj.get("character_designer_generator") == GENERATOR_ID
            and obj.get("character_designer_source") == hair_obj.name
            and obj.get("character_designer_layer_vertices")
        ),
        key=lambda obj: obj.name,
    )
    if not curves:
        raise AssertionError(f"No stored Character Designer layer set targets {hair_obj.name}")
    return tuple(
        (curve_obj, read_layer_set(curve_obj, len(hair_obj.data.vertices)))
        for curve_obj in curves
    )


def evaluated_rings(curve_obj):
    evaluated = curve_obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        vertices = [vertex.co.copy() for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()
    point_count = len(curve_obj.data.splines[0].points)
    if not vertices or len(vertices) % point_count:
        raise AssertionError(
            f"{curve_obj.name}: evaluated mesh is not regular per center point "
            f"({len(vertices)} vertices / {point_count} points)"
        )
    ring_size = len(vertices) // point_count
    if ring_size < 3:
        raise AssertionError(f"{curve_obj.name}: HALF profile has fewer than three samples")
    return tuple(
        vertices[index * ring_size : (index + 1) * ring_size]
        for index in range(point_count)
    )


def ring_span(ring):
    return max((first - second).length for first in ring for second in ring)


def ring_bulge(ring, center):
    direction = sum(ring, Vector()) / len(ring) - Vector(center)
    if direction.length <= 1.0e-8:
        raise AssertionError("Evaluated HALF profile has no measurable bulge")
    return direction.normalized()


def adjacent_regular_index(sections, point_index):
    if sections[point_index]["kind"] != "POINT":
        raise AssertionError("Expected a POINT section")
    adjacent_index = 1 if point_index == 0 else point_index - 1
    if sections[adjacent_index]["kind"] == "POINT":
        raise AssertionError("A POINT endpoint has no adjacent regular section")
    return adjacent_index


def remove_temporary_curve(curve_obj):
    if curve_obj is None or curve_obj.name not in bpy.data.objects:
        return
    data = curve_obj.data
    bpy.data.objects.remove(curve_obj, do_unlink=True)
    if data.users == 0:
        bpy.data.curves.remove(data)


def validate_layer_set(character_designer, hair_obj, source_curve, layers, expected_widths):
    expected_sizes = (4,) * (len(layers) - 1) + (1,)
    if tuple(map(len, layers)) != expected_sizes:
        raise AssertionError(
            f"{source_curve.name}: expected regular four-point layers plus one POINT, "
            f"got {tuple(map(len, layers))}"
        )

    bm = bmesh.new()
    temporary_curve = None
    try:
        bm.from_mesh(hair_obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        centers = tuple(
            sum((bm.verts[index].co for index in layer), Vector()) / len(layer)
            for layer in layers
        )
        metadata = character_designer._build_cross_section_metadata(
            hair_obj,
            bm,
            layers,
            centers,
            "CLOSED",
        )
        sections = metadata["sections"]
        if (
            metadata.get("version") != 3
            or metadata.get("point_count") != len(layers)
            or metadata.get("profile_tip_radius") != 0.015
            or [section["kind"] for section in sections]
            != ["CLOSED"] * (len(layers) - 1) + ["POINT"]
        ):
            raise AssertionError(f"{source_curve.name}: reconstructed v3 metadata is incomplete")
        if any(section.get("shape_source") != "FRONT_WIDE_FACE" for section in sections):
            raise AssertionError(f"{source_curve.name}: a real Hair1 section lost its broad front face")

        boundary_widths = tuple(
            float(section["boundary_edge_span_local"])
            for section in sections
            if section["kind"] != "POINT"
        )
        shape_widths = tuple(
            float(section["shape_span_local"])
            for section in sections
            if section["kind"] != "POINT"
        )
        if len(boundary_widths) != len(layers) - 1 or any(width <= 0.0 for width in boundary_widths):
            raise AssertionError(f"{source_curve.name}: reconstructed boundary widths are invalid")
        for boundary, shape in zip(boundary_widths, shape_widths):
            assert_close(
                shape,
                boundary,
                message=f"{source_curve.name}: CLOSED shape width is not its real boundary edge",
            )
        if expected_widths:
            if len(boundary_widths) != len(expected_widths):
                raise AssertionError(f"{source_curve.name}: expected-width fixture count changed")
            for actual, expected in zip(boundary_widths, expected_widths):
                assert_close(
                    actual,
                    expected,
                    tolerance=5.0e-4,
                    message=f"{source_curve.name}: audited Hair1 boundary width changed",
                )

        temporary_curve = character_designer._create_centerline_object(
            bpy.context,
            hair_obj,
            layers,
            centers,
            metadata,
        )
        data = temporary_curve.data
        points = data.splines[0].points
        if (
            data.bevel_mode != "ROUND"
            or data.fill_mode != "HALF"
            or data.twist_mode != "MINIMUM"
            or data.bevel_resolution != character_designer.HAIR_PROFILE_BEVEL_RESOLUTION
            or len(points) != len(layers)
        ):
            raise AssertionError(f"{source_curve.name}: temporary Curve shaping contract changed")

        maximum_width = max(boundary_widths)
        assert_close(data.bevel_depth, maximum_width * 0.5)
        for point_index, (point, section) in enumerate(zip(points, sections)):
            if section["kind"] == "POINT":
                adjacent_index = adjacent_regular_index(sections, point_index)
                expected_radius = (
                    sections[adjacent_index]["shape_span_local"]
                    / maximum_width
                    * 0.015
                )
            else:
                expected_radius = section["shape_span_local"] / maximum_width
            assert_close(point.radius, expected_radius)
            if not math.isfinite(point.tilt):
                raise AssertionError(f"{source_curve.name}: generated a non-finite Tilt")

        for index, (ring, point, section) in enumerate(
            zip(evaluated_rings(temporary_curve), points, sections)
        ):
            expected_span = (
                sections[adjacent_regular_index(sections, index)]["shape_span_local"]
                * 0.015
                if section["kind"] == "POINT"
                else section["shape_span_local"]
            )
            assert_close(
                ring_span(ring),
                expected_span,
                message=f"{source_curve.name}: evaluated width mismatch at section {index}",
            )
            normal = Vector(section["shape_normal_local"]).normalized()
            bulge = ring_bulge(ring, point.co.xyz)
            if bulge.dot(normal) <= ORIENTATION_TOLERANCE:
                raise AssertionError(
                    f"{source_curve.name}: HALF bulge/front mismatch at section {index}: "
                    f"dot={bulge.dot(normal)}"
                )

        return boundary_widths
    finally:
        remove_temporary_curve(temporary_curve)
        bm.free()


def main():
    args = parse_args()
    if args.autosave:
        requested = Path(args.autosave).expanduser().resolve()
        if not requested.is_file():
            raise AssertionError(f"Autosave does not exist: {requested}")
        bpy.ops.wm.open_mainfile(filepath=str(requested), load_ui=False)

    source_path = Path(bpy.data.filepath).resolve()
    if (
        not source_path.is_file()
        or source_path.suffix.lower() != ".blend"
        or "autosave" not in source_path.name.lower()
    ):
        raise AssertionError("Run this verifier only against an X autosave .blend")
    before_size = source_path.stat().st_size
    before_mtime = source_path.stat().st_mtime_ns
    before_hash = sha256(source_path)

    hair_obj = bpy.data.objects.get(args.hair)
    if hair_obj is None or hair_obj.type != "MESH":
        raise AssertionError(f"Expected Mesh object {args.hair!r} was not found")
    stored_sets = find_stored_layer_sets(hair_obj)
    primary = [entry for entry in stored_sets if len(entry[1]) == 8]
    secondary = [entry for entry in stored_sets if len(entry[1]) == 7]
    if len(primary) != 1:
        raise AssertionError(f"Expected one audited 8-layer Hair1 set, found {len(primary)}")

    character_designer = load_source_addon()
    results = []
    primary_widths = validate_layer_set(
        character_designer,
        hair_obj,
        primary[0][0],
        primary[0][1],
        EXPECTED_PRIMARY_WIDTHS,
    )
    results.append((primary[0][0].name, primary_widths))
    if secondary:
        if len(secondary) != 1:
            raise AssertionError(f"Expected at most one 7-layer Hair1 set, found {len(secondary)}")
        secondary_widths = validate_layer_set(
            character_designer,
            hair_obj,
            secondary[0][0],
            secondary[0][1],
            EXPECTED_SECONDARY_WIDTHS,
        )
        results.append((secondary[0][0].name, secondary_widths))

    after_size = source_path.stat().st_size
    after_mtime = source_path.stat().st_mtime_ns
    after_hash = sha256(source_path)
    if (
        after_size != before_size
        or after_mtime != before_mtime
        or after_hash != before_hash
    ):
        raise AssertionError("The read-only verifier changed the autosave file")

    result_text = "; ".join(
        f"{name}: {len(widths)} widths "
        f"[{', '.join(f'{width:.6f}' for width in widths)}]"
        for name, widths in results
    )
    print(
        "PASS real Hair1 autosave:",
        result_text,
        "ROUND/HALF, v3 front Tilt, adjacent-relative 0.015 tip, no save",
    )


if __name__ == "__main__":
    main()
