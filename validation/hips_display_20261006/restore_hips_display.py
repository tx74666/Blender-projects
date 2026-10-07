"""Restore only the backed-up Hips custom-shape scale in live Blender 5.1.

No artist file is saved by this script. Inspect the viewport and Ctrl+S only after
verification succeeds. Original backup metadata remains intact for audit/reuse.
"""
from pathlib import Path

_hips_prepare_path = Path(r"D:\Blender\Projects\Character\X\Validation\hips_display_20261006\prepare_hips_display.py")
exec(compile(_hips_prepare_path.read_text(encoding="utf-8"), str(_hips_prepare_path), "exec"), {"action": "restore"})
