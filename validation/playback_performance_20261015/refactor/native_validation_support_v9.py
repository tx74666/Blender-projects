"""Add registered source/foreign Object guards to protected original witnesses."""
import hashlib
from pathlib import Path

_BASE_PATH = Path(__file__).resolve().with_name("native_validation_support.py")
_BASE_SHA256 = "3994f58288244684679ffd48d0837ac88bcfd9768f0a3a12c3e1d7d5b6265c0a"
_EXTENSION_PATH = Path(__file__).resolve().with_name("native_source_reference_witness_v9.py")
_EXTENSION_SHA256 = "fb87e81b29482e2668b6d29449713e4ddf4885797e6860100f118dd4bfa6b192"
for _path, _expected in ((_BASE_PATH, _BASE_SHA256), (_EXTENSION_PATH, _EXTENSION_SHA256)):
    if hashlib.sha256(_path.read_bytes()).hexdigest() != _expected:
        raise RuntimeError("Protected native witness dependency changed: " + _path.name)

import native_validation_support as _original
from native_validation_support import *
from native_source_reference_witness_v9 import registered_source_witness
import native_source_reference_witness_v9 as _extension
if Path(_original.__file__).resolve() != _BASE_PATH or Path(_extension.__file__).resolve() != _EXTENSION_PATH:
    raise RuntimeError("Native imported a different source witness")


def witness_dependency_pins():
    result = {}
    for path, expected in ((_BASE_PATH, _BASE_SHA256), (_EXTENSION_PATH, _EXTENSION_SHA256)):
        observed = pin(path)
        if observed["sha256"] != expected:
            raise RuntimeError("Protected native witness dependency changed: " + path.name)
        result[path.name] = observed
    result[Path(__file__).name] = pin(__file__)
    return result


def source_property_witness(scene):
    original = _original.source_property_witness(scene)
    extension = registered_source_witness(scene, _original)
    components = {**original["components"],
                  "registered_source_and_external_objects": extension["sha256"]}
    return {"sha256": object_hash(components), "components": components,
            "registered_source_and_external_objects": extension}
