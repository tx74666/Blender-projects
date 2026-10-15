"""Admission/cadence/hot-boundary scaffold tests; no bpy or GUI invocation."""
import ast
import importlib.util
import json
from pathlib import Path
import sys

PATH = Path(__file__).resolve().with_name("private_gui_fps_probe_009.py")
spec = importlib.util.spec_from_file_location("private_fps009_pure", PATH)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def rejects(config, pid=777):
    try:
        probe.validate_config(config, pid)
    except RuntimeError:
        return
    raise AssertionError("Unsafe/incomplete configuration accepted")


def main():
    require_no_bpy = "bpy" not in sys.modules
    config = {"expected_pid": 777, "private_blend": "private.blend", "private_sha256": probe.FIXED_BASELINE[0],
              "artist": "artist.blend", "addons": "stage/addons", "source_manifest": "stage/source_manifest.json",
              "source_manifest_sha256": "a" * 64, "mode": "SOLID", "kind": "baseline",
              "report": "unused.json", "allow_fixed_baseline": True}
    assert probe.validate_config(config, 777) == config
    rejects({**config, "expected_pid": 778})
    rejects({**config, "expected_pid": True})
    rejects({**config, "allow_fixed_baseline": False})
    rejects({**config, "private_sha256": "b" * 64})
    rejects({**config, "mode": "WIREFRAME"})
    rejects({**config, "private_blend": Path("private.blend")})
    rejects({**config, "kind": "baked", "allow_fixed_baseline": False})
    baked = {**config, "kind": "baked", "allow_fixed_baseline": False,
             "gui008_report": "gui008.json", "gui008_report_sha256": "c" * 64}
    assert probe.validate_config(baked, 777) == baked
    rows = [(round(index * 1e9 / 30), index % 30 + 1, 0.0) for index in range(480)]
    stats = probe.cadence(rows)
    assert stats["count_per_fixed_window_hz"] == 30.0
    assert abs(stats["interevent_hz"] - 30.0) < 1e-7
    assert stats["unique_integer_frames"] == list(range(1, 31))
    duplicate_draws = [row for row in rows for _ in range(2)]
    assert probe.changed_draw_events(duplicate_draws) == rows
    assert probe.cadence(duplicate_draws)["count_per_fixed_window_hz"] == 60.0
    controller = object.__new__(probe.Probe)
    controller.collecting, controller.start_ns, controller.end_ns = True, 2_000_000_000, 18_000_000_000
    assert not controller.in_hot(1_999_999_999) and controller.in_hot(2_000_000_000)
    assert controller.in_hot(17_999_999_999) and not controller.in_hot(18_000_000_000)
    controller.collecting = False
    assert not controller.in_hot(5_000_000_000)
    assert probe.distribution([])["mean"] is None
    # No file-open/save/addon registration/deformation call is present in the
    # entry source. This check does not substitute for native ownership proof.
    tree = ast.parse(PATH.read_text(encoding="utf-8-sig"))
    forbidden = {"open_mainfile", "save_mainfile", "save_as_mainfile", "_calculate_object",
                 "defer_runtime", "update_from_deformations"}
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr in forbidden for node in ast.walk(tree))
    playback_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                      and isinstance(node.func, ast.Attribute) and node.func.attr == "animation_play"]
    assert len(playback_calls) == 1 and not any(keyword.arg == "sync" for keyword in playback_calls[0].keywords)
    assert require_no_bpy and "bpy" not in sys.modules
    print(json.dumps({"config_positive_and_seven_rejections": True, "baked_receipt_required": True,
                      "thirty_Hz_event_math": True, "duplicate_draws_are_not_changed_frames": True,
                      "fixed_hot_boundaries": True, "empty_stats_not_fake_rate": True,
                      "no_forbidden_native_calls_in_source": True, "no_bpy_import_or_GUI": True}, indent=2))


if __name__ == "__main__":
    main()
