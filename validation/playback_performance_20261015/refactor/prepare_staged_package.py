"""Copy reviewed canonical sources into a uniquely owned, sealed native stage.

This is ordinary file I/O only. No Blender import/process, deployment or artist
access. Concurrent canonical source changes fail the stage instead of silently
mixing versions. Existing stage/report paths are never replaced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def files(package):
    result = {}
    for path in sorted(package.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        raw = path.read_bytes()
        result[str(path.relative_to(package)).replace("\\", "/")] = {
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return result


def main():
    parser = argparse.ArgumentParser()
    for name in ("source-addons", "destination-addons", "reference-runtime", "manifest", "receipt"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--reference-sha256", required=True)
    args = parser.parse_args()
    source = (Path(args.source_addons).resolve() / "character_designer").resolve()
    destination_root = Path(args.destination_addons).resolve()
    destination = destination_root / "character_designer"
    if source == destination or source in destination.parents:
        raise RuntimeError("Native stage must be independent from canonical sources")
    allowed = Path(__file__).resolve().parent
    if allowed not in destination_root.parents:
        raise RuntimeError("Stage must stay within this validation directory")
    if destination_root.exists() or Path(args.manifest).exists() or Path(args.receipt).exists():
        raise RuntimeError("Do not replace an existing stage or seal")
    before = files(source)
    destination.mkdir(parents=True)
    for name in before:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)
    if files(source) != before or files(destination) != before:
        raise RuntimeError("Canonical/staged files changed during copy")
    subprocess.run([sys.executable, str(allowed / "seal_source_manifest.py"),
                    "--addons", str(destination_root), "--reference-runtime", args.reference_runtime,
                    "--reference-sha256", args.reference_sha256, "--output", args.manifest], check=True)
    if files(source) != before or files(destination) != before:
        raise RuntimeError("Canonical/staged files changed during seal")
    receipt = {"schema": "x.private-playback-stage/1", "completed": True,
               "source_package": str(source), "staged_package": str(destination),
               "all_files_exact": True, "files": before,
               "source_manifest": str(Path(args.manifest).resolve()),
               "no_native_invocation": True, "no_deployment": True, "no_artist_access": True}
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"staged_package": str(destination), "files": len(before),
                      "manifest": str(Path(args.manifest).resolve()), "all_files_exact": True}))


if __name__ == "__main__":
    main()
