"""Read-only registered RNA and external Object source protection.

No registrations, operators, evaluations or writes occur here. Native ID
references keep exact pointer/session identity. Geometry and all large values
are hashed in memory; report payloads contain only components and scope.
"""
from array import array
import hashlib
import json
import marshal
import struct
import sys


class SourceReferenceWitnessError(RuntimeError):
    pass


def object_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def native_identity(value):
    if value is None:
        return None
    return {"rna_type": value.bl_rna.identifier, "name": value.name_full,
            "pointer": int(value.as_pointer()), "session_uid": getattr(value, "session_uid", None),
            "library": value.library.filepath if value.library else None}


def _is_property_group_type(rna_type):
    while rna_type is not None:
        if rna_type.identifier == "PropertyGroup":
            return True
        rna_type = rna_type.base
    return False


def registered_properties(owner):
    """Discover descriptors without invoking registered owner-field getters."""
    return tuple(prop for prop in owner.bl_rna.properties
                 if prop.identifier != "rna_type" and
                 (getattr(prop, "is_runtime", False) or
                  (prop.type in {"POINTER", "COLLECTION"} and
                   _is_property_group_type(prop.fixed_type))))


def callback_declaration(owner, prop):
    """Read Python registration metadata, never the owner's property getter.

    RNA is_property_set() is true for computed properties even without backing
    storage. Only an explicit deferred callback declaration selects this
    route; unknown/native getters retain the ordinary guarded read behavior.
    """
    name = prop.identifier
    for cls in type(owner).__mro__:
        annotations = vars(cls).get("__annotations__", {})
        if name not in annotations:
            continue
        deferred = annotations[name]
        native_props = getattr(sys.modules.get("bpy"), "props", None)
        deferred_type = getattr(native_props, "_PropertyDeferred", None)
        if deferred_type is None or type(deferred) is not deferred_type:
            return None
        keywords = getattr(deferred, "keywords", None)
        factory = getattr(deferred, "function", None)
        if not isinstance(keywords, dict) or not callable(factory):
            return None
        if "attr" in keywords and keywords["attr"] != name:
            raise SourceReferenceWitnessError("Deferred registration attribute does not match RNA identifier: " + name)
        factory_name = {"STRING": "StringProperty", "ENUM": "EnumProperty", "POINTER": "PointerProperty",
                        "COLLECTION": "CollectionProperty", "BOOLEAN": "BoolProperty",
                        "INT": "IntProperty", "FLOAT": "FloatProperty"}.get(prop.type)
        if factory_name is None:
            return None
        if getattr(prop, "is_array", False) and prop.type in {"BOOLEAN", "INT", "FLOAT"}:
            factory_name = factory_name.replace("Property", "VectorProperty")
        if factory is not getattr(native_props, factory_name, None):
            raise SourceReferenceWitnessError("Deferred property factory does not match RNA type: " + name)
        # A set-only callback also removes PROP_IDPROPERTY in native RNA;
        # is_property_set is therefore not evidence of stored getter state.
        callbacks = {key: keywords[key] for key in ("get", "get_transform", "set", "set_transform")
                     if keywords.get(key) is not None}
        if not callbacks:
            return None
        if not all(callable(callback) for callback in callbacks.values()):
            raise SourceReferenceWitnessError("Invalid declared callback: " + name)
        def declaration(callback):
            code = getattr(callback, "__code__", None)
            return {"module": getattr(callback, "__module__", None),
                    "qualname": getattr(callback, "__qualname__", getattr(callback, "__name__", None)),
                    "python_code_sha256": hashlib.sha256(marshal.dumps(code)).hexdigest() if code is not None else None}
        return {"declaring_type": cls.__module__ + "." + cls.__qualname__,
                "registered_attribute": keywords.get("attr", name),
                "property_factory": declaration(factory),
                "callbacks": {key: declaration(callback) for key, callback in callbacks.items()}}
    return None


class Reader:
    """One witness pass; native ID references stop RNA traversal cycles."""
    # Native bookkeeping changes when private references are allocated, even
    # when original payloads are untouched. It is not original asset state.
    OMIT_ID_FIELDS = frozenset({"rna_type", "id_data", "original", "is_evaluated",
                                "users", "tag", "is_updated", "is_updated_data",
                                "is_updated_transform", "name_full", "session_uid"})

    def __init__(self, id_type):
        self.id_type = id_type
        self.references = {}
        self.reference_paths = []
        self.active = {}
        self.fields_read = 0
        self.registered_field_observations = []

    def default_descriptor(self, prop):
        result = {"identifier": prop.identifier, "type": prop.type,
                  "is_array": getattr(prop, "is_array", False),
                  "array_length": getattr(prop, "array_length", 0),
                  "is_runtime": getattr(prop, "is_runtime", False),
                  "is_readonly": getattr(prop, "is_readonly", False)}
        if prop.type in {"POINTER", "COLLECTION"}:
            fixed = prop.fixed_type
            result["fixed_RNA_type"] = fixed.identifier if fixed else None
        # These are RNA definition metadata, not a getter on source storage.
        for name in ("default", "default_array"):
            if hasattr(prop, name):
                result[name] = self.value(getattr(prop, name), "RNA_descriptor." + prop.identifier + "." + name)
        return result

    def ref(self, value, path):
        pointer = int(value.as_pointer())
        self.references[pointer] = value
        self.reference_paths.append({"path": path, "id": native_identity(value)})
        return {"native_ID": native_identity(value)}

    def value(self, value, path, *, typed_rna=True):
        if value is None or isinstance(value, (bool, int, str)):
            return value
        if isinstance(value, float):
            return {"float_hex": value.hex()}
        if isinstance(value, self.id_type):
            return self.ref(value, path)
        if isinstance(value, bytes):
            return {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
        if isinstance(value, (set, frozenset)):
            return sorted((self.value(item, path + "{item}", typed_rna=typed_rna) for item in value),
                          key=lambda item: json.dumps(item, sort_keys=True, allow_nan=False))
        if typed_rna and hasattr(value, "bl_rna"):
            return self.rna(value, path)
        if hasattr(value, "items"):
            return {str(key): self.value(item, path + "." + str(key), typed_rna=typed_rna) for key, item in value.items()}
        try:
            return [self.value(item, path + "[" + str(index) + "]", typed_rna=typed_rna) for index, item in enumerate(value)]
        except TypeError as error:
            raise SourceReferenceWitnessError("Unsupported source value at " + path + ": " + type(value).__name__) from error

    def raw(self, owner, path):
        try:
            items = owner.items()
        except TypeError as error:
            if str(error) != "bpy_struct.items(): this type doesn't support IDProperties":
                raise
            return None
        return {str(key): self.value(item, path + "[" + json.dumps(str(key)) + "]", typed_rna=False) for key, item in items}

    def rna(self, value, path, properties=None):
        pointer = int(value.as_pointer())
        token = (value.bl_rna.identifier, pointer)
        if token in self.active:
            return {"active_RNA_cycle_to": self.active[token]}
        self.active[token] = path
        try:
            props = tuple(value.bl_rna.properties if properties is None else properties)
            is_group = _is_property_group_type(value.bl_rna)
            registered_names = {prop.identifier for prop in props if prop.identifier not in self.OMIT_ID_FIELDS and (
                is_group or getattr(prop, "is_runtime", False) or
                (prop.type in {"POINTER", "COLLECTION"} and _is_property_group_type(prop.fixed_type)))}
            set_bits_before = {name: bool(value.is_property_set(name)) for name in registered_names}
            raw_before = self.raw(value, path + ".custom")
            result = {"rna_type": value.bl_rna.identifier, "properties": {}, "property_set_bits": {}}
            for prop in props:
                name = prop.identifier
                if name in self.OMIT_ID_FIELDS:
                    continue
                try:
                    registered = name in registered_names
                    if registered:
                        was_set = set_bits_before[name]
                        result["property_set_bits"][name] = was_set
                        computed = callback_declaration(value, prop)
                        observation = {"path": path + "." + name, "is_property_set": was_set,
                                       "mode": "computed_declaration_and_raw_no_getter" if computed is not None else
                                               "stored_typed_read" if was_set else "unset_descriptor_no_getter"}
                        self.registered_field_observations.append(observation)
                        if computed is not None:
                            observation["callback_declaration"] = computed
                            result["properties"][name] = {"computed_registered_field": self.default_descriptor(prop),
                                                          "callback_declaration": computed}
                            continue
                        if not was_set:
                            result["properties"][name] = {"unset_registered_field": self.default_descriptor(prop)}
                            continue
                    observed = getattr(value, name)
                    # Native IDs are references; non-ID RNA pointers and
                    # sequence collections are fully read without assignment.
                    if prop.type == "COLLECTION":
                        # Native collection.items() uses member.name as key;
                        # duplicate/empty names must retain order and identity.
                        result["properties"][name] = [self.value(item, path + "." + name + "[" + str(index) + "]")
                                                       for index, item in enumerate(observed)]
                    else:
                        result["properties"][name] = self.value(observed, path + "." + name)
                    self.fields_read += 1
                    if registered and bool(value.is_property_set(name)) != was_set:
                        raise SourceReferenceWitnessError("Typed getter changed registered source set status: " + path + "." + name)
                except BaseException as error:
                    raise SourceReferenceWitnessError("Cannot read source RNA " + path + "." + name) from error
            raw_after = self.raw(value, path + ".custom")
            if set_bits_before != {name: bool(value.is_property_set(name)) for name in registered_names}:
                raise SourceReferenceWitnessError("Typed getter changed registered source set status: " + path)
            if object_hash(raw_before) != object_hash(raw_after):
                raise SourceReferenceWitnessError("Typed getter changed nested source raw storage: " + path)
            result["custom_properties"] = raw_after
            return result
        finally:
            self.active.pop(token)


def _bulk(collection, name, kind, width=1):
    values = array(kind, [0]) * (len(collection) * width)
    collection.foreach_get(name, values)
    return {"count": len(collection), "width": width, "kind": kind,
            "sha256": hashlib.sha256(values.tobytes()).hexdigest()}


def _mesh_payload(mesh, reader, path, old):
    """Raw foreign mesh payload; never depsgraph/evaluated_get/to_mesh."""
    parts = {"vertices": _bulk(mesh.vertices, "co", "f", 3),
             "vertex_normals": _bulk(mesh.vertices, "normal", "f", 3),
             "edges": _bulk(mesh.edges, "vertices", "i", 2),
             "loop_vertices": _bulk(mesh.loops, "vertex_index", "i"),
             "loop_edges": _bulk(mesh.loops, "edge_index", "i"),
             "polygon_loop_start": _bulk(mesh.polygons, "loop_start", "i"),
             "polygon_loop_total": _bulk(mesh.polygons, "loop_total", "i"),
             "polygon_material_index": _bulk(mesh.polygons, "material_index", "i"),
             "polygon_smooth": _bulk(mesh.polygons, "use_smooth", "b"),
             "polygon_normals": _bulk(mesh.polygons, "normal", "f", 3)}
    weights = hashlib.sha256()
    for vertex in mesh.vertices:
        weights.update(struct.pack("<II", vertex.index, len(vertex.groups)))
        for group in vertex.groups:
            weights.update(struct.pack("<If", group.group, group.weight))
    parts["weights"] = weights.hexdigest()
    parts["attributes"] = [
        {"name": attribute.name, "data_type": attribute.data_type, "domain": attribute.domain,
         "fields": old.oracle().attribute_fields(attribute.data)} for attribute in mesh.attributes]
    parts["uv_layers"] = [
        {"name": layer.name, "active_render": layer.active_render, "active_clone": layer.active_clone,
         "fields": old.oracle().attribute_fields(layer.data)} for layer in mesh.uv_layers]
    parts["uv_active_index"] = mesh.uv_layers.active_index
    parts["corner_normals"] = _bulk(mesh.corner_normals, "vector", "f", 3)
    parts["normal_metadata"] = [mesh.normals_domain, mesh.has_custom_normals]
    # Geometry arrays were covered above; all remaining native RNA state and
    # references are retained. These exclusions do not omit material pointers,
    # animation_data, shape_keys or registered/custom properties.
    excluded = {"vertices", "edges", "loops", "polygons", "attributes", "uv_layers",
                "corner_normals", "vertex_normals", "polygon_normals", "loop_triangles",
                "vertex_creases", "edge_creases", "color_attributes", "skin_vertices",
                "vertex_colors", "face_maps"}
    properties = [prop for prop in mesh.bl_rna.properties if prop.identifier not in excluded]
    parts["rna"] = reader.rna(mesh, path, properties)
    # Skin/color/crease values belong to attributes in current Blender. A
    # separate nonempty legacy skin collection must still be read explicitly.
    if hasattr(mesh, "skin_vertices"):
        parts["skin_vertices"] = reader.value(mesh.skin_vertices, path + ".skin_vertices")
    return parts


def _key_payload(keys, reader, path):
    properties = [prop for prop in keys.bl_rna.properties if prop.identifier not in {"key_blocks", "reference_key"}]
    reference = keys.reference_key
    result = {"rna": reader.rna(keys, path, properties), "blocks": [],
              "reference_key": {"name": reference.name, "pointer": int(reference.as_pointer())} if reference else None}
    for index, block in enumerate(keys.key_blocks):
        block_properties = [prop for prop in block.bl_rna.properties if prop.identifier not in {"data", "relative_key"}]
        result["blocks"].append({"index": index, "rna": reader.rna(block, path + ".key_blocks[" + str(index) + "]", block_properties),
                                 "coordinates": _bulk(block.data, "co", "f", 3),
                                 "relative_key_name": block.relative_key.name if block.relative_key else None,
                                 "relative_key_pointer": int(block.relative_key.as_pointer()) if block.relative_key else None})
    return result


def registered_source_witness(scene, old):
    """Protect catalog/foreign original data outside ordinary scene output proof.

    Native ID pointers are not normalized to clones. An added/removed reference,
    source RNA field, external Object or payload component changes the digest.
    """
    import bpy
    reader = Reader(bpy.types.ID)
    components, scope = {}, {"registered_owners": [], "foreign_objects": [], "payload_ids": [],
                              "identity_only_dependency_ids": []}
    source_objects = tuple(scene.objects)
    source_pointers = {int(obj.as_pointer()) for obj in source_objects}
    for owner in (scene,) + source_objects:
        path = owner.bl_rna.identifier + ":" + owner.name_full
        properties = registered_properties(owner)
        # Read raw storage before/after typed access to detect a getter that
        # unexpectedly mutates saved data. No setter/operator is invoked.
        before_raw = object_hash(reader.raw(owner, path + ".custom_before"))
        state = reader.rna(owner, path, properties)
        after_raw = object_hash(reader.raw(owner, path + ".custom_before"))
        if before_raw != after_raw:
            raise SourceReferenceWitnessError("Registered RNA getter changed raw source storage: " + path)
        components["registered:" + path] = object_hash(state)
        scope["registered_owners"].append({"id": native_identity(owner),
                                            "properties": [prop.identifier for prop in properties]})
    # Only referenced Objects outside the source Scene are payload roots.
    # Follow further Object references, data, Key and Action IDs; images,
    # materials/world/node groups remain exact reference identities here.
    # Their contents are not claimed by this narrowly scoped object witness.
    pending, done = [], set()
    def enqueue_references():
        for pointer, item in tuple(reader.references.items()):
            if pointer not in done and isinstance(item, bpy.types.Object) and pointer not in source_pointers:
                pending.append(item)
    enqueue_references()
    while pending:
        item = pending.pop()
        pointer = int(item.as_pointer())
        if pointer in done:
            continue
        done.add(pointer)
        path = item.bl_rna.identifier + ":" + item.name_full
        if isinstance(item, bpy.types.Object):
            object_properties = [prop for prop in item.bl_rna.properties if prop.identifier != "active_shape_key"]
            state = reader.rna(item, path, object_properties)
            active_key = item.active_shape_key
            state["active_shape_key"] = {"name": active_key.name, "pointer": int(active_key.as_pointer())} if active_key else None
            state["active_shape_key_index"] = int(item.active_shape_key_index)
            state["users_scene"] = [native_identity(value) for value in item.users_scene]
            state["users_collection"] = [native_identity(value) for value in item.users_collection]
            scope["foreign_objects"].append(native_identity(item))
            data = item.data
            if data is not None:
                pending.append(data)
            if item.type == "MESH":
                state["shape_keys"] = old.shape_keys_witness(item, {})
        elif isinstance(item, bpy.types.Mesh):
            state = _mesh_payload(item, reader, path, old)
        elif isinstance(item, bpy.types.Key):
            state = _key_payload(item, reader, path)
        else:
            state = reader.rna(item, path)
        components["external_payload:" + path] = object_hash(state)
        scope["payload_ids"].append(native_identity(item))
        # Actions/Keys plus data IDs directly attached to external objects are
        # protected as payloads, including all RNA FCurve/driver/NLA structures.
        for dependency in tuple(reader.references.values()):
            if isinstance(dependency, (bpy.types.Action, bpy.types.Key)) and int(dependency.as_pointer()) not in done:
                pending.append(dependency)
        enqueue_references()
    for pointer, item in reader.references.items():
        if pointer not in done and pointer not in source_pointers and item is not scene:
            scope["identity_only_dependency_ids"].append(native_identity(item))
    references = sorted(reader.reference_paths, key=lambda row: (row["path"], row["id"]["pointer"]))
    components["registered_and_external_ID_references"] = object_hash(references)
    scope["foreign_objects"].sort(key=lambda row: (row["rna_type"], row["name"], row["pointer"]))
    scope["payload_ids"].sort(key=lambda row: (row["rna_type"], row["name"], row["pointer"]))
    scope["identity_only_dependency_ids"].sort(key=lambda row: (row["rna_type"], row["name"], row["pointer"]))
    field_observations = sorted(reader.registered_field_observations, key=lambda row: row["path"])
    components["registered_field_set_status_and_read_mode"] = object_hash(field_observations)
    scope.update(native_RNA_fields_read=reader.fields_read, native_ID_reference_rows=len(references),
                 all_stored_noncomputed_registered_reads_completed=True,
                 unset_registered_fields_not_read=sum(not row["is_property_set"] for row in field_observations),
                 declared_computed_fields_not_read=sum(row["mode"] == "computed_declaration_and_raw_no_getter" for row in field_observations),
                 registered_field_observations=field_observations,
                 native_ID_bookkeeping_omitted=sorted(Reader.OMIT_ID_FIELDS),
                 no_evaluated_foreign_geometry=True,
                 limits="Exact stored noncomputed registered Scene/Object fields, ordinal native collections, unset-field set-status/schema/default markers and explicitly declared computed-field schema/callback metadata plus raw storage without getter invocation; raw foreign Object/data/Key/Action payload. Unset/computed getter outputs are unclaimed. Callback closure/global runtime values are not separately traversed. Other native IDs are reference identities only. No foreign evaluated output, image pixels, material/node content or viewport proof.")
    return {"schema": "x.registered-source-and-external-object-protection/2",
            "sha256": object_hash(components), "components": components,
            "scope": scope, "reference_manifest": references}
