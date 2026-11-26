"""Make a relocatable Blender scene from the exact saved X checkpoint. Requires Python 3."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verify(path, expected):
    if not path.is_file() or digest(path) != expected:
        raise ValueError(f"Missing or changed file: {path}. Check the version and run git lfs pull.")


def publish_copy(path, expected, writer):
    if path.exists():
        verify(path, expected)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent) as temp:
        candidate = Path(temp) / "verified-file"
        with candidate.open("wb") as output:
            writer(output)
        verify(candidate, expected)
        # Exclusive creation preserves edits made between checking and finishing.
        path.hardlink_to(candidate)


def restore():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "project_dependencies/X-checkpoint-manifest.json").read_text(encoding="utf-8"))
    source = root / "X.blend"
    verify(source, manifest["source_sha256"])

    def destination(relative):
        path = (root / relative).resolve()
        if root not in path.parents:
            raise ValueError(f"Dependency outside the checkout: {relative}")
        return path

    for relative, expected in manifest["dependencies"].items():
        verify(destination(relative), expected)
    with source.open("rb") as scene:
        for relative, spec in manifest["embedded_textures"].items():
            scene.seek(spec["offset"])
            content = scene.read(spec["size"])
            publish_copy(destination(relative), spec["sha256"], lambda output: output.write(content))

        def write_scene(output):
            scene.seek(0)
            shutil.copyfileobj(scene, output, length=1024 * 1024)
            for field in manifest["path_fields"]:
                value = ("//" + field["file"]).encode("utf-8") + b"\0"
                if len(value) > field["width"]:
                    raise ValueError(f"Path exceeds the saved field: {field['file']}")
                output.seek(field["offset"])
                output.write(value.ljust(field["width"], b"\0"))

        portable = root / "X-portable.blend"
        publish_copy(portable, manifest["portable_sha256"], write_scene)
        print(f"Open {portable} in Blender 5.2.")


if __name__ == "__main__":
    restore()
