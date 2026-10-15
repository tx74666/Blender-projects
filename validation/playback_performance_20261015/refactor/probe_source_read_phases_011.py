"""Diagnostic wrappers around protected Smoke005v2; never waive its failure.

Run only in a new, root-owned factory background Blender process. This adds
metadata observations to the existing Reader calls, without changing their
inputs, return values, exceptions, source guards or fixture cleanup.
"""
import argparse
import datetime
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
PINS = {
    "native_source_reference_witness_v5.py": "e0a56ab2c38546a36dd90eaca1dc74ca1ad57da61bab7528b602144157ef8135",
    "native_validation_support_v5.py": "68451f7cc73d582da148b6a4efcbdf3596edaf4285310a3e40997273d70ff2ce",
    "scene_builder_smoke_005_v2.py": "146b8ed27b600e064d55feb0252a2d7dfe67712654c399ddc5c0d51c1270f5ef",
}
STAGE_SHA = "d62c3178ca6f0615fa4517440c157bba0ab2ced87cb64aa560ac1830197bac34"


def changed(before, after):
    return {name: [before.get(name), after.get(name)]
            for name in sorted(set(before) | set(after))
            if before.get(name) != after.get(name)}


def main(args, report):
    for name, expected in PINS.items():
        if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Protected diagnostic dependency changed: " + name)
    manifest = Path(args.source_manifest).resolve()
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != STAGE_SHA:
        raise RuntimeError("Expected sealed Stage05 source manifest")
    if Path(args.addons).resolve() != manifest.parent / "addons":
        raise RuntimeError("Expected Stage05 addons beside its manifest")
    sys.path.insert(0, str(HERE))
    import native_source_reference_witness_v5 as extension
    import scene_builder_smoke_005_v2 as smoke
    if Path(extension.__file__).resolve() != HERE / "native_source_reference_witness_v5.py" or Path(smoke.__file__).resolve() != HERE / "scene_builder_smoke_005_v2.py":
        raise RuntimeError("Different diagnostic dependency imported")
    reader = extension.Reader
    original_rna_code = reader.rna.__code__
    originals = {name: getattr(reader, name) for name in ("raw", "value", "default_descriptor")}
    events, observer_errors, previous = [], [], {}
    report.update(diagnostic_script={"path": str(Path(__file__).resolve()),
                                    "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                  diagnostic_dependency_pins=PINS, diagnostic_stage_manifest_sha256=STAGE_SHA,
                  diagnostic_events=events, diagnostic_observer_errors=observer_errors,
                  diagnostic_limits="Only existing Setup Reader phases observed. Snapshot reads is_property_set and raw key names; computed getter outputs are never independently requested. Existing Smoke guards remain authoritative.")

    def observe(method, call_args, boundary, result=None, exception=None):
        frame = inspect.currentframe()
        try:
            while frame is not None:
                if frame.f_code is original_rna_code and str(frame.f_locals.get("path", "")).endswith(".character_designer_setup"):
                    break
                frame = frame.f_back
            if frame is None:
                return
            local = frame.f_locals
            setup, path = local["value"], local["path"]
            names = sorted(local["registered_names"])
            snapshot = {"set_bits": {name: bool(setup.is_property_set(name)) for name in names},
                        "raw_keys": sorted(str(key) for key in setup.keys())}
            token = (id(frame), int(setup.as_pointer()))
            old = previous.get(token, {"set_bits": dict(local["set_bits_before"]),
                                       "raw_keys": snapshot["raw_keys"]})
            prop = local.get("prop")
            call_path = call_args[1] if len(call_args) > 1 and isinstance(call_args[1], str) else None
            phase = ("raw_before" if "raw_before" not in local else "raw_after") if method == "raw" else method
            event = {"sequence": len(events), "phase": phase, "boundary": boundary,
                     "rna_path": path, "field": local.get("name"), "call_path": call_path,
                     "set_bit_delta_since_previous_observation": changed(old["set_bits"], snapshot["set_bits"]),
                     "raw_keys_added": sorted(set(snapshot["raw_keys"]) - set(old["raw_keys"])),
                     "raw_keys_removed": sorted(set(old["raw_keys"]) - set(snapshot["raw_keys"])),
                     "snapshot": snapshot}
            if prop is not None:
                event["field_type"] = prop.type
            if method == "value" and prop is not None and prop.type == "COLLECTION" and call_path == path + "." + local.get("name", ""):
                event["native_collection_count"] = len(call_args[0])
                if boundary == "after" and exception is None:
                    event["reader_result_type"] = type(result).__name__
                    event["reader_result_count"] = len(result)
                    if isinstance(result, dict):
                        event["reader_result_mapping_keys"] = list(result)
            if exception is not None:
                event["original_exception"] = type(exception).__name__ + ": " + str(exception)
            previous[token] = snapshot
            if len(events) < 512:
                events.append(event)
            else:
                report["diagnostic_events_truncated"] = True
        except BaseException:
            observer_errors.append(traceback.format_exc())
        finally:
            del frame

    wrappers = {}
    for name, original in originals.items():
        def wrapped(self, *call_args, _name=name, _original=original, **kwargs):
            observe(_name, call_args, "before")
            try:
                result = _original(self, *call_args, **kwargs)
            except BaseException as error:
                observe(_name, call_args, "after", exception=error)
                raise
            observe(_name, call_args, "after", result=result)
            return result
        wrappers[name] = wrapped
        setattr(reader, name, wrapped)
    try:
        smoke.main(args, report)
    finally:
        report["diagnostic_wrappers_still_owned"] = all(getattr(reader, name) is wrapper for name, wrapper in wrappers.items())
        for name, original in originals.items():
            if getattr(reader, name) is wrappers[name]:
                setattr(reader, name, original)
        report["diagnostic_reader_methods_restored"] = all(getattr(reader, name) is original for name, original in originals.items())
        if "sources" in report:
            sources = report.pop("sources")
            report["source_pin_summary"] = {"count": len(sources), "sha256": extension.object_hash(sources)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("artist", "addons", "source-manifest", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    if path.exists():
        raise RuntimeError("Never overwrite evidence")
    report = {"schema": "x.source-rna-read-phase-diagnostic/1", "completed": False,
              "pid": os.getpid(), "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "no_blend_open": True, "no_artist_open_or_save": True, "no_scene_save": True,
              "performance_claim": None, "expected_outcome": "Original Smoke005v2 guard failure preserved, with phase metadata."}
    try:
        main(args, report)
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        with path.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2, ensure_ascii=False)
            output.write("\n")
