"""QA-only actual Body collision experiment; never production graph acceptance.

Run a serial factory background child with caller-isolated TEMP/TMP:
  --background --factory-startup --disable-autoexec --threads 1 --python <file>
  -- --output <fresh Validation directory> --render
Only abrupt_stop, 60 forward frames, once. No bake/reset/public modes after
the experimental collision collection is assigned. No artist/source writes.
"""

import argparse
import json
from pathlib import Path
import sys
import time
import traceback
from types import SimpleNamespace

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import diagnose_skin_transfer as diag
qa, skirt, physics = diag.qa, diag.skirt, diag.physics
from character_designer import body_original_mode as original, skirt_motion_tuning as tuning

ARTIST = Path(r"D:\Blender\Projects\Character\X\X.blend")
FRAMES = (1,7,25,30)


def require(condition,message):
    if not condition: raise RuntimeError(message)


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=ARTIST)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--source")
    parser.add_argument("--render",action="store_true")
    parser.add_argument("--body-vertex-limit",type=int,default=100000)
    parser.add_argument("--triangle-pair-limit",type=int,default=2000)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    args.input,args.output = args.input.resolve(),args.output.resolve()
    require(args.input == ARTIST.resolve() and args.input.is_file(),"Only the saved X.blend is allowed")
    require(args.output.is_relative_to(diag.VALIDATION) and args.output != diag.VALIDATION,
            "Use a separate unique owned Validation output")
    require(1000 <= args.body_vertex_limit and 1 <= args.triangle_pair_limit <= 20000,"Invalid budgets")
    require(not (args.output/"experimental_body_collision.json").exists()
            and not (args.output/"Cosha_Dress_QA_experimental_body_collision.blend").exists(),"Output is not fresh")
    return args


def manifest():
    values = diag.source_manifest()
    values[str(Path(__file__))] = qa.file_state(Path(__file__))
    return values


def prepare_copy(source,rig,record,protection,report):
    """Reuse the public preparation route in validate_real_dress.main, once."""
    scene = bpy.context.scene
    scene.tool_settings.use_keyframe_insert_auto = False
    skirt._activate(bpy.context,rig,"POSE")
    owner = rig.get(skirt.ORIGINAL_DISPLAY_OWNER_KEY)
    if original.active(rig) or owner:
        if isinstance(owner,bpy.types.Object) and owner.type == "ARMATURE" and original.active(owner):
            skirt._activate(bpy.context,owner,"POSE")
        qa.public_switch(bpy.ops.character_designer.body_original_mode,action="CONTROLS")
        skirt._activate(bpy.context,rig,"POSE")
    skirt._require_controls_for_setup(source)
    if record.get("physics"): physics.validate_physics(source)
    require(protection.verify()["success"],"Public Controls changed protected raw assets")
    relevant = [rig,source,source.data.shape_keys]
    relevant.extend(bpy.data.objects.get(name) for name in record.get("owned_objects",()))
    report["author_animation_backup"] = qa.backup_animation(scene,relevant,protection.action_refs)
    qa.public_switch(bpy.ops.character_designer.body_ik_fk_switch,mode="FK")
    record = skirt.read_record(source)
    if not record.get("physics"):
        physics.add_physics(bpy.context,source)
        report["physics_added_to_qa_copy"] = True
    record,rig,proxy,cloth = physics.validate_physics(source)
    report["profile_before_experiment"] = tuning.initialize(source,capability="BOTH" if report.get("physics_added_to_qa_copy") else None)
    tuning.apply(bpy.context,(source,),mode="AUTOMATIC")
    scene.frame_start,scene.frame_end = 1,60
    cloth.point_cache.frame_start,cloth.point_cache.frame_end,cloth.point_cache.frame_step = 1,60,1
    cloth.point_cache.use_disk_cache = False
    report["pre_experiment_reset"] = physics.reset_simulation(bpy.context,source)
    legs,axes,height = qa.body_inputs(rig,record)
    action = qa.author_case("abrupt_stop",rig,legs,axes,qa.pose_channels(rig),rig.matrix_basis.copy(),height,60)
    report["qa_action"] = {"name":action.name,"sha256":qa.digest(qa.action_content(action))}
    scene.frame_set(0)
    record,rig,proxy,cloth = physics.validate_physics(source)
    return record,rig,proxy,cloth


def key_channels(keys):
    return None if keys is None else {"relative":keys.use_relative,"eval_time":keys.eval_time,
        "values":{key.name:{"value":key.value,"mute":key.mute} for key in keys.key_blocks}}


def copied_parameters(owner):
    # Evaluation timings/readonly runtime identity are not copied settings.
    return {name:value for name,value in qa.simple_rna(owner).items()
            if not owner.bl_rna.properties[name].is_readonly}


def clone_body(body,rig,record,collection,report):
    """Native raw Rest mesh copy plus its original skin/Subsurf, no refitting."""
    for owner in (body,body.data,body.data.shape_keys):
        if owner is None: continue
        require(owner.library is None and owner.override_library is None,"Linked/override Body data is unsupported")
        animation = owner.animation_data
        require(animation is None or (animation.action is None and not animation.nla_tracks and not animation.drivers),
                "Body Object/Mesh/Key animation or drivers are unsupported; none are disabled")
    require(body.mode == "OBJECT" and not body.constraints and not body.show_only_shape_key,"Unsupported Body edit/constraint/key-pin state")
    require(body.parent is None or (body.parent == rig and body.parent_type == "OBJECT"),"Unsupported Body parenting")
    keys = body.data.shape_keys
    require(keys is None or keys.use_relative,"Absolute Shape Keys are unsupported")
    mods = list(body.modifiers)
    require([item.type for item in mods] in (["ARMATURE"],["ARMATURE","SUBSURF"]),"Only native Armature then optional Subsurf is supported")
    skin = mods[0]
    require(all(item.show_viewport and item.show_render for item in mods) and skin.object == rig
            and skin.use_vertex_groups and not skin.use_bone_envelopes and not skin.vertex_group and not skin.use_multi_modifier,
            "Unsupported native Body skin semantics")
    owned = set(record["shared"]["names"])
    feedback = {group.index for group in body.vertex_groups if group.name in owned}
    require(not any(weight.group in feedback and weight.weight > 0 for vertex in body.data.vertices for weight in vertex.groups),
            "Body weights refer to generated Dress bones; collider feedback is refused")
    clone = body.copy()
    clone.name = "QA Actual Body Collision"
    clone.data = body.data.copy()
    collection.objects.link(clone)
    clone.hide_render = True
    clone.hide_set(False)
    clone["CD_QA_ExperimentalBodyCollision"] = True
    require(clone.data != body.data,"Body mesh copy is not independent")
    require(keys is None or (clone.data.shape_keys is not None and clone.data.shape_keys != keys),"Body Key copy is not independent")
    raw = qa.digest(qa.raw_mesh_content(body))
    require(qa.digest(qa.raw_mesh_content(clone)) == raw and key_channels(clone.data.shape_keys) == key_channels(keys),
            "Native Body copy changed Rest mesh, weights or static keys")
    require(diag.json_content([copied_parameters(item) for item in clone.modifiers]) == diag.json_content([copied_parameters(item) for item in mods]),
            "Native copied Body modifier parameters differ")
    report.update(original=body.name,clone=clone.name,raw_rest_mesh_sha256=raw,static_keys=key_channels(keys),
        original_modifiers=[qa.simple_rna(item) for item in mods],copied_modifier_parameters=[copied_parameters(item) for item in clone.modifiers],
        preserve_volume=skin.use_deform_preserve_volume,
        parent=body.parent.name if body.parent else None,matrix_world=diag.matrix(body.matrix_world),
        definition="Independent native raw Rest mesh/Key copy; original Armature/weights/Subsurf stack preserved, no posed-mesh double skin")
    clone.modifiers.new("QA Actual Body Collision","COLLISION")
    templates = [bpy.data.objects[name].collision for name in record["physics"]["colliders"]]
    require(all(diag.json_content(copied_parameters(item)) == diag.json_content(copied_parameters(templates[0])) for item in templates),
            "Old collider settings differ; no arbitrary Body collision settings are selected")
    copied = {}
    for prop in templates[0].bl_rna.properties:
        if prop.identifier == "rna_type" or prop.is_readonly or prop.type not in {"BOOLEAN","INT","FLOAT","ENUM"}: continue
        value = getattr(templates[0],prop.identifier)
        if prop.is_array: value = list(value)
        setattr(clone.collision,prop.identifier,value)
        copied[prop.identifier] = value
    report["collision_settings_copied_from_all_equal_old3"] = copied
    return clone


def measured_frame(args,source,rig,proxy,cloth,record,body,clone,frame):
    graph = bpy.context.evaluated_depsgraph_get()
    cage,final = diag.mesh_snapshot(proxy,graph),diag.mesh_snapshot(source,graph)
    actual,copied = diag.mesh_snapshot(body,graph),diag.mesh_snapshot(clone,graph)
    require(len(actual["points"]) == len(copied["points"]) and actual["faces"] == copied["faces"],"Body clone evaluated topology differs")
    delta = max(((a-b).length for a,b in zip(actual["points"],copied["points"])),default=0.)
    require(delta <= 1.e-8,"Body clone does not match actual native evaluated Body")
    require(qa.finite(cage["points"]) and qa.finite(final["points"]),"Nonfinite simulated mesh")
    waist = source.vertex_groups[record["controls"]["waist"]].index
    require(any(final["weights"]),"Actual Dress weight layer is unavailable")
    final["free_indices"] = [index for index,weights in enumerate(final["weights"])
        if next((item["weight"] for item in weights if item["index"] == waist),0.) < .999]
    bounds = diag.framing(rig,record,graph)
    roles = {name:layer for chain in record["chains"] for layer in ("manual","phys","def") for name in chain[layer]}
    roles[record["controls"]["waist"]] = "waist"
    meters = bpy.context.scene.unit_settings.scale_length
    epsilon = max(1.e-8,record["fit"]["height_world"]*1.e-6)
    body_result,_mesh = diag.body_diagnostics(body,graph,final,bounds,args,meters,roles,epsilon)
    pin = proxy.vertex_groups.get(cloth.settings.vertex_group_mass)
    require(pin is not None,"Actual native Cloth pin group is unavailable")
    cage["free_indices"] = [index for index,weights in enumerate(cage["weights"])
        if next((item["weight"] for item in weights if item["index"] == pin.index),0.) < .999]
    cloth_body,_mesh = diag.body_diagnostics(body,graph,cage,bounds,args,meters,roles,epsilon)
    item = {"frame":frame,"cloth_vertices":len(cage["points"]),"final_vertices":len(final["points"]),
        "body_clone_actual_max_delta_world":delta,"body_clone_evaluated_geometry_exact":True,
        "old3_owned_colliders":diag.collider_diagnostics(final,cage,record,graph,meters,roles,epsilon),
        "actual_registered_body":body_result,"actual_registered_body_vs_cloth":cloth_body,
        "cloth_free_definition":{"native_pin_group":pin.name,"maximum_fully_pinned_weight_excluded":.999},
        "cloth_world":[diag.vector(point) for point in cage["points"]],
        "final_world":[diag.vector(point) for point in final["points"]],"final_actual_weights":final["weights"]}
    if args.render and frame == 25:
        item["render"] = diag.native_render(SimpleNamespace(frame=frame,output=args.output),final,actual,bounds)
    return item


def main(args):
    isolation = qa.require_isolated_background()
    require(Path(diag.character_designer.__file__).resolve().is_relative_to(diag.REPOSITORY/"addons"),"Canonical import proof failed")
    args.output.mkdir(parents=True,exist_ok=True)
    path = args.output/"experimental_body_collision.json"
    candidate = args.output/"Cosha_Dress_QA_experimental_body_collision.blend"
    started = time.perf_counter()
    report = {"success":False,"production_effect_accepted":False,"canonical_full_graph_pass":False,
        "purpose":"QA-only old3 plus exact actual Body collider diagnostic", "artist_operation":False,
        "isolation":isolation,"artist_before":qa.file_state(args.input),"code_before":manifest(),
        "frames":[],"errors":[],"post_experimental_cache_reset_bake_or_public_mode_calls":[],
        "body_inside_outside_claim":False,"render_requested":args.render,"simulation_frames":60,"simulation_passes":1}
    report["body_clone_geometry_comparison_frames"] = list(FRAMES)
    report["render_focus_frame"] = 25
    protection = None
    try:
        diag.character_designer.register()
        require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(args.input),load_ui=False,use_scripts=False),"Artist copy open failed")
        protection = qa.Protection()
        report["original_assets_before"] = protection.summary()
        source,rig,record = qa.owned_source(args.source)
        report["artist_cache_preflight"] = qa.saved_cache_preflight(source,record)
        require(report["artist_cache_preflight"]["allowed"],report["artist_cache_preflight"].get("reason","Unsafe artist cache"))
        for index,action in enumerate(protection.action_refs): bpy.context.scene[f"CD_QA_AuthorAction_{index:04d}"] = action
        report["initial_owned_save"] = qa.save_candidate(candidate,args.input)
        record,rig,proxy,cloth = prepare_copy(source,rig,record,protection,report)
        body,report["registered_body_status"] = qa.registered_body(bpy.context,rig,args)
        require(body is not None,"Actual registered Body proof/budget failed")
        old_collection = cloth.collision_settings.collection
        require(len(record["physics"]["colliders"]) == 3 and not cloth.point_cache.is_baked,"Expected unbaked old3 baseline")
        report["frozen_record"] = record
        report["frozen_record_raw"] = source.get(skirt.RECORD_KEY)
        report["canonical_graph_proved_before_experiment"] = True
        report["native_settings_before_experiment"] = {"cloth":qa.simple_rna(cloth.settings),"collision":qa.simple_rna(cloth.collision_settings)}
        collection = bpy.data.collections.new("QA Experimental old3 plus Actual Body")
        bpy.context.scene.collection.children.link(collection)
        report["body_clone"] = {}
        clone = clone_body(body,rig,record,collection,report["body_clone"])
        for name in record["physics"]["colliders"]: collection.objects.link(bpy.data.objects[name])
        exact = set(record["physics"]["colliders"]+[clone.name])
        require(set(collection.objects.keys()) == exact and not collection.children,"Experimental collection is not exact")
        cloth.collision_settings.collection = collection
        report["experimental_graph"] = {"old_collection":old_collection.name,"new_collection":collection.name,
            "exact_members":sorted(exact),"canonical_validator_intentionally_not_called":True,
            "declaration":"Collision pointer intentionally differs from frozen canonical record; diagnostic only, no unlink/relink or production proof"}
        bpy.context.scene["CD_QA_ExperimentalGraph"] = json.dumps(report["experimental_graph"],ensure_ascii=False)
        for frame in range(1,61):
            bpy.context.scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            # Force the native Cloth result at every forward frame, exactly once.
            cage = diag.mesh_snapshot(proxy,graph)
            require(qa.finite(cage["points"]),"Cloth simulation is nonfinite")
            if frame in FRAMES: report["frames"].append(measured_frame(args,source,rig,proxy,cloth,record,body,clone,frame))
            if frame%10 == 0: print(f"QA ACTUAL BODY COLLISION {frame}/60",flush=True)
        require(source.get(skirt.RECORD_KEY) == report["frozen_record_raw"],"Experimental simulation changed source record")
        require(not cloth.point_cache.is_baked and not cloth.point_cache.use_disk_cache,"Experiment unexpectedly created sealed/disk cache")
        require(cloth.collision_settings.collection == collection and set(collection.objects.keys()) == exact,"Experimental collection changed")
        report["native_cache_after"] = qa.cache_state(cloth)
        report["saved_candidate"] = qa.save_candidate(candidate,args.input)
        report["candidate_file"] = qa.file_state(candidate)
        report["diagnostic_completed"] = len(report["frames"]) == len(FRAMES)
    except Exception:
        report["errors"].append(traceback.format_exc())
    finally:
        if protection is not None:
            report["original_asset_protection"] = protection.verify()
            report["original_assets_after"] = qa.Protection().summary()
        report["artist_after"],report["code_after"] = qa.file_state(args.input),manifest()
        report["artist_disk_exact"] = report["artist_after"] == report["artist_before"]
        report["code_exact"] = report["code_after"] == report["code_before"]
        rendered = [item["render"] for item in report["frames"] if "render" in item]
        report["success"] = report.get("diagnostic_completed",False) and not report["errors"] \
            and report.get("original_asset_protection",{}).get("success",False) and report["artist_disk_exact"] and report["code_exact"] \
            and (not args.render or len(rendered) == 1 and rendered[0]["success"])
        report["elapsed_seconds"] = time.perf_counter()-started
        conversions = []
        serializable = diag.json_content(report,conversions=conversions)
        serializable["json_mathutils_conversions"] = conversions
        path.write_text(json.dumps(serializable,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
        print("EXPERIMENTAL_BODY_COLLISION_REPORT="+str(path),flush=True)
        print("EXPERIMENTAL_BODY_COLLISION_COMPLETED="+str(report["success"]),flush=True)
    return report


if __name__ == "__main__":
    result = main(arguments())
    if not result["success"]: raise RuntimeError("QA Body collision experiment incomplete; inspect its JSON")
