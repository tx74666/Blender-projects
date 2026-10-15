"""Count exact weight reuse in a disposable Round 2 Blender process.

Call only after the existing assertions pass, outside all ABBA timing blocks.
This helper neither opens files nor saves scenes. It clears the disposable
Forearm runtime caches, evaluates the requested frames and returns compact
statistics; the caller owns any report write. No per-vertex arrays are returned.
"""

from collections import Counter
import sys


def probe(runtime, geometry, scene, frames=(5, 9)):
    """Observe each calculation independently without changing math results."""
    import bpy
    if not bpy.app.background:
        raise RuntimeError('Use this probe only in a disposable background Blender process')

    frames = tuple(frames)
    if not frames or any(type(frame) is not int for frame in frames):
        raise ValueError("Probe frames must be a nonempty sequence of integers")
    calculate_code = runtime._calculate_records.__code__
    corrected_code = geometry.corrected_vertex.__code__
    previous_profile = sys.getprofile()
    calculations, active, pending, issues = [], [], {}, []
    requested_frame = None
    errors_by_frame = []
    orphan_corrected_calls = 0

    def profile(frame, event, argument):
        nonlocal orphan_corrected_calls
        try:
            code, identity = frame.f_code, id(frame)
            if code is calculate_code:
                if event == "call":
                    group = {"id": len(calculations) + 1, "frame": requested_frame,
                             "samples": [], "matrix_context": None,
                             "transform_names": None}
                    calculations.append(group)
                    active.append((identity, group))
                elif event == "return":
                    if active and active[-1][0] == identity:
                        active.pop()
                    else:
                        issues.append("Unbalanced calculation return")
                        active[:] = [item for item in active if item[0] != identity]
            elif code is corrected_code:
                if event == "call":
                    if not active:
                        orphan_corrected_calls += 1
                        return
                    group = active[-1][1]
                    values = frame.f_locals
                    names = tuple(values["transforms"])
                    rows = values.get("_matrix_rows")
                    context = id(rows if rows is not None else values["transforms"])
                    if group["matrix_context"] is None:
                        group["matrix_context"], group["transform_names"] = context, names
                    elif (group["matrix_context"] != context
                          or group["transform_names"] != names):
                        issues.append("Transform context changed within a calculation")
                    sample = {"weights": tuple(values["weights"].items()),
                              "names": names, "returned_success": False,
                              "inverse_success": False,
                              "max_condition": values["max_condition"]}
                    group["samples"].append(sample)
                    pending[identity] = sample
                elif event == "return":
                    sample = pending.pop(identity, None)
                    if sample is None:
                        return
                    sample["returned_success"] = argument is not None
                    # Zero-delta returns have no inverse local. A return after
                    # an exception has argument=None, even if inversion ran.
                    sample["inverse_success"] = (argument is not None
                                                  and "inverse" in frame.f_locals)
        except Exception as exc:
            # A broken diagnostic must not alter native correction or recovery.
            issues.append("Profile capture failed: " + type(exc).__name__ + ": " + str(exc))

    sys.setprofile(profile)
    try:
        for requested_frame in frames:
            runtime._CACHE.clear()
            runtime._OUTPUT_CACHE.clear()
            runtime.validation_cache.clear()
            scene.frame_set(requested_frame)
            bpy.context.view_layer.update()
            errors_by_frame.append({"frame": requested_frame,
                                    "errors": dict(runtime._ERRORS)})
    finally:
        sys.setprofile(previous_profile)
    if active or pending:
        issues.append("Profile ended with unfinished native calls")
    if orphan_corrected_calls:
        issues.append("Correction calls occurred outside the selected calculation")

    def histogram(counter):
        return dict(sorted(Counter(counter.values()).items()))

    rows = []
    for group in calculations:
        actual, desired, inverse_actual, inverse_thresholds = Counter(), Counter(), Counter(), Counter()
        failed = normalized = empty = 0
        for sample in group["samples"]:
            if not sample["returned_success"]:
                failed += 1
            try:
                # Normalization is pure membership/scalar math. Run it only
                # after profiling ends, without reading native matrix values.
                membership = dict.fromkeys(sample["names"])
                once = geometry._weights(membership, dict(sample["weights"]))
                twice = geometry._weights(membership, once)
                actual_key, desired_key = tuple(once.items()), tuple(twice.items())
            except Exception as exc:
                issues.append("Offline normalization failed: " + type(exc).__name__ + ": " + str(exc))
                continue
            normalized += 1
            empty += not actual_key
            actual[actual_key] += 1
            desired[desired_key] += 1
            if sample["inverse_success"]:
                inverse_actual[actual_key] += 1
                inverse_thresholds[(actual_key, sample["max_condition"])] += 1
        rows.append({"calculation": group["id"], "frame": group["frame"],
                     "N": len(group["samples"]), "normalized_N": normalized,
                     "failed_correction_returns": failed, "empty_weight_N": empty,
                     "U_actual": len(actual), "U_desired": len(desired),
                     "possible_blend_savings": 2 * normalized - len(actual) - len(desired),
                     "possible_weighted_blend_savings":
                         sum(count - 1 for key, count in actual.items() if key)
                         + sum(count - 1 for key, count in desired.items() if key),
                     "actual_group_size_histogram": histogram(actual),
                     "desired_group_size_histogram": histogram(desired),
                     "inverse_success_N": sum(inverse_actual.values()),
                     "inverse_unique_actual": len(inverse_actual),
                     "inverse_unique_actual_and_threshold": len(inverse_thresholds),
                     "possible_inverse_reuses":
                         sum(inverse_actual.values()) - len(inverse_actual)})
    if not any(row["N"] for row in rows):
        issues.append("No correction calls were observed; do not infer reuse")
    if any(row["failed_correction_returns"] for row in rows):
        issues.append("A correction failed; hypothetical savings are not a valid-pose result")
    if any(item["errors"] for item in errors_by_frame):
        issues.append("Native runtime reported errors during the probe")
    return {"schema": "x.forearm-weight-reuse-probe/1", "completed": not issues,
            "frames": list(frames), "calculations": rows, "issues": issues,
            "orphan_corrected_calls": orphan_corrected_calls,
            "errors_by_frame": errors_by_frame,
            "previous_profile_restored": sys.getprofile() is previous_profile,
            "limits": ["Diagnostic evaluation is outside ABBA timings; no speedup is measured.",
                       "Groups are exact ordered normalized weights within each calculation only.",
                       "Desired/actual normalization paths remain separate; no result cache was added.",
                       "Possible blend savings include empty-weight Identity construction; weighted savings exclude it.",
                       "Inverse reuse is counted only after a successful return with an inverse local.",
                       "Native per-point checks remain unchanged; failed probes cannot justify a cache.",
                       "No scene save, file open, artist refresh or per-vertex arrays in this report."]}
