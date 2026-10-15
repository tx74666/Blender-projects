"""Lightweight stored-RNA / unset-getter safety checks; no Blender import/run."""
import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_source_reference_witness_v5 as witness


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
    sys.modules["bpy"] = types.SimpleNamespace(types=types.SimpleNamespace(
        ID=NativeID, Object=Object, Action=Action, Key=Key, Mesh=Mesh))
    try:
        old = types.SimpleNamespace()
        before = witness.registered_source_witness(scene, old)
        assert before == witness.registered_source_witness(scene, old)
        assert before["scope"]["foreign_objects"][0]["name"] == "Hair1"
        assert any(".setup.assets[0].object" in row["path"] for row in before["reference_manifest"])
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
    finally:
        if original_bpy is None:
            sys.modules.pop("bpy", None)
        else:
            sys.modules["bpy"] = original_bpy


if __name__ == "__main__":
    main()
