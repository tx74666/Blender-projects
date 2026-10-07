"""Typed, CLI-selected disk-only protection. No Blender/UI/save operation.

A Root-selected receipt fixes one exact disk state for a new private QA run.
Current save/UI/live/model identity claims remain explicitly Unmeasured.
"""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ARTIST = HERE.parent.parent / "X.blend"
HISTORICAL_V2 = HERE / "artist_disk_protection_20261006_caeb.json"
HISTORICAL_V2_SHA = "ffd821f9fc4a4d76c179bbc7d1792d9a6d7b38e86a966d649209287977685938"
FIELDS = {"schema", "captured_at_utc", "scope", "artist_path", "artist_sha256", "artist_bytes", "artist_mtime_ns",
          "artist_last_write_utc", "artist_pid", "artist_executable", "changed_by_this_capture", "current_native_save_proof",
          "current_disk_equals_old_7ac_fullraw", "current_disk_equals_caeb_fullraw", "live_unsaved_state", "historical_caeb_v2", "accepted"}


def need(condition, message):
    if not condition:
        raise RuntimeError("ArtistDiskProtection52: " + message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def complete_sha(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def typed_receipt(value, artist=ARTIST):
    need(type(value) is dict and set(value) == FIELDS, "V3 exact field set differs")
    need(value["schema"] == "ARTIST_DISK_PROTECTION_V3" and value["scope"] ==
         "Read-only current disk protection; current native save, live state and historical model equivalence are not proved", "V3 scope differs")
    need(type(value["artist_path"]) is str and Path(value["artist_path"]).is_absolute()
         and Path(value["artist_path"]).resolve() == Path(artist).resolve() == ARTIST.resolve(), "V3 artist path differs")
    need(complete_sha(value["artist_sha256"]) and type(value["artist_bytes"]) is int and value["artist_bytes"] > 0
         and type(value["artist_mtime_ns"]) is int and value["artist_mtime_ns"] > 0, "V3 SHA/size/mtime untyped")
    need(type(value["artist_pid"]) is int and value["artist_pid"] > 0 and type(value["artist_executable"]) is str
         and Path(value["artist_executable"]).resolve() == Path("D:/Blender5.2/blender.exe").resolve(), "V3 captured artist runtime differs")
    need(value["changed_by_this_capture"] is False and value["accepted"] is False, "V3 read-only flags differ")
    for name in ("current_native_save_proof", "current_disk_equals_old_7ac_fullraw", "current_disk_equals_caeb_fullraw", "live_unsaved_state"):
        need(value[name] == "Unmeasured", "V3 unknown claim promoted")
    for name in ("captured_at_utc", "artist_last_write_utc"):
        need(type(value[name]) is str and datetime.fromisoformat(value[name].replace("Z", "+00:00")).tzinfo is not None,
             "V3 timestamp untyped/untimed")
    old = value["historical_caeb_v2"]
    need(type(old) is dict and set(old) == {"path", "sha256", "current_identity"} and type(old["path"]) is str
         and Path(old["path"]).resolve() == HISTORICAL_V2.resolve() and old["sha256"] == HISTORICAL_V2_SHA
         and old["current_identity"] is False, "V3 caeb historical identity promoted/differs")
    return copy.deepcopy(value)


def proof(receipt_path, receipt_sha, artist=ARTIST):
    """Strict Root-selected receipt SHA plus exact current bytes/mtime; no defaults."""
    path = Path(receipt_path)
    need(path.is_absolute() and path.resolve().is_relative_to(HERE) and path.is_file() and complete_sha(receipt_sha),
         "explicit complete Root receipt path/SHA required")
    need(sha(path) == receipt_sha, "selected V3 receipt bytes changed")
    receipt = typed_receipt(json.loads(path.read_text(encoding="utf-8")), artist)
    need(sha(HISTORICAL_V2) == HISTORICAL_V2_SHA, "historical caeb V2 bytes changed")
    before = Path(artist).stat()
    digest = sha(artist)
    after = Path(artist).stat()
    need((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
         == (receipt["artist_bytes"], receipt["artist_mtime_ns"]) and digest == receipt["artist_sha256"],
         "current artist bytes/mtime changed from selected protection")
    need(sha(path) == receipt_sha, "V3 receipt changed during capture")
    return {"path": str(path.resolve()), "sha256": receipt_sha, "receipt": receipt,
            "current_artist_sha256": receipt["artist_sha256"], "current_artist_bytes": receipt["artist_bytes"],
            "current_artist_mtime_ns": receipt["artist_mtime_ns"], "current_artist_loaded_saved_or_modified": False,
            "current_artist_fullraw_vs7ac": "Unmeasured", "current_artist_fullraw_vs_caeb": "Unmeasured",
            "current_live_unsaved_state": "Unmeasured", "current_native_save_proof": "Unmeasured",
            "captured_artist_runtime": {"pid": receipt["artist_pid"], "executable": receipt["artist_executable"],
                "scope": "Root receipt capture; this helper does not revalidate the current process/UI"},
            "accepted": False}


def pure_checks(receipt_path, receipt_sha):
    observed = proof(receipt_path, receipt_sha)
    rejected = 0
    changes = (("artist_bytes", True), ("artist_mtime_ns", True), ("artist_sha256", "bad"),
               ("artist_path", str(ARTIST.with_name("Other.blend"))), ("artist_pid", True),
               ("artist_executable", "D:/Blender5.1/blender.exe"), ("changed_by_this_capture", True),
               ("current_native_save_proof", "PASS"), ("current_disk_equals_old_7ac_fullraw", True),
               ("current_disk_equals_caeb_fullraw", "True"), ("live_unsaved_state", "Clean"), ("accepted", True))
    for name, val in changes:
        value = copy.deepcopy(observed["receipt"]); value[name] = val
        try: typed_receipt(value)
        except (RuntimeError, TypeError, ValueError): rejected += 1
        else: raise RuntimeError("V3 negative accepted")
    value = copy.deepcopy(observed["receipt"]); value["historical_caeb_v2"]["current_identity"] = True
    try: typed_receipt(value)
    except RuntimeError: rejected += 1
    else: raise RuntimeError("V3 historical promotion accepted")
    value = copy.deepcopy(observed["receipt"]); value["new_claim"] = True
    try: typed_receipt(value)
    except RuntimeError: rejected += 1
    else: raise RuntimeError("V3 extra-field accepted")
    return {"passed": True, "typed_V3_positive": 1, "typed_V3_negatives_rejected": rejected,
            "current_artist_sha256": observed["current_artist_sha256"], "native_run": False, "accepted": False}
