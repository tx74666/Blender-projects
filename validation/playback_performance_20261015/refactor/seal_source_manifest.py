"""Seal the staged package and preserved authoring oracle without Blender.

Only hashes/source metadata are written. Invoke after root's source integration
has reached a reviewable state, immediately before a permitted native run.
"""
import argparse
import ast
import datetime
import hashlib
import json
from pathlib import Path


AUTHORING_FUNCTIONS = (
    "_input_mix", "_calculate_object", "_calculate_records", "_prepare_runtime_records",
    "_current_record", "_weights", "_resolve_rig", "_managed_key", "_rest_signature",
)


def pin(path):
    raw = Path(path).read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def functions(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    nodes = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return {name: hashlib.sha256(ast.dump(nodes[name], include_attributes=False).encode("utf-8")).hexdigest()
            for name in AUTHORING_FUNCTIONS}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--addons", required=True)
    parser.add_argument("--reference-runtime", required=True)
    parser.add_argument("--reference-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    package = (Path(args.addons).resolve() / "character_designer").resolve()
    reference = Path(args.reference_runtime).resolve()
    reference_pin = pin(reference)
    if reference_pin["sha256"] != args.reference_sha256.lower():
        raise RuntimeError("Reference .41 authoring runtime changed")
    if functions(package / "forearm_twist.py") != functions(reference):
        raise RuntimeError("Pinned authoring comparison functions differ from .41 reference")
    output = Path(args.output).resolve()
    if output.exists():
        raise RuntimeError("Do not overwrite a sealed source manifest")
    files = {str(path.relative_to(package)).replace("\\", "/"): pin(path)
             for path in sorted(package.rglob("*.py")) if "__pycache__" not in path.parts}
    if not files or "forearm_twist_playback_core.py" not in files:
        raise RuntimeError("Frozen playback core is absent from the staged package")
    manifest = {
        "schema": "x.frozen-playback-source-seal/1",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "package": str(package), "files": files,
        "model": "gpt-6.1-sol", "reasoning_effort": "ultra",
        "model_source": "Current root task local index verified by root; inherited task settings.",
        "reference_authoring_runtime": {"path": str(reference), **reference_pin},
        "preserved_authoring_function_ast_sha256": functions(reference),
        "limits": ["AST equality covers named authoring functions, not an unconditional package equivalence claim.",
                   "Every staged Python source is separately pinned and must be reviewed before native execution."],
    }
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(output), "files": len(files), "authoring_functions": len(AUTHORING_FUNCTIONS)}))


if __name__ == "__main__":
    main()
