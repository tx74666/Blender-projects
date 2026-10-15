"""Inject the Enum API fix into preserved SourceScan009; keep both scan passes."""
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_source_bulk_scan_009 as scan
import native_validation_support_v9 as witness


def main(args, report):
    original_pin = witness.pin(scan.__file__)
    if original_pin["sha256"] != "bd8fbfd593b4553374f967dbe7ca9a4f1c3e66c3ab6049a6e1673711218855e5":
        raise RuntimeError("Protected SourceScan009 changed")
    original = scan.witness
    wrapper_pin = witness.pin(__file__)
    report["scan_witness_override"] = {"wrapper": wrapper_pin, "unchanged_scan": original_pin,
        "original_support": witness.pin(original.__file__), "injected_support": witness.pin(witness.__file__),
        "injected_dependencies": witness.witness_dependency_pins()}
    scan.witness = witness
    try:
        scan.main(args, report)
    finally:
        report["scan_override_still_owned"] = scan.witness is witness
        if scan.witness is witness:
            scan.witness = original
        report["scan_override_restored"] = scan.witness is original
        report["wrapper_scan_sources_unchanged"] = wrapper_pin == witness.pin(__file__) and original_pin == witness.pin(scan.__file__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "artist", "addons", "source-manifest", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    if path.exists():
        raise RuntimeError("Never overwrite evidence")
    report = {"schema": "x.initial-source-bulk-scan/1", "completed": False, "pid": os.getpid(),
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "no_artist_open_or_save": True, "no_scene_save": True, "no_clone": True,
        "no_frame_seek_or_manual_solver": True, "performance_acceptance": False,
        "limits": ["Two initial source-reference scans, not 30-frame equivalence or GUI FPS.",
                   "Process peak RSS is lifetime high-water including load, not an isolated scan peak."]}
    try:
        main(args, report)
        if not all(report[name] for name in ("scan_override_still_owned", "scan_override_restored", "wrapper_scan_sources_unchanged")):
            raise RuntimeError("Source-scan witness override cleanup failed")
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
