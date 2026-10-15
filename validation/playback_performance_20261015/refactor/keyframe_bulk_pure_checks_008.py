"""Retain all prior source guards and test native-only bulk admission; no Blender."""
from array import array
import hashlib
from pathlib import Path
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_source_reference_witness_v8 as witness
import source_reference_witness_v7_pure_checks as previous


def main():
    old_witness = previous.witness
    try:
        previous.witness = witness
        previous.main()  # All 21 prior guard/coverage groups against NEW V8.
    finally:
        previous.witness = old_witness
    original_bpy = sys.modules.get("bpy")
    class RNA:
        def __init__(self, props):
            self.properties = props
        def as_pointer(self):
            return id(self)
    props = []
    for name, (kind, width) in witness.KEYFRAME_FIELDS.items():
        props.append(types.SimpleNamespace(identifier=name, type=kind, array_length=width,
            is_array=width > 1, is_runtime=False, is_readonly=False,
            enum_items=[types.SimpleNamespace(identifier="A", value=0), types.SimpleNamespace(identifier="B", value=1)]))
    class Native:
        def items(self):
            if self.raw_supported:
                return self.raw.items()
            raise TypeError("bpy_struct.items(): this type doesn't support IDProperties")
    class Keyframe(Native):
        bl_rna = RNA(props)
        raw_supported = False
        def __init__(self, offset=0):
            self.raw = {}
            for name, (kind, width) in witness.KEYFRAME_FIELDS.items():
                setattr(self, name, ([float(offset), -0.0] if width == 2 else
                                    "A" if kind == "ENUM" else bool(offset) if kind == "BOOLEAN" else 0.25 + offset))
    class Points(list):
        def foreach_get(self, name, values):
            kind, width = witness.KEYFRAME_FIELDS[name]
            flat = []
            for point in self:
                value = getattr(point, name)
                flat.extend(value if width > 1 else [int(value == "B") if kind == "ENUM" else value])
            assert len(values) == len(flat)
            for index, value in enumerate(flat):
                values[index] = value
    fake_bpy = types.SimpleNamespace(app=types.SimpleNamespace(version=(5, 2, 0)),
        types=types.SimpleNamespace(Keyframe=Keyframe, bpy_struct=Native))
    sys.modules["bpy"] = fake_bpy
    def read(points):
        return witness.keyframe_collection_witness(points, Keyframe.bl_rna, witness.Reader(type("FakeID", (), {})))
    def reject(points):
        try:
            read(points)
        except witness.SourceReferenceWitnessError:
            return
        raise AssertionError("Unproved bulk case admitted")
    try:
        points = Points([Keyframe(), Keyframe(1)])
        initial = read(points)
        assert set(initial["fields"]) == set(witness.KEYFRAME_FIELDS)
        expected = array("f", [0.0, -0.0, 1.0, -0.0]).tobytes()
        assert initial["fields"]["co"]["sha256"] == hashlib.sha256(expected).hexdigest()
        points[0].co[1] = 0.0
        assert read(points)["fields"]["co"]["sha256"] != initial["fields"]["co"]["sha256"]
        points[0].interpolation = "B"
        assert read(points)["fields"]["interpolation"]["sha256"] != initial["fields"]["interpolation"]["sha256"]
        points[0].co = [float("inf"), float("nan")]
        expected_nonfinite = array("f", [float("inf"), float("nan"), 1.0, -0.0]).tobytes()
        assert read(points)["fields"]["co"]["sha256"] == hashlib.sha256(expected_nonfinite).hexdigest()
        points[0].co = [0.0, 0.0]
        points.append(Keyframe(2))
        assert read(points)["count"] == 3
        points.pop()
        assert read(points)["count"] == 2
        # Empty FIRST storage never proves that later native rows have none.
        Keyframe.raw_supported = True
        points[0].raw, points[1].raw = {}, {"foreign": "must not disappear"}
        reject(points)
        Keyframe.raw_supported = False
        class SameNameKeyframe(Keyframe):
            pass
        reject(Points([SameNameKeyframe()]))
        props[0].is_runtime = True
        reject(points)
        props[0].is_runtime = False
        extra = types.SimpleNamespace(identifier="future_unknown")
        props.append(extra)
        reject(points)
        props.pop()
        empty = read(Points())
        assert empty["raw_storage_mode"] == "empty_collection_no_elements" and empty["count"] == 0
        print("PASS8 bulk groups: all15fields; signedzero/nonfinite bits; enum; add/remove; empty-first/later-raw rejection; nonnative/runtime/unknown rejection; empty collection schema")
    finally:
        if original_bpy is None:
            sys.modules.pop("bpy", None)
        else:
            sys.modules["bpy"] = original_bpy


if __name__ == "__main__":
    main()

    # Run the real factory entry against a tiny fake backend for insertion
    # partial failures: even a created Action on False/raise must be owned.
    import native_keyframe_bulk_factory_008 as factory
    original_bpy, original_argv = sys.modules.get("bpy"), sys.argv
    names = ("pin", "verify_package_manifest", "handler_snapshot", "native_id_pointers", "witness_dependency_pins")
    saved = {name: getattr(factory.witness, name) for name in names}
    class Item:
        def __init__(self):
            self.session_uid = id(self)
        def as_pointer(self):
            return id(self)
    class Collection(list):
        def remove(self, item, do_unlink=False):
            super().remove(item)
    try:
        for mode in ("false", "raise"):
            objects, actions = Collection(), Collection()
            failure = RuntimeError("owned insert raised after Action allocation")
            class Obj(Item):
                def __init__(self):
                    super().__init__()
                    self.location = types.SimpleNamespace(x=0)
                    self.animation_data = None
                def keyframe_insert(self, **_kwargs):
                    action = Item()
                    actions.append(action)
                    self.animation_data = types.SimpleNamespace(action=action)
                    if mode == "raise":
                        raise failure
                    return False
            def new(_name, _data):
                obj = Obj()
                objects.append(obj)
                return obj
            objects.new = new
            sys.modules["bpy"] = types.SimpleNamespace(app=types.SimpleNamespace(background=True, version_string="pure-fake"),
                data=types.SimpleNamespace(filepath="", objects=objects, actions=actions))
            sys.argv = ["fake", "--factory-startup", "-t", "1", "--"]
            def pin(path):
                return {"path": str(path), "sha256": "d62c3178ca6f0615fa4517440c157bba0ab2ced87cb64aa560ac1830197bac34", "bytes": 0}
            factory.witness.pin = pin
            factory.witness.verify_package_manifest = lambda *_args: {}
            factory.witness.handler_snapshot = lambda: {}
            factory.witness.native_id_pointers = lambda: {id(item) for item in list(objects) + list(actions)}
            factory.witness.witness_dependency_pins = lambda: {}
            here = Path(__file__).resolve().parent
            args = types.SimpleNamespace(artist=str(here / "fake-artist"),
                source_manifest=str(here / "staged_20261015_05/source_manifest.json"), addons=str(here / "staged_20261015_05/addons"))
            report = {}
            try:
                factory.main(args, report)
            except RuntimeError as error:
                assert error is failure if mode == "raise" else str(error) == "Fixture insertion failed"
            else:
                raise AssertionError("Insertion failure disappeared")
            assert not objects and not actions and report["all_fixture_ids_removed"] and not report["cleanup_errors"]
        print("PASS2 factory partial-insert groups: created Action removed on False and on original exception")
    finally:
        for name, value in saved.items():
            setattr(factory.witness, name, value)
        sys.argv = original_argv
        if original_bpy is None:
            sys.modules.pop("bpy", None)
        else:
            sys.modules["bpy"] = original_bpy
