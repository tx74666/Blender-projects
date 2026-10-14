"""Read-only bounded source protection check; does not compile or invoke Unity."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RELATIVE = Path("unity_runtime/Editor/ForearmCorrectionImporter.cs")
BASE = ROOT / "forearm_roll_07712_runtime/character_designer" / RELATIVE
SOURCE = Path("D:/MyRepository/Blender-addons-by-Randy/addons/character_designer") / RELATIVE


def section(text, start, end=None):
    begin = text.index(start)
    return text[begin:text.index(end, begin) if end else len(text)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


before, after = BASE.read_text(encoding="utf-8"), SOURCE.read_text(encoding="utf-8")
checks = {}
checks["export_dto_unchanged"] = before.split("        static readonly HashSet<string> Pending")[0] == after.split("        static readonly HashSet<string> Pending")[0]
checks["model_preprocess_unchanged"] = section(before, "        void OnPreprocessModel()", "        static void OnPostprocessAllAssets") == section(after, "        void OnPreprocessModel()", "        static void OnPostprocessAllAssets")
checks["sidecar_checksum_schema_unchanged"] = section(before, "        public static ExportFile ReadVerified", "        public static string Build") == section(after, "        public static ExportFile ReadVerified", "        public static string Build")
old_build = section(before, "        public static string Build", "        static string ProjectAssetPath")
new_build = section(after, "        public static string Build", "        static string ProjectAssetPath")
for allowed in (
    "                    data.name = Path.GetFileNameWithoutExtension(target);\n",
    "                Pending.Remove(path);\n",
    "                Ready.Remove(path);\n",
    "                SavePending();\n",
):
    if new_build.count(allowed) != 1:
        raise AssertionError("Expected one bounded Build addition: " + allowed.strip())
    new_build = new_build.replace(allowed, "", 1)
checks["entire_build_except_name_and_queue_ack_unchanged"] = old_build == new_build
checks["path_backup_convert_geometry_runtime_contracts_unchanged"] = section(before, "        static string ProjectAssetPath") == section(after, "        static string ProjectAssetPath")
checks["only_ready_paths_drained"] = "var paths = new List<string>(Ready);\n            Ready.Clear();" in section(after, "        static void Drain()", "        [MenuItem")
checks["all_pending_paths_saved"] = "new List<string>(Pending)" in section(after, "        static void SavePending()", "        static void SchedulePending()")
schedule = section(after, "        static void SchedulePending()", "        static string Sidecar")
drain = section(after, "        static void Drain()", "        [MenuItem")
checks["one_editor_update_subscription"] = schedule.count("EditorApplication.update += Drain;") == 1 and "delayCall" not in schedule
checks["update_unsubscribed_before_busy_check"] = drain.index("EditorApplication.update -= Drain;") < drain.index("scheduled = false;") < drain.index("EditorApplication.isPlayingOrWillChangePlaymode")
checks["retry_only_while_editor_busy"] = drain.count("SchedulePending();") == 1 and "SchedulePending();\n                return;" in drain
report = {
    "scope": "Source preservation only; native C# compile/reload acceptance remains with Character.",
    "baseline": str(BASE), "source": str(SOURCE),
    "baseline_sha256": sha(BASE), "source_sha256": sha(SOURCE),
    "checks": checks, "passed": all(checks.values()),
    "session_limit": "SessionState survives assembly reload in the current Editor; it clears on Editor exit.",
    "documentation": "https://docs.unity.com/ja-jp/engine/6000.5/script-reference/unityeditor/sessionstate",
}
(ROOT / "unity_queue_patch_contract_07714_20261010.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"passed": report["passed"], "source_sha256": report["source_sha256"], "checks": checks}))
raise SystemExit(0 if report["passed"] else 1)
