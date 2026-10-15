"""Serial client for the already installed, temporary X playback profiler."""
import argparse
import json
import os
from pathlib import Path
import time

FOLDER = Path(__file__).resolve().parent
CASES = {
    "snapshot": {"operation": "snapshot"},
    "material": {"operation": "sample", "shading": "MATERIAL"},
    "solid": {"operation": "sample", "shading": "SOLID"},
    "solid_panel_closed": {"operation": "sample", "shading": "SOLID", "hide_sidebar": True},
    "cosha_hidden": {"operation": "sample", "shading": "SOLID", "hide_sidebar": True, "hide_objects": ["Cosha"]},
    "shoes_hidden": {"operation": "sample", "shading": "SOLID", "hide_sidebar": True, "hide_objects": ["Shoes"]},
    "both_hidden": {"operation": "sample", "shading": "SOLID", "hide_sidebar": True, "hide_objects": ["Cosha", "Shoes"]},
    "cosha_disabled": {"operation": "sample", "shading": "SOLID", "hide_sidebar": True, "disable_viewport_objects": ["Cosha"]},
    "shoes_disabled": {"operation": "sample", "shading": "SOLID", "hide_sidebar": True, "disable_viewport_objects": ["Shoes"]},
    "both_disabled": {"operation": "sample", "shading": "SOLID", "hide_sidebar": True, "disable_viewport_objects": ["Cosha", "Shoes"]},
    "cosha_subsurf_off": {"operation": "sample", "shading": "SOLID", "hide_sidebar": True, "disable_modifiers": {"Cosha": ["Subdivision"]}},
    "shoes_armature_off": {"operation": "sample", "shading": "SOLID", "hide_sidebar": True, "disable_modifiers": {"Shoes": ["Armature"]}},
    "shoes_mirror_off": {"operation": "sample", "shading": "SOLID", "hide_sidebar": True, "disable_modifiers": {"Shoes": ["Mirror"]}},
    "close": {"operation": "close"},
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="+", choices=CASES)
    parser.add_argument("--seconds", type=float, default=16)
    args = parser.parse_args()
    for case in args.cases:
        request = dict(CASES[case])
        request["id"] = case + "_" + str(time.time_ns())
        if request["operation"] == "sample":
            request.update(seconds=args.seconds, warmup_seconds=2)
        path = FOLDER / "request.json"
        temporary = FOLDER / "request.client.tmp"
        temporary.write_text(json.dumps(request) + "\n", encoding="utf-8")
        os.replace(temporary, path)
        response_path = FOLDER / ("response_" + request["id"] + ".json")
        deadline = time.monotonic() + 90
        print(json.dumps({"case": case, "request": request, "waiting_for": str(response_path)}), flush=True)
        while not response_path.exists():
            if time.monotonic() > deadline:
                raise TimeoutError("Response missing; inspect current helper before retry: " + str(response_path))
            time.sleep(.25)
        report = json.loads(response_path.read_text(encoding="utf-8"))
        compact = {key: report.get(key) for key in (
            "completed", "id", "operation", "errors", "context", "runtime_errors",
            "observed_displayed_frame_change_hz", "evaluated_frame_count", "frame_evaluation_ms", "restored", "disk_unchanged")}
        compact["components"] = sorted(report.get("components", {}).items(), key=lambda row: -row[1]["total_ms"])[:20]
        print(json.dumps(compact, ensure_ascii=False), flush=True)
        if not report.get("completed"):
            raise RuntimeError("Sample failed; inspect restoration and retain recovery evidence: " + str(response_path))

if __name__ == "__main__":
    main()
