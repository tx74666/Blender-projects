"""Read-only disk receipt. Never loads, saves or controls Blender."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTIST = HERE.parent.parent / "X.blend"
HISTORY = HERE / "artist_disk_protection_20261006_caeb.json"
HISTORY_SHA = "ffd821f9fc4a4d76c179bbc7d1792d9a6d7b38e86a966d649209287977685938"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    assert sha(HISTORY) == HISTORY_SHA, "Historical caeb V2 changed"
    before = ARTIST.stat()
    digest = sha(ARTIST)
    after = ARTIST.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    assert sha(ARTIST) == digest, "Artist changed during read-only capture"
    value = {
        "schema": "ARTIST_DISK_PROTECTION_V3",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Read-only current disk protection; current native save, live state and historical model equivalence are not proved",
        "artist_path": str(ARTIST.resolve()),
        "artist_sha256": digest,
        "artist_bytes": after.st_size,
        "artist_mtime_ns": after.st_mtime_ns,
        "artist_last_write_utc": datetime.fromtimestamp(after.st_mtime, timezone.utc).isoformat(),
        "artist_pid": 12696,
        "artist_executable": "D:\\Blender5.2\\blender.exe",
        "changed_by_this_capture": False,
        "current_native_save_proof": "Unmeasured",
        "current_disk_equals_old_7ac_fullraw": "Unmeasured",
        "current_disk_equals_caeb_fullraw": "Unmeasured",
        "live_unsaved_state": "Unmeasured",
        "historical_caeb_v2": {"path": str(HISTORY), "sha256": HISTORY_SHA, "current_identity": False},
        "accepted": False,
    }
    output = HERE / ("artist_disk_protection_20261006_" + digest[:12] + ".json")
    assert not output.exists(), "Preserve prior receipts; do not overwrite"
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(output), "sha256": sha(output), "artist_sha256": digest, "artist_bytes": after.st_size, "artist_mtime_ns": after.st_mtime_ns}))


if __name__ == "__main__":
    main()
