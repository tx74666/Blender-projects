# Source-prepared control launcher

This file has not launched an application. Root alone invokes it after the new
Parent ACTUAL_START. It admits the final cfaa control harness and exact R5 ready
index; it does not launch the separate Sync/worker phase.

All path/SHA pairs are explicit CLI inputs: resource token, ready index, actual
Prepare report, protected artist, protected old workspace, R5 Source freeze,
complete package manifest and complete QA reference packet. The launcher itself
and physical Blender executable also require exact SHA arguments. The artist
requires its current PID, timezone-aware creation time and exact creation
FILETIME. FILETIME is authoritative because WMI creation UTC may truncate the
last sub-microsecond digit.

The START schema is `x.validation.fresh-native-resource-start/1`; Root writes it
only after actual Parent START. Its owner, Parent, control-only scope, one-process
limit and ready-index SHA must match. Optional `free_mib`/`used_percent` remain
historical START evidence. Fresh live RAM is read before launch: at least 200 MiB
available, with a reread after two seconds when usage reaches 98%. The START
window is fifteen minutes. A durable exclusive claim hashes the opaque token
itself, so copying its JSON cannot replay it.

`--output-root` and `--launcher-evidence` are different empty owned ROUND
children. Only the latter receives OS receipts/stdout/stderr before the harness
claims its own output. `--profile-root` is a short fresh child of `D:/Codex/XV`
with empty CONFIG/DATAFILES. The actual source-cache derived path must remain
below 260 UTF-16 units. Root creates these empty directories; source preparation
does not create a native run.

The live process inventory must contain exactly the current protected artist
Blender process, with exact PID, FILETIME and executable path. The physical
executable's Windows version resource must identify Blender 5.2. The new process
uses a plain `subprocess.Popen` argument list, `shell=False`, factory startup,
disabled autoexec, one thread, no background flag and no hidden interactive
window. It loads the entire frozen package through the harness.

The parent process retains the child handle and polls every second while Root
can inspect its durable receipt and harness progress through an exec session.
No blocking sleep exceeds two seconds. No process is killed or restarted.
Normal process exit is recorded even if subsequent protection checks fail. A
successful launcher result additionally requires exit code zero, the actual
completed control report tied to the same input tuple, unchanged artist/old
workspace hashes, and only the same artist process remaining.

An interruption leaves the child intact and records its PID/status for Root;
it never authorizes a second process or grant reuse. This receipt does not turn
the partial control/save probe into visible UI, physical FBX, Unity Apply or
Original X Rig acceptance. The old artist's unsaved state is never adopted or
saved by this flow.
