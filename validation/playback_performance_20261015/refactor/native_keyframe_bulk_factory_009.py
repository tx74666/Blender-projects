"""Retain Factory008 logic; inject only the missing-is_array API fix."""
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_keyframe_bulk_factory_008 as factory
import native_source_reference_witness_v9 as bulk
import native_validation_support_v9 as witness


def main(args, report):
    original_pin = witness.pin(factory.__file__)
    if original_pin["sha256"] != "986b1ad696222cf4fb7d1ff1381dcc149691f56af543a786a68c8d706a69a606":
        raise RuntimeError("Protected Factory008 changed")
    original_bulk, original_witness = factory.bulk, factory.witness
    wrapper_pin = witness.pin(__file__)
    report["factory_override"] = {"wrapper": wrapper_pin, "unchanged_factory": original_pin,
                                  "bulk": witness.pin(bulk.__file__), "support": witness.pin(witness.__file__)}
    factory.bulk, factory.witness = bulk, witness
    try:
        factory.main(args, report)
    finally:
        report["factory_overrides_still_owned"] = factory.bulk is bulk and factory.witness is witness
        if factory.bulk is bulk:
            factory.bulk = original_bulk
        if factory.witness is witness:
            factory.witness = original_witness
        report["factory_overrides_restored"] = factory.bulk is original_bulk and factory.witness is original_witness
        report["wrapper_factory_sources_unchanged"] = wrapper_pin == witness.pin(__file__) and original_pin == witness.pin(factory.__file__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("artist", "addons", "source-manifest", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    if path.exists():
        raise RuntimeError("Never overwrite evidence")
    report = {"schema": "x.native-keyframe-bulk-factory/1", "completed": False, "pid": os.getpid(),
              "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "no_blend_open_or_save": True, "no_addon_register": True, "performance_acceptance": False}
    try:
        main(args, report)
        if not all(report[name] for name in ("factory_overrides_still_owned", "factory_overrides_restored", "wrapper_factory_sources_unchanged")):
            raise RuntimeError("Factory override cleanup failed")
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
