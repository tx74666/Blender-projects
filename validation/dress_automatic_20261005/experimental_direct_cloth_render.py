"""Unreleased fixed-Basis visual/effect QA: direct Cloth positions before Subsurf.

Fresh factory background only. Frozen actual800 Cloth/Body/416tracker/same input,
with the original source ARMATURE/SUBSURF and original source metrics untouched.
A metadata-cleared object copy shares the artist raw mesh read-only and has
ARMATURE -> owned exact-index NODES SetPosition -> copied original SUBSURF.
Only the independent actual800 Cloth is sampled, using native RELATIVE Object
Info and unclamped POINT/vector Sample Index with the native original Index.
This is absolute Cloth output, not a manual/Shape Key delta overlay, not export,
not Original/mode compatibility and not production acceptance.
"""

import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import bpy

HERE = Path(__file__).resolve().parent
BASE_SHA256 = "188fd43531133a42aa7c12cf689a3dcb0fc5e1bfbfb2bc2f9527f83fa6ce5bae"
if hashlib.sha256((HERE/"experimental_actual_surface.py").read_bytes()).hexdigest() != BASE_SHA256:
    raise RuntimeError("Frozen actual-surface dependency differs")
sys.path.insert(0, str(HERE))
import experimental_actual_surface as base

diag, qa, bodyqa, skirt, require = base.diag, base.qa, base.bodyqa, base.skirt, base.require
ORIGINAL_GUARD, ORIGINAL_PROBE = base.dress_contract, base.make_skin_probe
ORIGINAL_REMOVE, ORIGINAL_MEASURE, ORIGINAL_MANIFEST = base.remove_skin_probe, base.measured_frame, base.manifest
STATE = {"installed":False, "raw_probe":None}
NODE_TYPES = {"Input":"NodeGroupInput", "Output":"NodeGroupOutput", "Cloth":"GeometryNodeObjectInfo",
    "Position":"GeometryNodeInputPosition", "Index":"GeometryNodeInputIndex", "Sample":"GeometryNodeSampleIndex",
    "Set Position":"GeometryNodeSetPosition"}
LINKS = [("Input","Geometry","Set Position","Geometry"), ("Cloth","Geometry","Sample","Geometry"),
    ("Position","Position","Sample","Value"), ("Index","Index","Sample","Index"),
    ("Sample","Value","Set Position","Position"), ("Set Position","Geometry","Output","Geometry")]
SAMPLE_WORLD_LIMIT = 1.e-6
SAMPLE_METRES_LIMIT = 1.e-6
BODY_TRIANGLE_SAMPLES = (4009,4032,4034,4035,10360,10384,10385,10390,10391,10407)


def strict_rna(owner):
    """Writable settings including native enum/string properties lacking is_array."""
    result = {}
    for prop in owner.bl_rna.properties:
        name = prop.identifier
        if name == "rna_type" or prop.is_readonly or prop.type == "COLLECTION":
            continue
        value = getattr(owner, name)
        if prop.type == "POINTER":
            result[name] = qa.id_name(value)
        elif getattr(prop,"is_array",False):
            result[name] = diag.json_content(list(value))
        elif isinstance(value,(str,bool,int,float)) or value is None:
            result[name] = value
        elif isinstance(value,set):
            result[name] = sorted(value)
        else:
            raise RuntimeError("Unsupported writable RNA in exact diagnostic proof: "+name)
    return result


def properties(owner):
    return qa.custom_content({key:owner[key] for key in owner.keys()})


def source_signature(source):
    return qa.digest({"raw_mesh_keys_UV_weights":qa.raw_mesh_content(source), "key_channels":bodyqa.key_channels(source.data.shape_keys),
        "all_raw_stored_nonposition_attributes":attribute_content(source.data),
        "source_properties":properties(source), "data_properties":properties(source.data),
        "modifiers":[strict_rna(m) for m in source.modifiers], "parent":qa.id_name(source.parent),
        "parent_type":source.parent_type, "parent_bone":source.parent_bone,
        "parent_inverse":diag.matrix(source.matrix_parent_inverse), "basis":diag.matrix(source.matrix_basis)})


def attribute_content(mesh):
    attributes = []
    domain_counts = {"POINT":len(mesh.vertices),"EDGE":len(mesh.edges),"FACE":len(mesh.polygons),"CORNER":len(mesh.loops)}
    for attribute in mesh.attributes:
        if attribute.name == "position":
            continue
        require(attribute.domain in domain_counts and len(attribute.data) == domain_counts[attribute.domain],
                "Unknown native attribute domain/count: "+attribute.name)
        values = [strict_rna(item) for item in attribute.data]
        require(all(values), "Cannot read complete native attribute values: "+attribute.name)
        attributes.append({"name":attribute.name,"domain":attribute.domain,"data_type":attribute.data_type,
            "count":len(attribute.data),"native_value_types":sorted({item.bl_rna.identifier for item in attribute.data}),
            "internal":getattr(attribute,"is_internal",None),"required":getattr(attribute,"is_required",None),"values":values})
    return sorted(attributes,key=lambda item:item["name"])


def mesh_layers(obj,graph):
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=graph)
    try:
        return {"vertices":len(mesh.vertices), "edges":[tuple(edge.vertices) for edge in mesh.edges],
            "faces":[(tuple(face.vertices),face.material_index,face.use_smooth) for face in mesh.polygons],
            "loops":[(loop.vertex_index,loop.edge_index) for loop in mesh.loops],
            "UV":[(layer.name,layer.active_render,[tuple(item.uv) for item in layer.data]) for layer in mesh.uv_layers],
            "weights":[sorted((item.group,item.weight) for item in vertex.groups) for vertex in mesh.vertices],
            "groups":[(group.name,group.index,group.lock_weight) for group in obj.vertex_groups],
            "materials":[qa.id_name(material) for material in mesh.materials],
            "all_stored_nonposition_attributes":attribute_content(mesh),
            "derived_fields_excluded_from_attribute_equality":["position","evaluated vertex/face/corner normal caches"],
            "stored_custom_normals_not_exempted":True,"has_custom_normals":mesh.has_custom_normals}
    finally:
        evaluated.to_mesh_clear()


def socket_content(socket):
    settings = strict_rna(socket)
    return {"name":socket.name, "identifier":socket.identifier, "type":socket.bl_idname,
        "default":settings.get("default_value"), "settings":settings}


def node_contract(group):
    return {"type":group.bl_idname, "properties":properties(group), "settings":strict_rna(group),
        "interface":[{"name":item.name,"item_type":item.item_type,"in_out":getattr(item,"in_out",None),
            "socket_type":getattr(item,"socket_type",None),"settings":strict_rna(item)} for item in group.interface.items_tree],
        "nodes":[{"name":node.name,"type":node.bl_idname,"settings":strict_rna(node),
            "inputs":[socket_content(socket) for socket in node.inputs],
            "outputs":[socket_content(socket) for socket in node.outputs]} for node in group.nodes],
        "links":[(link.from_node.name,link.from_socket.identifier,link.to_node.name,link.to_socket.identifier,
            link.is_valid,link.is_muted) for link in group.links]}


def verify_nodes():
    group, actual = STATE["group"], STATE["actual"]
    require(group.library is None and group.override_library is None and group.animation_data is None
            and group.bl_idname == "GeometryNodeTree", "Only independent nonanimated native Geometry Nodes allowed")
    sockets = list(group.interface.items_tree)
    require(len(sockets) == 2 and all(item.item_type == "SOCKET" and item.name == "Geometry"
            and item.socket_type == "NodeSocketGeometry" for item in sockets)
            and {item.in_out for item in sockets} == {"INPUT","OUTPUT"}, "Extra graph interface inputs/panels are forbidden")
    require({node.name:node.bl_idname for node in group.nodes} == NODE_TYPES and len(group.nodes) == 7,
            "Only the seven identified position-only nodes are allowed")
    require(all(not node.mute and node.parent is None for node in group.nodes) and group.nodes["Output"].is_active_output,
            "No muted nodes or alternate Group Output may bypass the identified graph")
    observed = [(link.from_node.name,link.from_socket.name,link.to_node.name,link.to_socket.name) for link in group.links]
    require(sorted(observed) == sorted(LINKS) and all(link.is_valid and not link.is_muted for link in group.links),
            "Exact Index/Position links changed, or graph gained an additional input")
    info, sample, position = group.nodes["Cloth"],group.nodes["Sample"],group.nodes["Set Position"]
    require(info.transform_space == "RELATIVE" and info.inputs["Object"].default_value == actual
            and not info.inputs["Object"].is_linked and not info.inputs["As Instance"].is_linked
            and not info.inputs["As Instance"].default_value, "Object Info must read exact actual Cloth, in native output-relative space")
    require(sample.data_type == "FLOAT_VECTOR" and sample.domain == "POINT" and not sample.clamp,
            "Sample Index must use exact vector Point-domain indices without clamping")
    require(position.inputs["Selection"].default_value and not position.inputs["Selection"].is_linked
            and not position.inputs["Offset"].is_linked and tuple(position.inputs["Offset"].default_value) == (0.,0.,0.),
            "Only absolute sampled Position may modify geometry; selection/offset inputs must be fixed")
    require(qa.digest(node_contract(group)) == STATE["node_hash"], "Complete owned node graph/interface/defaults/settings changed")


def verify_wrapper():
    source, wrapper, raw = STATE["source"],STATE["wrapper"],STATE["raw_probe"]
    require(source_signature(source) == STATE["source_hash"], "Wrapper lifetime changed artist source/keys/UV/weights/modifiers/properties")
    require(wrapper != source and wrapper.data == source.data and wrapper.data != STATE["actual"].data
            and wrapper.animation_data is None and not wrapper.constraints,
            "Wrapper must have independent object identity and share only protected artist raw data read-only")
    require(properties(wrapper) == STATE["wrapper_properties"] and skirt.RECORD_KEY not in wrapper
            and skirt.OWNER_KEY not in wrapper and skirt.RIG_KEY not in wrapper,
            "QA output must not forge a canonical source UUID/record/Rig registration")
    require([m.type for m in wrapper.modifiers] == ["ARMATURE","NODES","SUBSURF"]
            and wrapper.modifiers[1] == STATE["modifier"] and STATE["modifier"].node_group == STATE["group"]
            and [strict_rna(wrapper.modifiers[i]) for i in (0,2)] == STATE["source_modifiers"],
            "Wrapper must retain exact copied artist Armature/Subsurf settings")
    require(strict_rna(STATE["modifier"]) == STATE["modifier_parameters"]
            and properties(STATE["modifier"]) == STATE["modifier_properties"], "Position modifier gained extra settings/inputs")
    for obj in (wrapper,raw) if raw is not None else (wrapper,):
        require(obj.parent == source.parent and obj.parent_type == source.parent_type and obj.parent_bone == source.parent_bone
                and diag.matrix(obj.matrix_parent_inverse) == diag.matrix(source.matrix_parent_inverse)
                and diag.matrix(obj.matrix_basis) == diag.matrix(source.matrix_basis)
                and diag.matrix(obj.matrix_world) == diag.matrix(source.matrix_world), "Native copy lost exact source object coordinate frame")
        require([(g.index,g.name,g.lock_weight) for g in obj.vertex_groups] == STATE["groups"],
                "Copied object changed native vertex-group index mapping")
        require(obj.name not in STATE["cloth"].collision_settings.collection.objects, "Output/helper cannot become a collision input")
    if raw is not None:
        require(raw.data == source.data and raw.animation_data is None and not raw.constraints
                and properties(raw) == STATE["raw_properties"] and skirt.RECORD_KEY not in raw and skirt.OWNER_KEY not in raw
                and [m.type for m in raw.modifiers] == ["ARMATURE","NODES"]
                and strict_rna(raw.modifiers[0]) == STATE["source_modifiers"][0]
                and raw.modifiers[1].node_group == STATE["group"]
                and strict_rna(raw.modifiers[1]) == STATE["modifier_parameters"]
                and properties(raw.modifiers[1]) == STATE["modifier_properties"], "Exact temporary raw output probe changed")
    verify_nodes()


def combined_guard(rig,record,source):
    if STATE["installed"]:
        verify_wrapper()
    # Wrapper/helper live outside the original contract; never normalize or relax original source/Rig fields.
    return ORIGINAL_GUARD(rig,record,source)


def make_group(actual):
    group = bpy.data.node_groups.new("QA Direct Actual Cloth Position","GeometryNodeTree")
    try:
        group.interface.new_socket(name="Geometry",in_out="INPUT",socket_type="NodeSocketGeometry")
        group.interface.new_socket(name="Geometry",in_out="OUTPUT",socket_type="NodeSocketGeometry")
        for name,kind in NODE_TYPES.items():
            node = group.nodes.new(kind)
            node.name = name
            node.mute = False
        group.nodes["Output"].is_active_output = True
        info,sample,position = group.nodes["Cloth"],group.nodes["Sample"],group.nodes["Set Position"]
        info.transform_space = "RELATIVE"
        info.inputs["Object"].default_value = actual
        info.inputs["As Instance"].default_value = False
        sample.data_type,sample.domain,sample.clamp = "FLOAT_VECTOR","POINT",False
        position.inputs["Selection"].default_value = True
        position.inputs["Offset"].default_value = (0.,0.,0.)
        for start,output,end,input_name in LINKS:
            group.links.new(group.nodes[start].outputs[output],group.nodes[end].inputs[input_name])
        group["CD_QA_DirectClothOutput"] = True
        return group
    except Exception:
        bpy.data.node_groups.remove(group)
        raise


def remove_outputs(source,report):
    STATE["installed"] = False
    for key in ("raw_probe","wrapper"):
        obj = STATE.get(key)
        if obj is not None:
            name = obj.name
            bpy.data.objects.remove(obj,do_unlink=True)
            require(name not in bpy.data.objects, "QA output rollback failed to remove its object")
            STATE[key] = None
    group = STATE.get("group")
    if group is not None:
        require(group.users == 0, "QA node group unexpectedly acquired an external user")
        bpy.data.node_groups.remove(group)
        STATE["group"] = None
    require(source.data.name in bpy.data.meshes and source_signature(source) == STATE["source_hash"],
            "Output rollback changed the protected artist data/keys/UV/weights/modifiers")
    report["rollback_all_owned_output_IDs_removed_source_exact"] = True


def install_output(source,actual,collection,probe,report):
    require(bpy.context.scene.frame_current == 0 and [m.type for m in source.modifiers] == ["ARMATURE","SUBSURF"],
            "Create owned output before frame1 from the exact artist modifier stack")
    require(source.animation_data is None and not source.constraints and not source.show_only_shape_key,
            "Object animation/constraints/key-only display are unsupported extra inputs")
    for owner in (source,source.data,source.data.shape_keys):
        if owner is None:
            continue
        animation = owner.animation_data
        require(owner.library is None and owner.override_library is None and (animation is None
                or (animation.action is None and not animation.nla_tracks and not animation.drivers)),
                "Source Object/Mesh/Key animation or drivers are unsupported; none are cleared or muted")
    keys = source.data.shape_keys
    require(keys is None or (keys.use_relative and all(key == keys.reference_key or key.mute or key.value == 0. for key in keys.key_blocks)),
            "Only the frozen inactive non-Basis Shape Keys fixture is supported; visible Key effects are not preserved by absolute Cloth output")
    STATE.update(source=source,actual=actual,cloth=next(m for m in actual.modifiers if m.type == "CLOTH"),
        source_hash=source_signature(source),source_modifiers=[strict_rna(m) for m in source.modifiers],
        groups=[(g.index,g.name,g.lock_weight) for g in source.vertex_groups],wrapper=None,raw_probe=None,group=None,report=report)
    group_names = {group.index:group.name for group in source.vertex_groups}
    require(all(item.group in group_names for vertex in source.data.vertices for item in vertex.groups),
            "Raw source weights contain an unregistered object group index")
    report["raw_source_native_groups"] = [(group.index,group.name,group.lock_weight) for group in source.vertex_groups]
    report["raw_source_native_weights800"] = [{"raw_vertex_index":vertex.index,
        "weights":[{"group_index":item.group,"group_name":group_names[item.group],"weight":item.weight} for item in vertex.groups]}
        for vertex in source.data.vertices]
    try:
        wrapper = source.copy()
        STATE["wrapper"] = wrapper
        wrapper.name = "QA Direct Cloth Render Output"
        collection.objects.link(wrapper)
        for key in list(wrapper.keys()):
            del wrapper[key]
        wrapper["CD_QA_DirectClothOutput"] = True
        wrapper["CD_QA_ArtistSource"] = source
        wrapper["CD_QA_Unreleased_NotExportCompatible"] = True
        group = make_group(actual)
        STATE["group"] = group
        modifier = wrapper.modifiers.new("QA Exact Index Actual Cloth Position","NODES")
        modifier.node_group = group
        wrapper.modifiers.move(2,1)
        modifier.is_active = False
        for copied_index,source_index in ((0,0),(2,1)):
            wrapper.modifiers[copied_index].is_active = STATE["source_modifiers"][source_index]["is_active"]
        raw = wrapper.copy()
        STATE["raw_probe"] = raw
        raw.name = "QA Temporary Direct Cloth Raw800 Probe"
        collection.objects.link(raw)
        for key in list(raw.keys()):
            del raw[key]
        raw["CD_QA_TemporaryRawOutputProbe"] = True
        raw["CD_QA_ArtistSource"] = source
        raw.modifiers.remove(raw.modifiers[2])
        raw.hide_render = True
        bpy.context.view_layer.update()
        STATE.update(modifier=modifier,modifier_parameters=strict_rna(modifier),modifier_properties=properties(modifier),
            wrapper_properties=properties(wrapper),raw_properties=properties(raw),node_hash=qa.digest(node_contract(group)))
        STATE["installed"] = True
        verify_wrapper()
        report.update(object=wrapper.name,temporary_raw_probe=raw.name,raw_shared_data=source.data.name,
            artist_mesh_shared_readonly=True,artist_ObjectUUID_and_record_not_copied=True,
            original_source_modifiers=STATE["source_modifiers"],owned_node_contract=node_contract(group),
            owned_node_contract_sha256=STATE["node_hash"],source_signature_sha256=STATE["source_hash"],
            original_guard_unchanged=True,subsurf_after_sample=True,unsupported="Absolute fixed Basis Cloth output overwrites visible manual/Original/Key deltas; this fixture refuses Object/Mesh/Key animation and active non-Basis Keys. Not production/export/mode compatibility.",
            primary_sources={"ObjectInfo":"https://raw.githubusercontent.com/blender/blender/blender-v5.1-release/source/blender/nodes/geometry/nodes/node_geo_object_info.cc",
                "SampleIndex":"https://raw.githubusercontent.com/blender/blender/blender-v5.1-release/source/blender/nodes/geometry/nodes/node_geo_sample_index.cc",
                "SetPosition":"https://raw.githubusercontent.com/blender/blender/blender-v5.1-release/source/blender/nodes/geometry/nodes/node_geo_set_position.cc"})
        raw_measurement(probe,bpy.context.evaluated_depsgraph_get(),report.setdefault("frame0_raw_proof",{}))
    except Exception:
        remove_outputs(source,report)
        raise


def make_probe(source,actual,collection,report):
    probe = ORIGINAL_PROBE(source,actual,collection,report)
    STATE.update(original_probe_name=probe.name,original_probe_pointer=probe.as_pointer(),original_probe_removed=False)
    try:
        report["direct_cloth_output"] = {}
        install_output(source,actual,collection,probe,report["direct_cloth_output"])
    except Exception:
        remove_original_once(probe,source,report)
        raise
    return probe


def raw_measurement(original_probe,graph,report):
    verify_wrapper()
    physical = diag.mesh_snapshot(STATE["actual"],graph)
    raw = diag.mesh_snapshot(STATE["raw_probe"],graph)
    require(len(physical["points"]) == len(raw["points"]) == 800 and qa.finite(physical["points"]) and qa.finite(raw["points"]),
            "Exact unclamped Sample Index requires two finite 800-point geometries")
    require(raw["faces"] == physical["faces"] and sorted(tuple(sorted(edge)) for edge in raw["edges"])
            == sorted(tuple(sorted(edge)) for edge in physical["edges"]), "Actual Cloth and output exact raw vertex/face connectivity differ")
    raw_layers,original_layers = mesh_layers(STATE["raw_probe"],graph),mesh_layers(original_probe,graph)
    require(raw_layers == original_layers, "Position-only output changed raw topology/indices/UV/materials/groups/weights/stored nonposition attributes")
    errors = [(a-b).length for a,b in zip(raw["points"],physical["points"])]
    meters = bpy.context.scene.unit_settings.scale_length
    report.update(raw_vertices=800,exact_index_mapping_and_layers_proved=True,no_clamp_or_nearest_or_index_rebuild=True,
        physical_connectivity_proof="Same indexed faces and complete undirected edge set; physical from_pydata edge storage order is not vertex-index mapping. Source-to-wrapper edges/loops remain exact ordered.",
        raw_vs_actual_point_max_world=max(errors),raw_vs_actual_point_max_m=max(errors)*meters,
        raw_vs_actual_point_rms_m=(sum(value*value for value in errors)/len(errors))**.5*meters,
        numerical_world_limit=SAMPLE_WORLD_LIMIT,numerical_m_limit=SAMPLE_METRES_LIMIT,
        raw_layers_sha256=qa.digest(raw_layers),raw800_world=[diag.vector(point) for point in raw["points"]])
    require(max(errors) <= SAMPLE_WORLD_LIMIT and max(errors)*meters <= SAMPLE_METRES_LIMIT,
            "Direct output did not equal actual Cloth by exact index; possible default-value/cycle/space error")
    return raw,physical


def visibility(obj):
    return [obj.hide_render,obj.hide_viewport,obj.hide_get()]


def measured_frame(args,source,rig,tracker,actual,cloth,record,body,clone,probe,frame):
    item = ORIGINAL_MEASURE(args,source,rig,tracker,actual,cloth,record,body,clone,probe,frame)
    graph = bpy.context.evaluated_depsgraph_get()
    original_skin = diag.mesh_snapshot(probe,graph)
    require(len(original_skin["points"]) == 800 and qa.finite(original_skin["points"]),
            "Original ARM-only raw skin measurement must remain finite exact800")
    item["raw_skin800_world"] = [diag.vector(point) for point in original_skin["points"]]
    detail = {"original_source_metrics_unchanged_and_separate":True,"wrapper":STATE["wrapper"].name,"raw_probe":STATE["raw_probe"].name}
    raw,physical = raw_measurement(probe,graph,detail.setdefault("raw800",{}))
    wrapper,final = STATE["wrapper"],diag.mesh_snapshot(STATE["wrapper"],graph)
    require(len(final["points"]) == 3040 and qa.finite(final["points"]), "Copied artist Subsurf output must be the proved finite 3040 vertices")
    final_layers,original_layers = mesh_layers(wrapper,graph),mesh_layers(source,graph)
    require(final_layers == original_layers, "Position-only wrapper changed final Subsurf topology/UV/materials/native weights/stored nonposition attributes")
    raw["free_indices"] = base.free_indices(raw,wrapper.vertex_groups[record["controls"]["waist"]])
    final["free_indices"] = base.free_indices(final,wrapper.vertex_groups[record["controls"]["waist"]])
    physical["free_indices"] = base.free_indices(physical,actual.vertex_groups[cloth.settings.vertex_group_mass])
    roles = {name:layer for chain in record["chains"] for layer in ("manual","phys","def") for name in chain[layer]}
    roles[record["controls"]["waist"]] = "waist"
    meters,bounds = bpy.context.scene.unit_settings.scale_length,diag.framing(rig,record,graph)
    epsilon = max(1.e-8,record["fit"]["height_world"]*1.e-6)
    raw_body,_ = diag.body_diagnostics(body,graph,raw,bounds,args,meters,roles,epsilon)
    final_body,body_mesh = diag.body_diagnostics(body,graph,final,bounds,args,meters,roles,epsilon)
    require(body_mesh is not None and all(index < len(body_mesh["triangles"]) for index in BODY_TRIANGLE_SAMPLES),
            "Registered evaluated Body triangle evidence is unavailable or out of range")
    body_vertices = sorted({index for triangle in BODY_TRIANGLE_SAMPLES for index in body_mesh["triangles"][triangle]})
    require(all(index < len(body_mesh["points"]) and index < len(body_mesh["weights"]) for index in body_vertices),
            "Evaluated Body triangle evidence references unavailable evaluated points/weights")
    item["evaluated_body_triangle_evidence"] = {"object":body_mesh["object"],
        "index_scope":"Native evaluated loop-triangle and evaluated vertex indices only; no raw-index correspondence inferred",
        "triangles":[{"evaluated_triangle_index":index,"evaluated_vertex_indices":body_mesh["triangles"][index]} for index in BODY_TRIANGLE_SAMPLES],
        "unique_evaluated_vertices":len(body_vertices),"prior_observed_unique_vertices":14,
        "vertices":[{"evaluated_vertex_index":index,"world":diag.vector(body_mesh["points"][index]),
            "native_evaluated_weights":body_mesh["weights"][index]} for index in body_vertices]}
    evaluated_rig = rig.evaluated_get(graph)
    item["evaluated_waist_evidence"] = {"rig_evaluated_matrix_world":diag.matrix(evaluated_rig.matrix_world),
        "native_rest_and_evaluated_pose":diag.bone_content(rig,evaluated_rig,record["controls"]["waist"])}
    colliders = diag.collider_diagnostics(final,physical,record,graph,meters,roles,epsilon)
    maximum = max(value["final_free"]["maximum_penetration_m"] for value in colliders.values())
    detail.update(final3040={"vertices":3040,"same_final_layers_sha256":qa.digest(final_layers),
        "world":[diag.vector(point) for point in final["points"]],"actual_registered_body":final_body,"old3_owned_colliders":colliders,
        "unchanged_2mm_diagnostic":{"maximum_penetration_m":maximum,"limit_m":base.FINAL_PENETRATION_LIMIT_M,
            "within_limit":maximum <= base.FINAL_PENETRATION_LIMIT_M,"production_acceptance":False}},
        raw800_vs_actual_registered_body=raw_body,open_body_unsigned_only=True,production_effect_accepted=False)
    if args.render and frame == 25:
        output = args.output/"direct_wrapper_render"
        require(not output.exists(), "Wrapper rendering must use a fresh separate PNG directory")
        output.mkdir()
        before = {obj.name:visibility(obj) for obj in (source,wrapper)}
        try:
            detail["render"] = diag.native_render(SimpleNamespace(frame=frame,output=output),final,body_mesh,bounds)
            detail["render"]["explicit_rendered_output"] = wrapper.name
            detail["render"]["method"] = "Frozen renderer uses temporary snapshot Mesh/Object/Scene, removed in finally; original source is never hidden or used as the wrapper render geometry."
        finally:
            after = {obj.name:visibility(obj) for obj in (source,wrapper)}
            detail["render_visibility"] = {"before":before,"after":after,"exact":after == before}
            require(after == before, "Wrapper rendering altered source/output visibility")
    item["direct_cloth_output"] = detail
    return item


def remove_original_once(probe,source,report):
    """Frozen removal exactly once, including a guard failure after native deletion."""
    name = STATE["original_probe_name"]
    if not STATE["original_probe_removed"]:
        current = bpy.data.objects.get(name)
        require(current is not None and current.as_pointer() == STATE["original_probe_pointer"] and current == probe,
                "Original disposable probe identity changed; refusing guessed cleanup")
        try:
            ORIGINAL_REMOVE(current,source,report)
        finally:
            if bpy.data.objects.get(name) is None:
                STATE["original_probe_removed"] = True
    require(STATE["original_probe_removed"] and bpy.data.objects.get(name) is None and source.data.name in bpy.data.meshes,
            "Original disposable probe remains, or its name was reused")
    require(report["source_properties_sha256"] == qa.digest(properties(source)) and
            report["source_data_properties_sha256"] == qa.digest(properties(source.data)),
            "Original probe cleanup changed protected source metadata")
    report["removed_before_candidate_save"] = True
    report["original_probe_native_removal_exactly_once"] = True


def remove_probe(probe,source,report):
    errors = []
    try:
        raw = STATE.get("raw_probe")
        if raw is not None:
            name = raw.name
            require(raw != source, "Refusing to remove artist source as an output probe")
            try:
                bpy.data.objects.remove(raw,do_unlink=True)
            finally:
                if bpy.data.objects.get(name) is None:
                    STATE["raw_probe"] = None
            require(name not in bpy.data.objects, "Temporary output probe cleanup did not remove the owned object")
            require(source_signature(source) == STATE["source_hash"],
                    "Temporary output-probe cleanup changed source data/keys/UV/weights/modifiers/properties")
            STATE["report"]["temporary_raw_probe_removed_before_candidate_save_source_exact"] = True
            verify_wrapper()
        require(STATE["raw_probe"] is None and source_signature(source) == STATE["source_hash"],
                "Temporary output cleanup/source proof failed on a repeated cleanup call")
    except Exception as exc:
        errors.append(exc)
    try:
        remove_original_once(probe,source,report)
    except Exception as exc:
        errors.append(exc)
    if errors:
        report.setdefault("cleanup_errors",[]).extend(type(exc).__name__+": "+str(exc) for exc in errors)
        raise RuntimeError("Owned diagnostic cleanup/guard failure: "+"; ".join(str(exc) for exc in errors)) from errors[0]


def manifest():
    values = ORIGINAL_MANIFEST()
    values[str(Path(__file__).resolve())] = qa.file_state(Path(__file__).resolve())
    return values


def output_completion(result,render_requested):
    frames = result.get("frames",[])
    details = [item.get("direct_cloth_output") for item in frames]
    frame_proof = [item.get("frame") for item in frames] == list(base.FRAMES) and len(details) == 4 and all(
        detail and detail.get("raw800",{}).get("exact_index_mapping_and_layers_proved")
        and detail.get("final3040",{}).get("vertices") == 3040 for detail in details)
    rendered = [detail["render"] for detail in details if detail and "render" in detail]
    render_proof = not render_requested or len(rendered) == 1 and rendered[0].get("success",False)
    cleanup = result.get("disposable_skin_probe",{}).get("direct_cloth_output",{}).get(
        "temporary_raw_probe_removed_before_candidate_save_source_exact",False) and STATE["raw_probe"] is None
    return {"four_frames_native_raw_and_final_proved":bool(frame_proof), "wrapper_render_complete":bool(render_proof),
        "raw_probe_cleanup_before_candidate_save_proved":bool(cleanup),
        "success":bool(frame_proof and render_proof and cleanup),
        "late_failure_policy":"Temporary raw output probe must be removed; owned wrapper/node group may remain solely in the independent failed QA candidate. Original artist assets and original source metrics are not converted to success."}


def main():
    base.dress_contract,base.make_skin_probe = combined_guard,make_probe
    base.remove_skin_probe,base.measured_frame,base.manifest = remove_probe,measured_frame,manifest
    args = base.arguments()
    result = base.main(args)
    result["original_source_diagnostic_success"] = result["success"]
    result["direct_output_completion"] = output_completion(result,args.render)
    result["success"] = bool(result["success"] and result["direct_output_completion"]["success"])
    if not result["direct_output_completion"]["success"]:
        result["errors"].append("Direct output native frame/render/temporary-probe completion proof failed; original source result remains separately recorded")
    result["purpose"] = "Unreleased direct fixed-Basis Cloth positions before copied Subsurf; original source/32-bone metrics separately preserved"
    result["frozen_actual_surface_sha256"] = BASE_SHA256
    result["production_effect_accepted"] = result["canonical_full_graph_pass"] = False
    result["manual_ShapeKeys_Original_modes_export_compatibility_proved"] = False
    result["limitations"].append("Direct absolute Cloth coordinates do not preserve manual/Original/Shape Key visible deltas. Source modifier/data is untouched; this owned QA wrapper is not an export-compatible runtime repair. Current coords-changing NODES export rejection remains unchanged.")
    conversions = []
    serializable = diag.json_content(result,conversions=conversions)
    serializable["json_mathutils_conversions"] = conversions
    output = Path(sys.argv[sys.argv.index("--output")+1]).resolve()/"experimental_actual_surface.json"
    output.write_text(json.dumps(serializable,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print("EXPERIMENTAL_DIRECT_CLOTH_RENDER_REPORT="+str(output),flush=True)
    require(result["success"], "Direct Cloth output diagnostic failed; see preserved report/candidate")
    return result


if __name__ == "__main__":
    main()
