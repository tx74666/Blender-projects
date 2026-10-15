"""Reuse pinned bulk tests with real Enum metadata shape; no native execution."""
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_source_reference_witness_v8 as old
import native_source_reference_witness_v9 as new

source = HERE / "keyframe_bulk_pure_checks_008.py"
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == "fb4425230b783a3c8e8c4740b7092d4661a680d9fe8225262d21b91d30ad5f39"
text = raw.decode("utf-8")
anchor = "    class Native:\n"
assert text.count(anchor) == 1
text = text.replace(anchor, "    for prop in props:\n        if prop.type == 'ENUM':\n            del prop.is_array\n            del prop.array_length\n" + anchor)
namespace = {"__file__": str(source), "__name__": "_enum_metadata_shape_regression"}
exec(compile(text, str(source), "exec"), namespace)
namespace["witness"] = old
try:
    namespace["main"]()
except AttributeError as error:
    assert "is_array" in str(error)
else:
    raise AssertionError("Original V8 did not reproduce missing EnumProperty.is_array")
namespace["witness"] = new
namespace["main"]()
print("PASS original V8 API failure reproduced; NEW V9 passes all prior guards/bulk cases with ENUM is_array/array_length absent")
