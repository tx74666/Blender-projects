"""Read-only probe for front-flush offsets on the real Hair1 autosave."""

import bmesh
import bpy
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addons" / "character_designer"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_addon():
    name = "character_designer_offset_probe"
    spec = importlib.util.spec_from_file_location(
        name,
        ADDON / "__init__.py",
        submodule_search_locations=[str(ADDON)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def vec(v):
    return tuple(round(float(x), 9) for x in v)


def evaluated_rings(curve):
    evaluated = curve.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        vertices = tuple(vertex.co.copy() for vertex in mesh.vertices)
    finally:
        evaluated.to_mesh_clear()
    count = len(curve.data.splines[0].points)
    size = len(vertices) // count
    return tuple(vertices[i * size : (i + 1) * size] for i in range(count))


def main():
    args = sys.argv[sys.argv.index("--") + 1 :]
    source_path = Path(args[0]).resolve()
    before = (source_path.stat().st_size, source_path.stat().st_mtime_ns, sha256(source_path))
    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    cd = load_addon()

    hair = bpy.data.objects["Hair1"]
    matrix = hair.matrix_world
    linear = matrix.to_3x3()
    print("SOURCE", hair.name, "matrix", tuple(round(float(x), 9) for row in matrix for x in row))
    print("SCALE", vec(matrix.to_scale()), "det", round(float(linear.determinant()), 9))

    curves = sorted(
        (
            obj
            for obj in bpy.data.objects
            if obj.type == "CURVE"
            and obj.get("character_designer_source") == hair.name
            and obj.get("character_designer_layer_vertices")
        ),
        key=lambda obj: obj.name,
    )
    print("CURVES", len(curves))
    for stored in curves:
        layers = tuple(tuple(x) for x in json.loads(stored["character_designer_layer_vertices"]))
        point_count = sum(len(spline.points) for spline in stored.data.splines)
        valid_indices = all(
            isinstance(index, int) and 0 <= index < len(hair.data.vertices)
            for layer in layers
            for index in layer
        )
        print(
            "CURVE_TAG_AUDIT", stored.name,
            "selected", stored.select_get(),
            "points", point_count,
            "layers", len(layers),
            "indices_valid", valid_indices,
            "source", stored.get("character_designer_source"),
            "generator", stored.get("character_designer_generator"),
            "metadata", stored.get("character_designer_metadata_version"),
            "has_sections", bool(stored.get("character_designer_cross_sections")),
        )
        if not valid_indices:
            continue
        bm = bmesh.new()
        try:
            bm.from_mesh(hair.data)
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            bm.normal_update()
            centers = tuple(
                sum((bm.verts[index].co for index in layer), Vector()) / len(layer)
                for layer in layers
            )
            metadata = cd._build_cross_section_metadata(hair, bm, layers, centers, "CLOSED")
            depth, radii, tilts = cd._curve_profile_parameters(metadata)
            bands = cd._front_band_descriptors(bm, layers)
            print("CURVE", stored.name, "points", len(layers), "generator", stored.get("character_designer_generator"))
            print(" TAGS source", stored.get("character_designer_source"), "metadata", stored.get("character_designer_metadata_version"), "has_sections", bool(stored.get("character_designer_cross_sections")))
            print(" MATRIX_MATCH", all(abs(stored.matrix_world[r][c] - hair.matrix_world[r][c]) < 1e-8 for r in range(4) for c in range(4)))
            existing_points = tuple(point.co.xyz.copy() for spline in stored.data.splines for point in spline.points)
            if len(existing_points) == len(centers):
                deltas = tuple((point - center).length for point, center in zip(existing_points, centers))
                print(
                    " CENTER_MATCH max_delta", round(float(max(deltas, default=0.0)), 9),
                    "all", [round(float(value), 9) for value in deltas],
                )
            else:
                print(" CENTER_MATCH point_count_mismatch")
            temporary = None
            computed_fronts = []
            computed_normals = []
            computed_bulges = []
            if stored.name in {"Hair1_Centerline", "Hair1_Centerline.001"}:
                temporary = cd._create_centerline_object(
                    bpy.context, hair, layers, centers, metadata
                )
                raw_extents = []
                shifted_extents = []
                for ring, point, center, section, radius in zip(
                    evaluated_rings(temporary),
                    temporary.data.splines[0].points,
                    centers,
                    metadata["sections"],
                    radii,
                ):
                    normal = Vector(section["shape_normal_local"]).normalized()
                    raw_extents.append(max((vertex - center).dot(normal) for vertex in ring))
                # The per-section offset is filled below; defer shift audit until
                # after the section loop by retaining the temporary object.
            for index, (layer, center, section, radius) in enumerate(zip(layers, centers, metadata["sections"], radii)):
                normal = Vector(section["shape_normal_local"]).normalized()
                bulge = depth * radius
                plane_distances = []
                edge_distances = []
                faces = []
                for band_index in (index - 1, index):
                    if band_index < 0 or band_index >= len(bands):
                        continue
                    descriptor = bands[band_index]
                    if descriptor is None:
                        continue
                    face = descriptor["face"]
                    faces.append(face.index)
                    layer_set = set(layer)
                    same = cd._face_same_layer_edge(face, layer_set) if len(layer) > 1 else None
                    if same:
                        pair = same[0]
                        midpoint = (bm.verts[pair[0]].co + bm.verts[pair[1]].co) * 0.5
                        edge_distances.append((midpoint - center).dot(normal))
                    denom = face.normal.dot(normal)
                    if abs(denom) > 1e-9:
                        plane_distances.append(face.normal.dot(face.calc_center_median() - center) / denom)

                if section["kind"] == "POINT":
                    front_distance = 0.0
                    source = "TIP_POINT"
                elif edge_distances:
                    front_distance = sum(edge_distances) / len(edge_distances)
                    source = "FRONT_EDGE"
                elif plane_distances:
                    front_distance = sum(plane_distances) / len(plane_distances)
                    source = "FACE_PLANE"
                else:
                    front_distance = float("nan")
                    source = "NONE"
                offset = bulge - front_distance
                new_center = center - normal * offset
                computed_fronts.append(front_distance)
                computed_normals.append(normal.copy())
                computed_bulges.append(bulge)
                # World displacement is exact affine transformation of the local offset.
                world_displacement = linear @ (-normal * offset)
                world_shape_step = linear @ normal
                # True world normal to the source local normal under arbitrary object scale.
                world_plane_normal = linear.inverted().transposed() @ normal
                if world_plane_normal.length:
                    world_plane_normal.normalize()
                print(
                    " SECTION", index,
                    "kind", section["kind"],
                    "width", round(float(section["shape_span_local"]), 9),
                    "bulge", round(float(bulge), 9),
                    "front", round(float(front_distance), 9),
                    "offset", round(float(offset), 9),
                    "normal", vec(normal),
                    "center", vec(center),
                    "new", vec(new_center),
                    "world_shift", vec(world_displacement),
                    "world_shift_len", round(float(world_displacement.length), 9),
                    "world_bulge_dir_dot_plane_normal", round(float(world_shape_step.normalized().dot(world_plane_normal)), 9),
                    "faces", faces,
                    "front_source", source,
                    "edge_d", [round(float(x), 9) for x in edge_distances],
                    "plane_d", [round(float(x), 9) for x in plane_distances],
                )
                if temporary is not None:
                    temporary.data.splines[0].points[index].co.xyz = new_center
            if temporary is not None:
                for ring, center, section in zip(
                    evaluated_rings(temporary), centers, metadata["sections"]
                ):
                    normal = Vector(section["shape_normal_local"]).normalized()
                    shifted_extents.append(
                        max((vertex - center).dot(normal) for vertex in ring)
                    )
                print(
                    " EVALUATED_FRONT raw", [round(float(x), 9) for x in raw_extents],
                    "shifted", [round(float(x), 9) for x in shifted_extents],
                )
                # Solve the small coupling introduced because moving adjacent
                # centers changes Curve tangents and therefore its HALF frame.
                offsets = [
                    bulge - front
                    for bulge, front in zip(computed_bulges, computed_fronts)
                ]
                for _iteration in range(30):
                    solved_centers = tuple(
                        center - normal * offset
                        for center, normal, offset in zip(centers, computed_normals, offsets)
                    )
                    solved_tangents = cd._center_tangents(solved_centers)
                    next_offsets = []
                    for normal, tangent, bulge, front in zip(
                        computed_normals,
                        solved_tangents,
                        computed_bulges,
                        computed_fronts,
                    ):
                        target = cd._project_to_normal_plane(normal, tangent)
                        next_offsets.append(bulge * target.dot(normal) - front)
                    if max(abs(a - b) for a, b in zip(offsets, next_offsets)) < 1e-12:
                        offsets = next_offsets
                        break
                    offsets = next_offsets
                solved_centers = tuple(
                    center - normal * offset
                    for center, normal, offset in zip(centers, computed_normals, offsets)
                )
                solved_tangents = cd._center_tangents(solved_centers)
                solved_metadata = copy.deepcopy(metadata)
                for section, tangent in zip(solved_metadata["sections"], solved_tangents):
                    section["tangent_local"] = cd._vector_json(tangent)
                _solved_depth, _solved_radii, solved_tilts = cd._curve_profile_parameters(solved_metadata)
                for point, center, tilt in zip(
                    temporary.data.splines[0].points, solved_centers, solved_tilts
                ):
                    point.co.xyz = center
                    point.tilt = tilt
                solved_extents = []
                for ring, center, normal in zip(
                    evaluated_rings(temporary), centers, computed_normals
                ):
                    solved_extents.append(
                        max((vertex - center).dot(normal) for vertex in ring)
                    )
                print(
                    " EVALUATED_FRONT_SOLVED expected",
                    [round(float(x), 9) for x in computed_fronts],
                    "actual", [round(float(x), 9) for x in solved_extents],
                    "offsets", [round(float(x), 9) for x in offsets],
                    "max_error", round(
                        float(max(abs(a - b) for a, b in zip(computed_fronts, solved_extents))),
                        12,
                    ),
                )
                data = temporary.data
                bpy.data.objects.remove(temporary, do_unlink=True)
                if data.users == 0:
                    bpy.data.curves.remove(data)
        finally:
            bm.free()

    after = (source_path.stat().st_size, source_path.stat().st_mtime_ns, sha256(source_path))
    print("FILE_UNCHANGED", before == after, "hash", before[2])
    if before != after:
        raise AssertionError("Autosave changed")


if __name__ == "__main__":
    main()
