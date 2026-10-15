"""Seal two existing generated-fixture sources beside a staged package.

Ordinary lightweight file I/O only; does not import Blender or execute fixtures.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil

NAMES = ("test_forearm_twist_blender.py", "test_limb_ik_blender.py")


def pin(path):
    raw = Path(path).read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def main():
    parser = argparse.ArgumentParser()
    for name in ("source-tests", "destination-tests", "manifest"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    source, destination = Path(args.source_tests).resolve(), Path(args.destination_tests).resolve()
    manifest = Path(args.manifest).resolve()
    allowed = Path(__file__).resolve().parent
    if allowed not in destination.parents or allowed not in manifest.parents:
        raise RuntimeError("Fixture stage/manifest must stay within this validation directory")
    if destination.exists() or manifest.exists():
        raise RuntimeError("Do not replace an existing fixture stage/seal")
    before = {name: pin(source / name) for name in NAMES}
    destination.mkdir(parents=True)
    for name in NAMES:
        shutil.copy2(source / name, destination / name)
    if before != {name: pin(source / name) for name in NAMES} or before != {name: pin(destination / name) for name in NAMES}:
        raise RuntimeError("Fixture sources changed during copy")
    result = {"schema": "x.playback-synthetic-fixture-seal/1",
              "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "directory": str(destination), "source_directory": str(source), "files": before,
              "all_files_exact": True, "native_invocation": False,
              "model": "gpt-6.1-sol", "reasoning_effort": "ultra",
              "model_source": "Current root task local index verified by root; inherited task settings."}
    manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest), "files": len(NAMES), "all_exact": True}))


if __name__ == "__main__":
    main()
