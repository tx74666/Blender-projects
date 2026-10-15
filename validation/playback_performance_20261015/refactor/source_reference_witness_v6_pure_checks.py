"""Lightweight stored-RNA / unset-getter safety checks; no Blender import/run."""
import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_source_reference_witness_v6 as witness


class Property:
    def __init__(self, name, kind="STRING", fixed=None, default=None):
        self.identifier, self.type, self.fixed_type = name, kind, fixed
        self.is_runtime, self.is_array, self.is_readonly = False, False, False
        self.array_length, self.default = 0, default


class RNAType:
    def __init__(self, name, properties=(), base=None):
        self.identifier, self.properties, self.base = name, properties, base


class Struct:
    def __init__(self, rna, **fields):
        self.bl_rna, self._raw, self._set_fields = rna, {}, set(fields)
        self.__dict__.update(fields)

    def as_pointer(self):
        return id(self)

    def items(self):
        return self._raw.items()

    def is_property_set(self, name):
        return name in self._set_fields


class NativeID(Struct):
    def __init__(self, rna, name, **fields):
        super().__init__(rna, **fields)
        self.name_full = self.name = name
        self.library, self.session_uid = None, id(self)


class Object(NativeID):
    pass


class Action(NativeID):
    pass


class Key(NativeID):
    pass


class Mesh(NativeID):
    pass


def main():
    group_type = RNAType("PropertyGroup")
    object_type = RNAType("Object", [Property("location", "FLOAT"), Property("data", "POINTER")])
    hair = Object(object_type, "Hair1", location=(0.0, 0.0, 0.0), data=None,
                  type="EMPTY", users_scene=(), users_collection=(), active_shape_key=None, active_shape_key_index=0)
    asset_type = RNAType("Asset", [Property("object", "POINTER"), Property("role", "ENUM", default="CLOTHING")], group_type)
    asset = Struct(asset_type, object=hair, role="HAIR")
    setup_type = RNAType("Setup", [Property("assets", "COLLECTION", asset_type)], group_type)
    setup = Struct(setup_type, assets=[asset])
    scene_type = RNAType("Scene", [Property("setup", "POINTER", setup_type)])
    scene = NativeID(scene_type, "source", setup=setup, objects=())
    original_bpy = sys.modules.get("bpy")
    class _PropertyDeferred:
        def __init__(self, function, **keywords):
            self.function, self.keywords = function, keywords
    def StringProperty():
        pass
    def IntProperty():
        pass
    native_props = types.SimpleNamespace(_PropertyDeferred=_PropertyDeferred,
                                        StringProperty=StringProperty, IntProperty=IntProperty)
    sys.modules["bpy"] = types.SimpleNamespace(types=types.SimpleNamespace(
        ID=NativeID, Object=Object, Action=Action, Key=Key, Mesh=Mesh), props=native_props)
    try:
        old = types.SimpleNamespace()
        before = witness.registered_source_witness(scene, old)
        assert before == witness.registered_source_witness(scene, old)
        assert before["scope"]["foreign_objects"][0]["name"] == "Hair1"
        assert any(".setup.assets[0].object" in row["path"] for row in before["reference_manifest"])
        class DuplicateNameCollection:
            def __iter__(self):
                return iter([asset, asset2])
            def items(self):
                raise AssertionError("RNA collection.items/name getter must not be invoked")
        asset2 = Struct(asset_type, object=hair, role="CLOTHING")
        setup.assets = DuplicateNameCollection()
        rows = witness.Reader(NativeID).rna(setup, "setup")["properties"]["assets"]
        assert [row["properties"]["role"] for row in rows] == ["HAIR", "CLOTHING"]
        duplicate_proof = witness.registered_source_witness(scene, old)
        paths = {row["path"] for row in duplicate_proof["reference_manifest"]}
        assert any(path.endswith(".assets[0].object") for path in paths)
        assert any(path.endswith(".assets[1].object") for path in paths)
        setup.assets = [asset]

        def never_get(_owner):
            raise AssertionError("Declared computed source getter must not be invoked")
        def never_set(_owner, _value):
            raise AssertionError("Declared setter must not be invoked")
        class ComputedGroup(Struct):
            __annotations__ = {"computed": _PropertyDeferred(StringProperty, get=never_get),
                               "transformed": _PropertyDeferred(StringProperty, get_transform=never_get),
                               "set_only": _PropertyDeferred(StringProperty, set=never_set)}
            @property
            def computed(self):
                return never_get(self)
            @property
            def transformed(self):
                return never_get(self)
            @property
            def set_only(self):
                return never_get(self)
        computed_type = RNAType("ComputedGroup", [Property("computed"), Property("transformed"), Property("set_only")], group_type)
        computed = ComputedGroup(computed_type)
        computed._set_fields.update({"computed", "transformed", "set_only"})
        computed._raw["computed"] = "preserved raw backing"
        computed_reader = witness.Reader(NativeID)
        computed_state = computed_reader.rna(computed, "computed")
        assert computed_state["custom_properties"]["computed"] == "preserved raw backing"
        assert all(row["mode"] == "computed_declaration_and_raw_no_getter" for row in computed_reader.registered_field_observations)
        assert all("computed_registered_field" in row for row in computed_state["properties"].values())
        class WrongFactory(ComputedGroup):
            __annotations__ = {"computed": _PropertyDeferred(IntProperty, get=never_get)}
        invalid = WrongFactory(computed_type)
        invalid._set_fields.update({"computed", "transformed", "set_only"})
        try:
            witness.Reader(NativeID).rna(invalid, "invalid")
        except witness.SourceReferenceWitnessError:
            pass
        else:
            raise AssertionError("Mismatched nearest callback factory was admitted")
        hair.location = (1.0, 0.0, 0.0)
        changed = witness.registered_source_witness(scene, old)
        assert before["components"]["external_payload:Object:Hair1"] != changed["components"]["external_payload:Object:Hair1"]
        hair.location, asset.role = (0.0, 0.0, 0.0), "CLOTHING"
        assert before["components"]["registered:Scene:source"] != witness.registered_source_witness(scene, old)["components"]["registered:Scene:source"]

        class UnsetOwner(Struct):
            @property
            def unset_setup(self):
                raise AssertionError("Unset pointer getter must never be invoked")

        unset = UnsetOwner(RNAType("Owner", [Property("unset_setup", "POINTER", setup_type)]))
        unset_state = witness.Reader(NativeID).rna(unset, "unset")
        assert unset_state["property_set_bits"]["unset_setup"] is False
        assert "unset_registered_field" in unset_state["properties"]["unset_setup"]

        class MutatingGroup(Struct):
            @property
            def first(self):
                self._set_fields.add("second")
                return "read"

        mutating_type = RNAType("MutatingGroup", [Property("first"), Property("second")], group_type)
        mutating = MutatingGroup(mutating_type)
        mutating._set_fields.add("first")
        try:
            witness.Reader(NativeID).rna(mutating, "mutating")
        except witness.SourceReferenceWitnessError:
            pass
        else:
            raise AssertionError("A getter changed another hidden registered field without rejection")

        class RawMutatingGroup(Struct):
            # A lookalike deferred annotation cannot exempt a real getter.
            __annotations__ = {"stored": types.SimpleNamespace(function=StringProperty, keywords={"get": never_get})}
            @property
            def stored(self):
                self._raw["changed"] = 1
                return "read"

        raw_mutating = RawMutatingGroup(RNAType("RawMutatingGroup", [Property("stored")], group_type))
        raw_mutating._set_fields.add("stored")
        try:
            witness.Reader(NativeID).rna(raw_mutating, "raw_mutating")
        except witness.SourceReferenceWitnessError:
            pass
        else:
            raise AssertionError("A nested getter changed its own raw properties without rejection")
        assert scene._raw == setup._raw == asset._raw == hair._raw == {}
        class ShapeKeyReference(Struct):
            @property
            def data(self):
                raise AssertionError("Reference ShapeKey geometry must not be traversed")

        shape_type = RNAType("ShapeKey", [Property("name"), Property("data", "COLLECTION")])
        shape_reference = ShapeKeyReference(shape_type, name="Basis")
        object_type.properties.append(Property("active_shape_key", "POINTER", shape_type))
        hair.active_shape_key = shape_reference
        witness.registered_source_witness(scene, old)

        class BulkPoints:
            def __len__(self):
                return 1
            def foreach_get(self, name, values):
                assert name == "co" and len(values) == 3
                for index, coordinate in enumerate((0.0, 0.5, 1.0)):
                    values[index] = coordinate

        block = Struct(RNAType("ShapeKey", [Property("data", "COLLECTION"), Property("relative_key", "POINTER"), Property("name")]),
                       data=BulkPoints(), relative_key=None, name="Basis")
        keys = Key(RNAType("Key", [Property("key_blocks", "COLLECTION"), Property("reference_key", "POINTER"), Property("use_relative", "BOOLEAN")]),
                   "Keys", key_blocks=[block], reference_key=shape_reference, use_relative=True)
        key_payload = witness._key_payload(keys, witness.Reader(NativeID), "Keys")
        assert key_payload["reference_key"]["name"] == "Basis"
        assert set(key_payload["blocks"][0]["coordinates"]) == {"count", "width", "kind", "sha256"}
        json.dumps(before, allow_nan=False)
        print(json.dumps({"stored_RNA_reference_found": True, "foreign_state_mutation_detected": True,
                          "stored_enum_mutation_detected": True, "repeat_exact": True,
                          "unset_pointer_getter_not_invoked": True, "hidden_set_bit_write_rejected": True,
                          "nested_raw_write_rejected": True, "normal_witness_did_not_write_storage": True,
                          "object_active_key_geometry_not_traversed": True,
                          "key_reference_geometry_not_traversed_bulk_coords_only": True}, indent=2))
        print(json.dumps({"duplicate_collection_rows_and_order_preserved": True,
                          "native_collection_items_name_getter_not_called": True,
                          "ordinal_native_ID_reference_paths_retained": True,
                          "computed_get_transform_set_only_getters_not_called": True,
                          "computed_raw_and_setbits_retained": True,
                          "nearest_mismatched_deferred_factory_rejected": True}, indent=2))
    finally:
        if original_bpy is None:
            sys.modules.pop("bpy", None)
        else:
            sys.modules["bpy"] = original_bpy


if __name__ == "__main__":
    main()
