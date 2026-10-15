"""Inject new bulk witness into unchanged FrozenV8.main for one admission frame."""
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_validation_support_v8 as witness
import private_playback_native_runner_v8 as frozen


def main(args, report):
    if not args.admission_only or args.builder_module != "character_designer.forearm_twist_playback_scene" or args.builder_function != "build_isolated_scene":
        raise RuntimeError("Single saved-frame protected admission arguments required")
    manifest = Path(args.source_manifest).resolve()
    if witness.pin(manifest)["sha256"] != "5c7965ef74e99ed8036bc57ad639cb4db37e6501bb580483a676d4b2fd6cc3c0" or Path(args.addons).resolve() != manifest.parent / "addons":
        raise RuntimeError("Protected Stage06 required")
    old_runner = witness.pin(frozen.__file__)
    if old_runner["sha256"] != "c67af8e103c7a6ad93dce723e5bfda3edcc70efde4e96c49cb49a35be6593f55":
        raise RuntimeError("Historical FrozenV8 changed")
    original = frozen.witness
    report["witness_override"] = {"wrapper": witness.pin(__file__), "unchanged_runner": old_runner,
                                  "original_support": witness.pin(original.__file__),
                                  "injected_support": witness.pin(witness.__file__),
                                  "injected_dependencies": witness.witness_dependency_pins()}
    frozen.witness = witness
    try:
        frozen.main(args, report)
    finally:
        report["witness_override_still_owned"] = frozen.witness is witness
        if frozen.witness is witness:
            frozen.witness = original
        report["witness_override_restored"] = frozen.witness is original
        report["wrapper_and_runner_sources_unchanged"] = report["witness_override"]["wrapper"] == witness.pin(__file__) and old_runner == witness.pin(frozen.__file__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "artist", "addons", "source-manifest", "builder-module", "report"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--builder-function", default="build_isolated_scene")
    parser.add_argument("--admission-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    if path.exists():
        raise RuntimeError("Never overwrite evidence")
    report = {"schema": "x.frozen-bulk-single-admission/1", "completed": False, "pid": os.getpid(),
              "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "no_artist_open_or_save": True, "no_scene_save": True, "no_deploy": True,
              "performance_acceptance": False, "all_30_complete_outputs_exact": False}
    try:
        main(args, report)
        if not report["witness_override_still_owned"] or not report["witness_override_restored"] or not report["wrapper_and_runner_sources_unchanged"]:
            raise RuntimeError("Witness override cleanup failed")
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
