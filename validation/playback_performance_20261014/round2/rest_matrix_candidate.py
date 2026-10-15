"""Scratch candidate; two fresh native matrix reads within one Rest proof.

No cross-call cache and no Blender imports. Not deployed runtime code.
"""


def _same_rest_bone(original, preview):
    """Connected is the only structural flag changed by our disposable data copy."""
    if (original.parent.name if original.parent else None) != (preview.parent.name if preview.parent else None):
        return False
    if any(getattr(original, field) != getattr(preview, field) for field in
           ("use_deform", "use_inherit_rotation", "inherit_scale", "use_local_location", "use_relative_parent")):
        return False
    if (original.head_local - preview.head_local).length > 1e-6 or (original.tail_local - preview.tail_local).length > 1e-6:
        return False
    original_matrix = original.matrix_local
    preview_matrix = preview.matrix_local
    return max(abs(original_matrix[i][j] - preview_matrix[i][j])
               for i in range(4) for j in range(4)) <= 1e-6
