using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using CharacterDesigner.Unity;
using MagicaCloth2;
using Unity.RandomRealm.CharacterPhysics;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace Unity.RandomRealm.Editor
{
    // Explicit QA only. All pose, physics and render changes are on owned clones.
    internal static class CharacterPoseStressVerification
    {
        const string PlayerPath = "Assets/Prefabs/Characters/Cosha/Cosha.Player.prefab";
        const string ModelPath = "Assets/Art/Character/Cosha/Cosha.fbx";
        const string SetupPath = "Assets/Prefabs/Characters/Cosha/Cosha.Setup.asset";
        const string PhysicsPath = "Assets/Prefabs/Characters/Cosha/Cosha.Player.Physics.asset";
        const string OutputRoot = "Logs/CharacterTuning/PoseStress";
        const string MenuRoot = "Tools/RandomRealm/Character/Pose Stress/";
        const string CleanupTicketKey = "RandomRealm.Character.PoseStress.OwnedCleanupTicket";
        static Run active;
        static bool recoveryScheduled;

        [MenuItem(MenuRoot + "Verify Arms (Transient Play)")] static void Arms() => Start("arms");
        [MenuItem(MenuRoot + "Verify Legs Squat Lunge (Transient Play)")] static void Legs() => Start("legs");
        [MenuItem(MenuRoot + "Verify Splits (Transient Play)")] static void Splits() => Start("splits");
        [MenuItem(MenuRoot + "Verify Dress Collision Baseline (Transient Play)")] static void DressCollisionBaseline() => Start("dressCollisionBaseline");
        [MenuItem(MenuRoot + "Verify Dress Collision Reference (Transient Play)")] static void DressCollisionReference() => Start("dressCollisionReference");
        [MenuItem(MenuRoot + "Verify Current Dress Only (Transient Play)")] static void CurrentDress() => Start("dressCurrent");
        [MenuItem(MenuRoot + "Cancel")] static void Cancel() { if (active != null) active.Abort("Cancelled explicitly."); else RecoverInterruptedRun(); }
        [MenuItem(MenuRoot + "Verify Pose Endpoints (Isolated)")]
        static void Endpoints()
        {
            if (active != null) { UnityEngine.Debug.Log("[Character pose stress] A batch is already running."); return; }
            try
            {
                Require(Unity.Multiplayer.PlayMode.CurrentPlayer.IsMainEditor && !EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling && !EditorApplication.isUpdating && !AnimationMode.InAnimationMode(), "Requires the idle main Editor.");
                Require(string.IsNullOrEmpty(SessionState.GetString(CleanupTicketKey, "")), "An owned Character cleanup ticket is still pending.");
                Require(!CharacterPhysicsPersistence.IsRestorePending, "Existing physics restore is pending.");
                var run = new Run("endpoints"); active = run; run.VerifyEndpoints();
            }
            catch (Exception e) { active = null; UnityEngine.Debug.LogWarning("[Character pose stress] Endpoint verification not started: " + e); }
        }

        [Serializable] internal sealed class SceneProof { public string handle, path; public int roots, dirtyId; public bool loaded, dirty, active; }
        [Serializable] internal sealed class FileProof { public string path, hash; public long length, ticks; public int assetDirtyCount; }
        [Serializable] internal sealed class ClothStats
        {
            public string part; public int particles, simulatedFrames;
            public float maximumDeflection, maximumSpeed, recoveryTailSpeed, fixedRootError;
            public int movingParticleSamples, retainedNormalSamples, freshNormalChanges, freshNormalFrames, nativeFrames, nativeSubsteps, attachmentTailFrames;
            public float attachmentMaximumSpeed, attachmentRecoveryTailSpeed;
            public float maximumNativeComponentStepMetres, maximumNativeComponentStepDegrees, teleportDistance, teleportRotation; public string teleportMode, nativeCenterPath;
            public string attachmentLimits = "Current-Dress response uses Waist translation/rotation removed in world metres; scale is not divided. Contact normals can persist in Edge mode; fresh Pre/Post changes are sufficient friction/proximity witnesses, not contact frequency or rendered-triangle penetration acceptance. Settling uses the existing QA 0.35 m/s tail threshold, not an art or game acceptance threshold.";
            public string limits = "Finite particles, speed and root stability are diagnostics; these do not prove that rendered cloth avoids body penetration.";
        }
        [Serializable] internal sealed class ClothSnapshot
        {
            public string part, phase; public int frame, registeredColliders, colliderCapacity;
            public Vector3[] particles, animationBase; public int[] triangles;
            public Vector3 attachmentWorldPosition; public Quaternion attachmentWorldRotation;
            public Vector3[] attachmentParticles, contactNormals, contactNormalsBefore; public bool[] moving;
            public int nativeSubsteps;
            public string[] bonePaths; public Vector3[] bonePositions; public Quaternion[] boneRotations;
            public string space = "Positions in owned clone local metres; bone rotations are world rotations. Proxy triangles use local particle indices. Diagnostic snapshot, not intersection acceptance.";
        }
        [Serializable] internal sealed class CaseResult
        {
            public string pose; public int entryFrames, holdFrames, recoveryFrames, settleFrames;
            public CharacterDressDynamicStressDriver.Proof dynamicInput;
            public bool attachmentSettled; public float settlingThresholdMetresPerSecond = .35f;
            public CharacterStressPoseDriver.Measurement heldPose;
            public float bodyRecoveryError;
            public List<ClothStats> cloth = new();
            public List<CharacterStressGeometry.Sample> geometry = new();
            public List<string> images = new();
            public List<ClothSnapshot> solver = new();
            public bool numericalChecksCompleted;
        }
        [Serializable] internal sealed class Report
        {
            public string id, batch, startedUtc, completedUtc, phase, error, output, fixturePath, startScenePath, modelHash, avatarPath;
            public bool endpointOnly, enteredPlay, returnedToIdleEdit, scenesPreserved, filesPreserved, selectionPreserved, previewScenesPreserved, numericalChecksCompleted;
            public bool userSavesPreserved, previousStartScenePreserved, builderLeaseReleased, cleanupTicketCleared;
            public string dressParameters; // Populated only by the isolated current-Dress route.
            public string walkBinding;
            public bool nativeContactObserved;
            public string contactLimits = "Edge-mode normals can persist after contact ends. A nonzero Pre/Post direction change in a real solver frame is a sufficient fresh collider-normal witness; unchanged/zero normals cannot establish contact frequency or absence. Normals describe friction/proximity at the final solver substep, not rendered-surface penetration or necessarily the displayed interpolated particle pose.";
            public string visualAcceptance = "Pending actual image review; numerical completion is not an art/penetration pass.";
            public string method = "Current production Player plus saved Physics profile restored on an isolated clone. Anatomical endpoint pose transitions run in real Magica frames. Physics-off reference has identical body pose and original unsimulated cloth bones. An owned camera/light-only playModeStartScene avoids unrelated Adventure startup; the previous start setting and original dirty Edit scenes are checked on exit. No authored motion, original scene save, production profile or FBX writes.";
            public List<SceneProof> originalScenes;
            public List<FileProof> protectedFiles = new();
            public List<CaseResult> cases = new();
            public List<string> logs = new();
            public List<ClothSnapshot> neutralSolver = new();
        }
        [Serializable] sealed class SceneList { public List<SceneProof> scenes; }
        [Serializable] sealed class CleanupTicket { public string reportPath, previousStartScenePath; }

        static void ClearCleanupTicket(string expected)
        {
            if (!string.IsNullOrEmpty(expected) && SessionState.GetString(CleanupTicketKey, "") == expected) SessionState.EraseString(CleanupTicketKey);
        }
        static void RestoreInterruptedStart(CleanupTicket ticket, string ownedStartScenePath)
        {
            string current = AssetDatabase.GetAssetPath(EditorSceneManager.playModeStartScene);
            if (current == ticket.previousStartScenePath) return;
            Require(!string.IsNullOrEmpty(ownedStartScenePath) && current == ownedStartScenePath, "Play start setting changed outside this owned run; it was not overwritten.");
            var previous = string.IsNullOrEmpty(ticket.previousStartScenePath) ? null : AssetDatabase.LoadAssetAtPath<SceneAsset>(ticket.previousStartScenePath);
            Require(string.IsNullOrEmpty(ticket.previousStartScenePath) || previous != null, "Previous Play start scene is unavailable.");
            EditorSceneManager.playModeStartScene = previous;
            Require(AssetDatabase.GetAssetPath(EditorSceneManager.playModeStartScene) == ticket.previousStartScenePath, "Previous Play start setting was not restored.");
        }
        [InitializeOnLoadMethod]
        static void RecoverInterruptedRun()
        {
            // No ticket means no callback, scans or global cleanup. This ticket is created only
            // after this Run acquires the otherwise exclusive Builder verification lease.
            if (recoveryScheduled || active != null || string.IsNullOrEmpty(SessionState.GetString(CleanupTicketKey, ""))) return;
            recoveryScheduled = true;
            EditorApplication.delayCall += Schedule;
            void Schedule()
            {
                string expected = SessionState.GetString(CleanupTicketKey, "");
                if (active != null || string.IsNullOrEmpty(expected) || !Unity.Multiplayer.PlayMode.CurrentPlayer.IsMainEditor) { recoveryScheduled = false; return; }
                CleanupTicket ticket;
                try
                {
                    ticket = JsonUtility.FromJson<CleanupTicket>(expected);
                    string root = Path.GetFullPath(OutputRoot) + Path.DirectorySeparatorChar;
                    Require(ticket != null && !string.IsNullOrEmpty(ticket.reportPath) && Path.GetFullPath(ticket.reportPath).StartsWith(root, StringComparison.OrdinalIgnoreCase) && Path.GetFileName(ticket.reportPath) == "verification.json", "Invalid owned Character cleanup ticket; no shared state was changed.");
                    string id = Path.GetFileName(Path.GetDirectoryName(ticket.reportPath));
                    Require(id.Length == 24 && id[8] == '-' && id[15] == '-' && Path.GetFullPath(Path.Combine(root, id, "verification.json")) == Path.GetFullPath(ticket.reportPath), "Cleanup ticket must identify one owned QA run directory.");
                }
                catch (Exception e) { recoveryScheduled = false; UnityEngine.Debug.LogError("[Character pose stress] " + e.Message); return; }
                double began = EditorApplication.timeSinceStartup; bool timeoutReported = false;
                EditorApplication.CallbackFunction tick = null;
                tick = () =>
                {
                    if (SessionState.GetString(CleanupTicketKey, "") != expected || active != null) { Detach(); return; }
                    if (EditorApplication.isPlayingOrWillChangePlaymode)
                    {
                        try { EditorApplication.isPlaying = false; }
                        catch (Exception e) { Detach(); UnityEngine.Debug.LogError("[Character pose stress] Native Play stop failed; owned ticket/lease retained: " + e); return; }
                        if (!timeoutReported && EditorApplication.timeSinceStartup - began > 10d) { timeoutReported = true; UnityEngine.Debug.LogError("[Character pose stress] Interrupted run still awaits native Play exit; owned lease retained."); }
                        return;
                    }
                    if (EditorApplication.isCompiling || EditorApplication.isUpdating) return;
                    Detach(); Report report = null; bool leaseReleased = false;
                    try
                    {
                        report = JsonUtility.FromJson<Report>(File.ReadAllText(ticket.reportPath));
                        Require(report != null && Path.GetFullPath(Path.Combine(report.output, "verification.json")) == Path.GetFullPath(ticket.reportPath), "Interrupted report does not match its owned cleanup ticket.");
                        report.numericalChecksCompleted = false; report.phase = "Failed: assembly reload interruption"; report.completedUtc = DateTime.UtcNow.ToString("O");
                        report.error = (report.error ?? "") + "\nAssembly reload interrupted QA; residual cleanup is not validation acceptance.";
                        report.returnedToIdleEdit = true; report.builderLeaseReleased = report.previousStartScenePreserved = report.cleanupTicketCleared = false;
                    }
                    catch (Exception e) { report = null; UnityEngine.Debug.LogError("[Character pose stress] Interrupted report read failed: " + e); }
                    string ownedStart = report != null ? report.startScenePath : "Assets/~Temp/CharacterPoseStress/" + Path.GetFileName(Path.GetDirectoryName(ticket.reportPath)) + "/PoseStress.Start.unity";
                    try { RestoreInterruptedStart(ticket, ownedStart); if (report != null) report.previousStartScenePreserved = true; }
                    catch (Exception e) { if (report != null) report.error += "\nResidual setting cleanup: " + e; UnityEngine.Debug.LogError("[Character pose stress] Residual setting cleanup: " + e); }
                    // The bool-only Builder API has no generation token: while this ticket
                    // exists, no other task may cancel/re-arm its lease under the writer protocol.
                    // Report I/O or setting conflicts must not block release of this owned lease.
                    try
                    {
                        BuilderAutoSaveLoad.CancelTransientVerificationPlayCycle();
                        Require(!BuilderAutoSaveLoad.IsTransientVerificationPlayCycleArmed, "Interrupted owned Builder lease was not released.");
                        leaseReleased = true;
                    }
                    catch (Exception e) { if (report != null) report.error += "\nResidual lease cleanup: " + e; UnityEngine.Debug.LogError("[Character pose stress] Residual lease cleanup: " + e); }
                    if (leaseReleased) ClearCleanupTicket(expected);
                    if (report != null)
                    {
                        report.builderLeaseReleased = leaseReleased; report.cleanupTicketCleared = string.IsNullOrEmpty(SessionState.GetString(CleanupTicketKey, ""));
                        try { File.WriteAllText(ticket.reportPath, JsonUtility.ToJson(report, true)); }
                        catch (Exception e) { UnityEngine.Debug.LogError("[Character pose stress] Interrupted report write failed: " + e.Message); }
                    }
                };
                void Detach() { EditorApplication.update -= tick; recoveryScheduled = false; }
                EditorApplication.update += tick;
            }
        }

        static void Start(string batch)
        {
            if (active != null) { UnityEngine.Debug.Log("[Character pose stress] A batch is already running."); return; }
            try
            {
                Require(Unity.Multiplayer.PlayMode.CurrentPlayer.IsMainEditor && !EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling && !EditorApplication.isUpdating && !AnimationMode.InAnimationMode(), "Requires the idle main Editor.");
                Require(string.IsNullOrEmpty(SessionState.GetString(CleanupTicketKey, "")), "An owned Character cleanup ticket is still pending.");
                Require(EditorSettings.enterPlayModeOptionsEnabled && (EditorSettings.enterPlayModeOptions & EnterPlayModeOptions.DisableDomainReload) != 0 && (EditorSettings.enterPlayModeOptions & EnterPlayModeOptions.DisableSceneReload) == 0, "The verifier requires Disable Domain Reload and normal Scene Reload; it does not change these settings.");
                Require(!CharacterPhysicsPersistence.IsRestorePending, "Existing physics restore is pending.");
                for (int i = 0; i < SceneManager.sceneCount; i++) Require(SceneManager.GetSceneAt(i).path != "Assets/Scenes/Tools/CharacterTuning.unity", "The normal CharacterTuning persistence scene must not be loaded.");
                var run = new Run(batch); active = run; run.Begin();
            }
            catch (Exception e) { active = null; UnityEngine.Debug.LogWarning("[Character pose stress] Not started: " + e); }
        }
        static void Require(bool okay, string message) { if (!okay) throw new InvalidOperationException(message); }
        static bool Finite(float v) => !float.IsNaN(v) && !float.IsInfinity(v);
        static bool Finite(Vector3 v) => float.IsFinite(v.x) && float.IsFinite(v.y) && float.IsFinite(v.z);
        static bool Finite(Quaternion q) => float.IsFinite(q.x) && float.IsFinite(q.y) && float.IsFinite(q.z) && float.IsFinite(q.w);
        static bool CollisionBatch(string batch) => batch == "dressCollisionBaseline" || batch == "dressCollisionReference";
        static bool CurrentDressBatch(string batch) => batch == "dressCurrent";
        static string Hash(string path) { using var h = SHA256.Create(); using var f = File.OpenRead(path); return BitConverter.ToString(h.ComputeHash(f)).Replace("-", "").ToLowerInvariant(); }
        static List<SceneProof> Scenes()
        {
            var result = new List<SceneProof>(); Scene current = SceneManager.GetActiveScene();
            var dirtyId = typeof(Scene).GetProperty("dirtyID", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
            Require(dirtyId != null && dirtyId.PropertyType == typeof(int), "Scene dirty ID is required for preservation evidence.");
            for (int i = 0; i < SceneManager.sceneCount; i++) { var s = SceneManager.GetSceneAt(i); result.Add(new SceneProof { handle = s.handle.ToString(), path = s.path, roots = s.isLoaded ? s.rootCount : 0, dirtyId = (int)dirtyId.GetValue(s), loaded = s.isLoaded, dirty = s.isDirty, active = s == current }); }
            return result;
        }

        sealed class Run
        {
            readonly Report report;
            readonly Object[] selection; readonly Object activeSelection;
            readonly int previewCount;
            readonly SceneAsset previousStartScene;
            readonly Type mirrorPreviewType;
            readonly bool hadMirrorPreview;
            const System.Reflection.BindingFlags MirrorMembers = System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic;
            readonly double began = EditorApplication.timeSinceStartup;
            double stoppedAt, cleanupAt, idleEditAt;
            bool subscribed, stopping, completed, enterRequested, builderLease;
            readonly string builderSaveRoot = Path.Combine(Application.persistentDataPath, "BuilderSaves");
            readonly string[] builderSaveFiles;
            string pendingAbort;
            string cleanupTicketJson;
            Runtime runtime;
            public Run(string batch)
            {
                string id = DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N").Substring(0, 8);
                report = new Report { id = id, batch = batch, startedUtc = DateTime.UtcNow.ToString("O"), phase = "Preparing protected fixture", originalScenes = Scenes(), modelHash = Hash(ModelPath), output = Path.GetFullPath(OutputRoot + "/" + id) };
                selection = Selection.objects; activeSelection = Selection.activeObject; previewCount = EditorSceneManager.previewSceneCount; previousStartScene = EditorSceneManager.playModeStartScene;
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    mirrorPreviewType = assembly.GetType("Unity.RandomRealm.Gameplay.Rendering.Editor.PlanarMirrorSceneViewPreview");
                    if (mirrorPreviewType == null) continue;
                    Scene mirror = (Scene)mirrorPreviewType.GetField("s_PreviewScene", MirrorMembers).GetValue(null);
                    hadMirrorPreview = mirror.IsValid() && mirror.isLoaded && EditorSceneManager.IsPreviewScene(mirror);
                    break;
                }
                Directory.CreateDirectory(report.output);
                var paths = AssetDatabase.GetDependencies(new[] { PlayerPath, SetupPath, PhysicsPath }, true).Concat(new[] { ModelPath, PlayerPath, SetupPath, PhysicsPath });
                foreach (string path in paths.Distinct().Where(p => p.StartsWith("Assets/", StringComparison.Ordinal) && File.Exists(p)))
                {
                    Snapshot(path);
                    if (File.Exists(path + ".meta")) Snapshot(path + ".meta");
                }
                foreach (var s in report.originalScenes.Where(s => !string.IsNullOrEmpty(s.path) && File.Exists(s.path))) Snapshot(s.path);
                builderSaveFiles = SavedFiles();
                foreach (string save in builderSaveFiles) Snapshot(save);
                Write();
            }
            string[] SavedFiles() => Directory.Exists(builderSaveRoot)
                ? Directory.GetFiles(builderSaveRoot, "*", SearchOption.AllDirectories).OrderBy(p => p, StringComparer.Ordinal).ToArray()
                : Array.Empty<string>();
            void Snapshot(string path)
            {
                if (report.protectedFiles.Any(f => f.path == path)) return;
                var info = new FileInfo(path); Object asset = path.StartsWith("Assets/", StringComparison.Ordinal) ? AssetDatabase.LoadMainAssetAtPath(path) : null;
                report.protectedFiles.Add(new FileProof { path = path, hash = Hash(path), length = info.Length, ticks = info.LastWriteTimeUtc.Ticks, assetDirtyCount = asset != null ? EditorUtility.GetDirtyCount(asset) : -1 });
            }
            public void Begin()
            {
                try
                {
                    Require(BuilderAutoSaveLoad.TryArmTransientVerificationPlayCycle(out string leaseMessage), leaseMessage);
                    builderLease = true; report.logs.Add(leaseMessage + " No user Builder save/load is allowed in this QA cycle.");
                    cleanupTicketJson = JsonUtility.ToJson(new CleanupTicket { reportPath = Path.Combine(report.output, "verification.json"), previousStartScenePath = AssetDatabase.GetAssetPath(previousStartScene) });
                    SessionState.SetString(CleanupTicketKey, cleanupTicketJson);
                    PrepareFixture();
                    PrepareStartScene();
                    EditorApplication.update += Tick; EditorApplication.playModeStateChanged += OnPlay;
                    AssemblyReloadEvents.beforeAssemblyReload += OnReload; Application.logMessageReceived += OnLog;
                    subscribed = true; report.phase = "Waiting for owned fixture import"; Write();
                }
                catch (Exception e) { Error(e.ToString()); Finish(); }
            }
            public void VerifyEndpoints()
            {
                report.endpointOnly = true;
                report.method = "Current Player and saved Physics on an owned PreviewScene clone; actual anatomical endpoints, bone length, symmetry and neutral recovery only. No simulation or visual acceptance is claimed.";
                Scene preview = default; GameObject holder = null; CharacterStressPoseDriver driver = null; CharacterStressGeometry geometry = null;
                try
                {
                    PrepareFixture(); preview = EditorSceneManager.NewPreviewScene(); holder = new GameObject("Owned endpoint verification"); holder.SetActive(false); SceneManager.MoveGameObjectToScene(holder, preview);
                    var source = AssetDatabase.LoadAssetAtPath<GameObject>(report.fixturePath); Require(source != null, "QA fixture is missing.");
                    var clone = Object.Instantiate(source, holder.transform, false);
                    foreach (var c in clone.GetComponentsInChildren<MagicaCloth>(true)) c.enabled = false;
                    foreach (var c in clone.GetComponentsInChildren<ColliderComponent>(true)) c.enabled = false;
                    var animator = clone.GetComponentInChildren<Animator>(true); Require(animator != null, "Animator missing.");
                    animator.runtimeAnimatorController = null; animator.applyRootMotion = false; animator.fireEvents = false;
                    holder.SetActive(true); animator.Rebind(); animator.Update(0); animator.enabled = false;
                    Require(animator.GetBoneTransform(HumanBodyBones.Hips) != null, "Humanoid binding did not initialize.");
                    driver = new CharacterStressPoseDriver(animator); var corrections = clone.GetComponentsInChildren<ForearmCorrection>(true);
                    driver.Apply(driver.Names("arms")[0], 0); foreach (var c in corrections) Require(c.ApplyNow(out string e), "Neutral correction failed: " + e);
                    geometry = new CharacterStressGeometry(clone);
                    foreach (string pose in driver.Names("arms").Concat(driver.Names("legs")).Concat(driver.Names("splits")))
                    {
                        driver.Apply(pose, 1); foreach (var c in corrections) Require(c.ApplyNow(out string e), "Held correction failed: " + e);
                        var result = new CaseResult { pose = pose, heldPose = driver.Measure(pose) }; report.cases.Add(result); result.geometry.Add(geometry.Capture(pose, "endpoint"));
                        driver.Apply(pose, 0); foreach (var c in corrections) Require(c.ApplyNow(out string e), "Recovery correction failed: " + e);
                        result.bodyRecoveryError = driver.RecoveryError(); result.numericalChecksCompleted = result.heldPose.targetReached && result.bodyRecoveryError < .0001f && result.geometry.All(s => s.finite);
                    }
                }
                catch (Exception e) { Error(e.ToString()); }
                finally
                {
                    try { geometry?.Dispose(); } catch (Exception e) { Error("Geometry cleanup: " + e); }
                    try { driver?.RestoreOriginal(); } catch (Exception e) { Error("Pose cleanup: " + e); }
                    try { if (holder != null) Object.DestroyImmediate(holder); } catch (Exception e) { Error("Fixture cleanup: " + e); }
                    try { if (preview.IsValid()) EditorSceneManager.ClosePreviewScene(preview); } catch (Exception e) { Error("Preview cleanup: " + e); }
                    finally { Finish(); }
                }
            }
            void PrepareFixture()
            {
                Scene original = SceneManager.GetActiveScene(); Scene preview = EditorSceneManager.NewPreviewScene(); GameObject holder = null;
                try
                {
                    holder = new GameObject("Owned pose stress preparation"); holder.SetActive(false); SceneManager.MoveGameObjectToScene(holder, preview);
                    var source = AssetDatabase.LoadAssetAtPath<GameObject>(PlayerPath); Require(source != null, "Current Player is missing.");
                    var clone = Object.Instantiate(source, holder.transform, false); clone.name = "Cosha.PoseStress";
                    var saved = CharacterPhysicsPersistence.Load(source); Require(saved != null, "Saved physics profile is missing.");
                    if (CurrentDressBatch(report.batch))
                    {
                        report.method = "Dress-only native QA on current Player/current imported Cosha.fbx clones. Saved Dress parameters/three collision copies and explicit eight-root migration are isolated. Nine anatomical poses plus exact existing Walk_N two-cycle playback, root yaw and moving-root abrupt stop run in real Magica frames. Root input, Waist rigid-frame response and native contact normals are recorded; none proves rendered-triangle collision safety. Other cloth simulations remain disabled; Hair/settings/gameplay publication and Blender/Magica equivalence are not accepted. Production profile/Player/model/dirty scenes remain protected.";
                        var walkBinding = CharacterDressDynamicStressDriver.ResolveWalk(clone.GetComponentInChildren<Animator>(true));
                        report.walkBinding = walkBinding.proof;
                        var dress = CharacterDressOnlyStressPreparation.Prepare(clone, saved, report.logs.Add);
                        report.dressParameters = CharacterDressOnlyStressPreparation.ParameterState(dress);
                    }
                    else
                    {
                        RecordPhysics(clone, "production prefab before profile restore");
                        CharacterPhysicsPersistence.Restore(clone, saved);
                        RecordPhysics(clone, "owned fixture after saved profile restore");
                    }
                    Strip(clone, preserveHairMetadata: CurrentDressBatch(report.batch));
                    var animator = clone.GetComponentInChildren<Animator>(true); Require(animator != null && animator.avatar != null && animator.avatar.isValid && animator.avatar.isHuman, "Current Player has no valid Humanoid Avatar.");
                    report.avatarPath = AssetDatabase.GetAssetPath(animator.avatar);
                    string parent = "Assets/~Temp"; if (!AssetDatabase.IsValidFolder(parent)) AssetDatabase.CreateFolder("Assets", "~Temp");
                    string root = parent + "/CharacterPoseStress"; if (!AssetDatabase.IsValidFolder(root)) AssetDatabase.CreateFolder(parent, "CharacterPoseStress");
                    string folder = root + "/" + report.id; AssetDatabase.CreateFolder(root, report.id);
                    report.fixturePath = folder + "/Cosha.PoseStress.prefab";
                    PrefabUtility.SaveAsPrefabAsset(clone, report.fixturePath, out bool success); Require(success, "Could not save the owned QA fixture.");
                    report.logs.Add(CurrentDressBatch(report.batch) ? "fixture=current Player + bounded saved Dress only; QA component/colliders, Hair stationary, no whole-profile restore or Hair setup/apply" : "fixture=current Player + saved Physics profile, stripped gameplay only; source/Avatar/mesh/material assets retained");
                }
                finally { if (holder != null) Object.DestroyImmediate(holder); EditorSceneManager.ClosePreviewScene(preview); }
                Require(SceneManager.GetActiveScene() == original && JsonUtility.ToJson(new SceneList { scenes = Scenes() }) == JsonUtility.ToJson(new SceneList { scenes = report.originalScenes }), "Preparation changed the original scene.");
                Require(EditorSceneManager.previewSceneCount == previewCount, "Preparation leaked a PreviewScene.");
            }
            void RecordPhysics(GameObject root, string stage)
            {
                var rig = root.GetComponent<CharacterPhysicsRig>();
                report.logs.Add(stage + ": cloths=" + root.GetComponentsInChildren<MagicaCloth>(true).Length + ", colliders=" + root.GetComponentsInChildren<ColliderComponent>(true).Length + ", owned=" + rig.OwnedColliders.Count + ", reused=" + rig.ReusedColliders.Count);
                foreach (var cloth in new[] { rig.Dress, rig.Hair })
                {
                    Require(cloth != null, "Missing configured cloth at " + stage);
                    var links = cloth.SerializeData.colliderCollisionConstraint.colliderList;
                    report.logs.Add(stage + ": " + cloth.name + ", enabled=" + cloth.enabled + ", roots=" + cloth.SerializeData.rootBones.Count + ", collisionMode=" + cloth.SerializeData.colliderCollisionConstraint.mode);
                    foreach (var collider in links)
                    {
                        Require(collider != null, "Missing registered collider at " + stage);
                        int componentIndex = Array.IndexOf(collider.GetComponents<ColliderComponent>(), collider);
                        report.logs.Add(stage + ": registered=" + AnimationUtility.CalculateTransformPath(collider.transform, root.transform) + "/" + collider.GetType().Name + "#" + componentIndex + ", enabled=" + collider.enabled + ", active=" + collider.gameObject.activeSelf + ", center=" + collider.center + ", size=" + collider.GetSize());
                    }
                }
            }
            void PrepareStartScene()
            {
                const string template = "Assets/Scenes/Tools/CharacterPoseStress.Start.unity";
                string yaml = File.ReadAllText(template);
                Require(yaml.Contains("Camera:") && yaml.Contains("Light:") && !yaml.Contains("--- !u!1001") && !yaml.Contains("MeshRenderer:") && !yaml.Contains("SkinnedMeshRenderer:") && !yaml.Contains("Collider:"), "The camera/light-only QA template changed; review before copying.");
                Snapshot(template); Snapshot(template + ".meta");
                report.startScenePath = Path.GetDirectoryName(report.fixturePath).Replace('\\', '/') + "/PoseStress.Start.unity";
                Require(!File.Exists(report.startScenePath) && AssetDatabase.CopyAsset(template, report.startScenePath), "Cannot create the owned camera/light startup asset.");
                report.logs.Add("Startup is a private copy of the camera/light-only CharacterPoseStress.Start scene; its roots are disabled in the disposable Play copy.");
            }
            void OnPlay(PlayModeStateChange state)
            {
                if (completed || (stopping && state == PlayModeStateChange.EnteredPlayMode)) return;
                if (state == PlayModeStateChange.EnteredPlayMode)
                {
                    try
                    {
                        RestoreInterruptedStart(JsonUtility.FromJson<CleanupTicket>(cleanupTicketJson), report.startScenePath);
                        Require(EditorSceneManager.playModeStartScene == previousStartScene, "Previous Play start setting was not restored.");
                        report.enteredPlay = true;
                        // Only disposable Play copies are affected. Edit scene state is checked at exit.
                        for (int i = 0; i < SceneManager.sceneCount; i++) foreach (var root in SceneManager.GetSceneAt(i).GetRootGameObjects()) root.SetActive(false);
                        runtime = new Runtime(report, Stop); runtime.Begin();
                        report.phase = "Simulating " + report.batch; Write();
                    }
                    catch (Exception e) { Abort(e.ToString()); }
                }
                else if (state == PlayModeStateChange.ExitingPlayMode && !stopping) Abort("Play was stopped before completion.");
            }
            void Tick()
            {
                if (completed) return;
                try
                {
                    if (!stopping && !string.IsNullOrEmpty(pendingAbort)) { string error = pendingAbort; pendingAbort = null; Abort(error); }
                    if (!stopping && !enterRequested)
                    {
                        if (EditorApplication.isCompiling) { Abort("Unexpected compilation during fixture preparation."); return; }
                        if (EditorApplication.isUpdating) { if (EditorApplication.timeSinceStartup - began > 30d) Abort("Owned fixture import exceeded 30 seconds."); return; }
                        var startup = AssetDatabase.LoadAssetAtPath<SceneAsset>(report.startScenePath); if (startup == null) { Abort("Owned startup scene is missing."); return; }
                        EditorSceneManager.playModeStartScene = startup;
                        enterRequested = true; report.phase = "Entering Play"; Write(); EditorApplication.isPlaying = true; return;
                    }
                    if (!stopping && runtime != null && runtime.IsCompleting)
                    {
                        if (cleanupAt <= 0) cleanupAt = EditorApplication.timeSinceStartup;
                        if (EditorApplication.timeSinceStartup - cleanupAt > 10d) Stop("Owned scene cleanup did not complete within 10 seconds.");
                    }
                    if (!stopping && EditorApplication.timeSinceStartup - began > 180d) Abort("Batch exceeded 180 seconds, including entry and capture.");
                    if (!stopping && (EditorApplication.isCompiling || EditorApplication.isUpdating)) Abort("Compilation/import interrupted QA.");
                    if (stopping && EditorApplication.isPlayingOrWillChangePlaymode && EditorApplication.timeSinceStartup - stoppedAt > 10d) { Error("Cleanup/Play exit exceeded 10 seconds."); EditorApplication.isPlaying = false; }
                    if (stopping && !EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling && !EditorApplication.isUpdating)
                    {
                        if (idleEditAt <= 0) idleEditAt = EditorApplication.timeSinceStartup;
                        bool loaded = report.originalScenes.Where(s => s.loaded && !string.IsNullOrEmpty(s.path)).All(s => SceneManager.GetSceneByPath(s.path).isLoaded);
                        bool activeSceneRestored = report.originalScenes.Any(s => s.active && s.path == SceneManager.GetActiveScene().path);
                        if (EditorApplication.timeSinceStartup - idleEditAt >= .25d && loaded && activeSceneRestored) Finish();
                        else if (EditorApplication.timeSinceStartup - idleEditAt > 10d) { Error("Original Edit scenes did not return within 10 seconds; no scene repair was attempted."); Finish(); }
                        else EditorApplication.QueuePlayerLoopUpdate();
                    }
                    else EditorApplication.QueuePlayerLoopUpdate();
                }
                catch (Exception e) { Error(e.ToString()); Abort(e.ToString()); }
            }
            public void Abort(string error) { if (completed || stopping) return; Error(error); if (runtime != null) runtime.Complete(error); else Stop(error); }
            void Stop(string error)
            {
                if (stopping || completed) return; if (!string.IsNullOrEmpty(error)) Error(error);
                stopping = true; stoppedAt = EditorApplication.timeSinceStartup; report.phase = "Returning to Edit";
                try { Write(); } finally { EditorApplication.isPlaying = false; }
            }
            void OnLog(string m, string stack, LogType t)
            {
                if (t == LogType.Warning) report.logs.Add("warning: " + m);
                else if (t == LogType.Error || t == LogType.Exception || t == LogType.Assert) { Error("New shared Editor error: " + m); pendingAbort = "New shared Editor error: " + m; }
            }
            void OnReload()
            {
                if (completed) return;
                const string error = "Assembly reload interrupted QA.";
                Error(error); report.numericalChecksCompleted = false;
                try { runtime?.Complete(error); } catch (Exception e) { Error("Reload runtime cleanup: " + e); }
                try { Stop(error); EditorApplication.isPlaying = false; } catch (Exception e) { Error("Reload Play stop: " + e); }
                try { RestoreInterruptedStart(JsonUtility.FromJson<CleanupTicket>(cleanupTicketJson), report.startScenePath); } catch (Exception e) { Error("Reload start setting: " + e); }
                report.phase = "Failed: assembly reload interruption"; Write();
                // Reload can discard unload.completed and the Run's Tick. The owned SessionState
                // ticket survives until a native idle-Edit recovery releases this Run's lease.
            }
            void Error(string e) { if (string.IsNullOrEmpty(e) || (report.error ?? "").Contains(e)) return; report.error = string.IsNullOrEmpty(report.error) ? e : report.error + "\n" + e; }
            void Write()
            {
                try { File.WriteAllText(Path.Combine(report.output, "verification.json"), JsonUtility.ToJson(report, true)); }
                catch (Exception e) { Error("Evidence write failed: " + e.Message); report.numericalChecksCompleted = false; }
            }
            void Finish()
            {
                if (completed) return; completed = true;
                if (subscribed) { EditorApplication.update -= Tick; EditorApplication.playModeStateChanged -= OnPlay; AssemblyReloadEvents.beforeAssemblyReload -= OnReload; Application.logMessageReceived -= OnLog; }
                try
                {
                    RestoreInterruptedStart(new CleanupTicket { previousStartScenePath = AssetDatabase.GetAssetPath(previousStartScene) }, report.startScenePath);
                    report.returnedToIdleEdit = !EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling && !EditorApplication.isUpdating;
                    report.scenesPreserved = JsonUtility.ToJson(new SceneList { scenes = Scenes() }) == JsonUtility.ToJson(new SceneList { scenes = report.originalScenes });
                    Require(report.scenesPreserved, "Original scene state changed; QA does not save/reload/repair it.");
                    foreach (var f in report.protectedFiles)
                    {
                        var info = new FileInfo(f.path); Require(info.Exists && info.Length == f.length && info.LastWriteTimeUtc.Ticks == f.ticks && Hash(f.path) == f.hash, "Protected file changed: " + f.path);
                        Object asset = f.path.StartsWith("Assets/", StringComparison.Ordinal) ? AssetDatabase.LoadMainAssetAtPath(f.path) : null; if (asset != null && f.assetDirtyCount >= 0) Require(EditorUtility.GetDirtyCount(asset) == f.assetDirtyCount, "Protected asset dirty count changed: " + f.path);
                    }
                    report.filesPreserved = true;
                    report.userSavesPreserved = builderSaveFiles.SequenceEqual(SavedFiles(), StringComparer.Ordinal);
                    Require(report.userSavesPreserved, "User Builder save file list changed.");
                    report.previousStartScenePreserved = EditorSceneManager.playModeStartScene == previousStartScene;
                    Require(report.previousStartScenePreserved, "Previous Play start setting was not restored on exit.");
                    report.selectionPreserved = Selection.activeObject == activeSelection && Selection.objects.SequenceEqual(selection);
                    // Closing a disposable runtime scene can retire the shared mirror preview.
                    // Recreate only a previously existing preview through its normal render path.
                    if (hadMirrorPreview && mirrorPreviewType != null && !((Scene)mirrorPreviewType.GetField("s_PreviewScene", MirrorMembers).GetValue(null)).IsValid())
                        mirrorPreviewType.GetMethod("Tick", MirrorMembers).Invoke(null, null);
                    report.previewScenesPreserved = EditorSceneManager.previewSceneCount == previewCount;
                    Require(report.selectionPreserved && report.previewScenesPreserved, "Selection or PreviewScene count changed.");
                    if (CurrentDressBatch(report.batch)) report.nativeContactObserved = report.cases.SelectMany(c => c.cloth).Any(s => s.freshNormalChanges > 0);
                    report.numericalChecksCompleted = (!CurrentDressBatch(report.batch) || report.nativeContactObserved) && (report.enteredPlay || report.endpointOnly) && report.returnedToIdleEdit && string.IsNullOrEmpty(report.error) && report.cases.Count == (report.endpointOnly ? 21 : report.batch == "arms" || CollisionBatch(report.batch) ? 3 : CurrentDressBatch(report.batch) ? 12 : 9) && report.cases.All(c => c.numericalChecksCompleted);
                }
                catch (Exception e) { Error(e.ToString()); }
                try
                {
                    if (builderLease)
                    {
                        BuilderAutoSaveLoad.CancelTransientVerificationPlayCycle();
                        Require(!BuilderAutoSaveLoad.IsTransientVerificationPlayCycleArmed, "Owned Builder QA lease was not released.");
                        builderLease = false;
                    }
                    report.builderLeaseReleased = true;
                }
                catch (Exception e) { Error("Builder QA lease cleanup: " + e); }
                try
                {
                    if (report.builderLeaseReleased) ClearCleanupTicket(cleanupTicketJson);
                    report.cleanupTicketCleared = string.IsNullOrEmpty(SessionState.GetString(CleanupTicketKey, ""));
                    Require(report.cleanupTicketCleared, "Owned Character cleanup ticket was not cleared.");
                }
                catch (Exception e) { Error("Character cleanup ticket: " + e); }
                report.numericalChecksCompleted &= string.IsNullOrEmpty(report.error) && report.userSavesPreserved && report.previousStartScenePreserved && report.builderLeaseReleased && report.cleanupTicketCleared;
                report.phase = "Complete"; report.completedUtc = DateTime.UtcNow.ToString("O");
                try { Write(); } finally { active = null; }
                UnityEngine.Debug.Log("[Character pose stress] " + (report.numericalChecksCompleted ? "CAPTURE COMPLETE; visual review pending" : "FAILED") + "; " + Path.Combine(report.output, "verification.json"));
            }
        }

        static void Strip(GameObject clone, bool preserveHairMetadata = false)
        {
            bool Kept(Behaviour b) => b is Animator || b is MagicaCloth || b is ColliderComponent || b is ForearmCorrection || b is CharacterPhysicsRig || preserveHairMetadata && b is CharacterHairMotionRig;
            foreach (var b in clone.GetComponentsInChildren<Behaviour>(true)) if (!Kept(b)) b.enabled = false;
            var removals = clone.GetComponentsInChildren<MonoBehaviour>(true).Where(b => !Kept(b)).ToList();
            while (removals.Count > 0)
            {
                MonoBehaviour removable = null;
                foreach (var candidate in removals)
                {
                    bool required = false;
                    foreach (var other in removals.Where(b => b != candidate))
                        foreach (RequireComponent a in other.GetType().GetCustomAttributes(typeof(RequireComponent), true))
                            foreach (var f in typeof(RequireComponent).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance))
                                if (f.FieldType == typeof(Type) && f.GetValue(a) is Type type && type.IsAssignableFrom(candidate.GetType())) required = true;
                    if (!required) { removable = candidate; break; }
                }
                Require(removable != null, "Cannot strip a cloned gameplay dependency cycle."); removals.Remove(removable); Object.DestroyImmediate(removable);
            }
            foreach (var c in clone.GetComponentsInChildren<Collider>(true)) c.enabled = false;
            foreach (var body in clone.GetComponentsInChildren<Rigidbody>(true)) { body.isKinematic = true; body.detectCollisions = false; }
            foreach (var p in clone.GetComponentsInChildren<ParticleSystem>(true)) { var main = p.main; main.playOnAwake = false; p.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear); }
        }

        sealed class Runtime
        {
            readonly Report report; readonly Action<string> done;
            Scene scene; GameObject holder, clone, reference;
            CharacterStressPoseDriver driver, referenceDriver; CharacterStressGeometry geometry;
            CharacterDressDynamicStressDriver dynamicDriver; Transform dressAttachment;
            readonly Dictionary<MagicaCloth, Vector3[]> previousAttachment = new();
            readonly Dictionary<MagicaCloth, Vector3[]> normalsBefore = new(); int normalsBeforeFrame = -1; bool stopCaptured;
            float CaseHold => dynamicDriver != null && current != null && CharacterDressDynamicStressDriver.IsDynamic(current.pose) ? dynamicDriver.HoldSeconds(current.pose) : Hold;
            bool DynamicCase => dynamicDriver != null && current != null && CharacterDressDynamicStressDriver.IsDynamic(current.pose);
            MagicaCloth[] cloths; ForearmCorrection[] corrections;
            Camera camera; Light light; RenderTexture target; Texture2D pixels;
            string[] names; int index = -1, lastFrame = -1, lastPoseFrame = -1; float time, weight, warmup;
            Vector3 anatomyRight, anatomyUp, anatomyForward;
            bool ready, finished, entryCaptured, holdCaptured, recoveryCaptured, pendingNext;
            readonly Dictionary<MagicaCloth, Vector3[]> previous = new();
            readonly Dictionary<Transform, Vector3> fixedPositions = new();
            double began;
            CaseResult current;
            const float Enter = 1f, Hold = 2f, Recover = 1f, Settle = 2f;
            public bool IsCompleting => finished;
            public Runtime(Report report, Action<string> done) { this.report = report; this.done = done; }
            public void Begin()
            {
                began = EditorApplication.timeSinceStartup;
                scene = SceneManager.CreateScene("CharacterPoseStress_" + report.id);
                holder = new GameObject("Owned pose stress root"); holder.SetActive(false); SceneManager.MoveGameObjectToScene(holder, scene); holder.transform.position = new Vector3(0, -100, 0);
                var source = AssetDatabase.LoadAssetAtPath<GameObject>(report.fixturePath); Require(source != null, "QA fixture missing.");
                clone = Object.Instantiate(source, holder.transform, false); reference = Object.Instantiate(source, holder.transform, false);
                clone.name = "Current character — physics on"; reference.name = "Matched character — physics off";
                foreach (var t in clone.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = 31;
                foreach (var t in reference.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = 30;
                foreach (var c in reference.GetComponentsInChildren<MagicaCloth>(true)) c.enabled = false;
                foreach (var c in reference.GetComponentsInChildren<ColliderComponent>(true)) c.enabled = false;
                var rig = clone.GetComponent<CharacterPhysicsRig>();
                Require(rig != null && rig.Dress != null && (CurrentDressBatch(report.batch) || rig.Hair != null), "Required configured cloths are missing.");
                cloths = CurrentDressBatch(report.batch) ? new[] { rig.Dress } : new[] { rig.Dress, rig.Hair };
                foreach (var c in cloths) Require(c.SerializeData.clothType == ClothProcess.ClothType.BoneCloth, "Expected BoneCloth.");
                if (report.batch == "dressCollisionReference")
                {
                    rig.Dress.SerializeData.colliderCollisionConstraint.colliderList.Clear();
                    report.logs.Add("DIAGNOSTIC A/B: only this owned clone's Dress body-collider list is empty; Dress simulation/constraints, Hair collision and production profile are retained. This is not a proposed gameplay setting.");
                }
                var nativeWalk = CurrentDressBatch(report.batch) ? CharacterDressDynamicStressDriver.ResolveWalk(clone.GetComponentInChildren<Animator>(true)) : null;
                if (nativeWalk != null) Require(nativeWalk.proof == report.walkBinding, "Walk_N/controller/Avatar binding changed after fixture preparation.");
                foreach (var a in new[] { clone.GetComponentInChildren<Animator>(true), reference.GetComponentInChildren<Animator>(true) }) { Require(a != null, "Animator missing."); a.runtimeAnimatorController = null; a.applyRootMotion = false; a.fireEvents = false; a.cullingMode = AnimatorCullingMode.AlwaysAnimate; }
                holder.SetActive(true);
                foreach (var a in new[] { clone.GetComponentInChildren<Animator>(true), reference.GetComponentInChildren<Animator>(true) }) { a.Rebind(); a.Update(0); a.enabled = false; }
                driver = new CharacterStressPoseDriver(clone.GetComponentInChildren<Animator>(true)); referenceDriver = new CharacterStressPoseDriver(reference.GetComponentInChildren<Animator>(true));
                string poseBatch = CollisionBatch(report.batch) || CurrentDressBatch(report.batch) ? "legs" : report.batch;
                names = driver.Names(poseBatch); Require(names.Length > 0 && names.SequenceEqual(referenceDriver.Names(poseBatch)), "Missing pose batch.");
                if (CollisionBatch(report.batch)) names = new[] { "leg_forward_R90", "squat", "lunge_R" };
                if (CurrentDressBatch(report.batch))
                {
                    dynamicDriver = new CharacterDressDynamicStressDriver(clone, reference, nativeWalk);
                    names = names.Concat(CharacterDressDynamicStressDriver.Names).ToArray();
                    dressAttachment = cloths[0].SerializeData.rootBones[0].parent;
                    Require(dressAttachment != null && dressAttachment.name == "SK_Dress_Waist" && cloths[0].SerializeData.rootBones.All(b => b != null && b.parent == dressAttachment), "Missing exact shared Dress attachment frame.");
                }
                corrections = holder.GetComponentsInChildren<ForearmCorrection>(true);
                foreach (var r in holder.GetComponentsInChildren<SkinnedMeshRenderer>(true)) r.updateWhenOffscreen = true;
                var cameraObject = new GameObject("Owned capture camera"); cameraObject.transform.SetParent(holder.transform, false); camera = cameraObject.AddComponent<Camera>(); camera.enabled = false; camera.cameraType = CameraType.Preview; camera.scene = scene;
                camera.overrideSceneCullingMask = EditorSceneManager.GetSceneCullingMask(scene); camera.cullingMask = 1 << 31; camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = new Color(.16f, .18f, .22f); camera.fieldOfView = 32; camera.nearClipPlane = .02f; camera.farClipPlane = 30; camera.aspect = 2f / 3f;
                var lightObject = new GameObject("Owned capture light"); lightObject.transform.SetParent(holder.transform, false); light = lightObject.AddComponent<Light>(); light.type = LightType.Directional; light.enabled = false; light.cullingMask = (1 << 31) | (1 << 30); light.intensity = 1.3f; light.transform.rotation = Quaternion.Euler(35, -35, 0);
                target = new RenderTexture(600, 900, 24) { hideFlags = HideFlags.HideAndDontSave }; Require(target.Create(), "Capture target allocation failed."); pixels = new Texture2D(600, 900, TextureFormat.RGB24, false) { hideFlags = HideFlags.HideAndDontSave };
                MagicaManager.OnPreSimulation += Pre; MagicaManager.OnPostSimulation += Post; EditorApplication.update += Tick;
            }
            void Tick()
            {
                if (finished) return;
                try
                {
                    Require(EditorApplication.isPlaying && !EditorApplication.isCompiling && clone != null, "Play/compile interrupted runtime.");
                    Require(EditorApplication.timeSinceStartup - began < 160d, "Runtime exceeded 160 seconds.");
                    if (!ready && cloths.All(c => c != null && c.IsValid() && c.Process.IsRunning() && c.Process.IsEnable && c.Process.HasProxyMesh))
                    {
                        foreach (var c in cloths)
                        {
                            ref var team = ref MagicaManager.Team.GetTeamDataRef(c.Process.TeamId);
                            int count = team.UseColliderCount, capacity = team.colliderChunk.dataLength;
                            report.logs.Add("Native registered colliders: " + (c == cloths[0] ? "Dress" : "Hair") + "=" + count + ", capacity=" + capacity);
                            if (c == cloths[0] && report.batch == "dressCollisionReference") Require(count == 0 && capacity == 0, "Dress collision reference registered native colliders.");
                            if (CurrentDressBatch(report.batch)) Require(count == 3 && c.Process.ProxyMeshContainer.shareVirtualMesh.VertexCount == 32 && c.SerializeData.rootBones.Count == 8 && CharacterDressOnlyStressPreparation.ParameterState(c) == report.dressParameters, "Dress-only native topology/collider registration or parameters changed.");
                        }
                        ready = true; driver.Apply(names[0], 0); referenceDriver.Apply(names[0], 0);
                        var axes = driver.Measure(names[0]); anatomyRight = axes.anatomyRight; anatomyUp = axes.anatomyUp; anatomyForward = axes.anatomyForward;
                    }
                    EditorApplication.QueuePlayerLoopUpdate();
                }
                catch (Exception e) { Complete(e.ToString()); }
            }
            void Next()
            {
                index++; if (index >= names.Length) { Complete(null); return; }
                time = 0; entryCaptured = holdCaptured = recoveryCaptured = false; current = new CaseResult { pose = names[index] }; report.cases.Add(current);
                foreach (var c in cloths) current.cloth.Add(new ClothStats { part = c == cloths[0] ? "Dress" : "Hair" });
                previousAttachment.Clear(); stopCaptured = false;
                if (DynamicCase) { dynamicDriver.BeginCase(current.pose, anatomyUp, anatomyForward); current.dynamicInput = dynamicDriver.Current; }
                // Let every case start from a settled neutral without immediately resetting the solver.
                Write();
            }
            void Pre()
            {
                if (!ready || finished) return;
                try
                {
                    if (lastPoseFrame != Time.frameCount)
                    {
                        lastPoseFrame = Time.frameCount;
                        if (pendingNext) { pendingNext = false; Next(); if (finished) return; }
                        // Advance from this frame's delta before driving the body. Advancing
                        // after capture would apply a long render-stall delta one frame later,
                        // when the native solver sees a short delta and an artificial jump.
                        if (index >= 0) time += Mathf.Min(Time.deltaTime, .1f);
                    }
                    float hold = CaseHold;
                    weight = index < 0 ? 0 : time < Enter ? Mathf.Clamp01(time / Enter) : time < Enter + hold ? 1 : time < Enter + hold + Recover ? 1 - Mathf.Clamp01((time - Enter - hold) / Recover) : 0;
                    string pose = index < 0 ? names[0] : current.pose;
                    driver.Apply(DynamicCase ? names[0] : pose, DynamicCase ? 0 : weight); referenceDriver.Apply(DynamicCase ? names[0] : pose, DynamicCase ? 0 : weight);
                    if (DynamicCase) dynamicDriver.Apply(time, Enter, hold, Recover, weight);
                    foreach (var c in corrections) Require(c.ApplyNow(out string error), "Forearm correction failed: " + error);
                    fixedPositions.Clear(); foreach (var c in cloths) foreach (var root in c.SerializeData.rootBones) if (root != null) fixedPositions[root] = root.position;
                    if (CurrentDressBatch(report.batch)) CaptureNativeInput();
                }
                catch (Exception e) { Complete(e.ToString()); }
            }
            void CaptureNativeInput()
            {
                var c = cloths[0]; ref var team = ref MagicaManager.Team.GetTeamDataRef(c.Process.TeamId);
                int count = team.particleChunk.dataLength, start = team.particleChunk.startIndex;
                Require(count == 32 && count == c.Process.ProxyMeshContainer.shareVirtualMesh.VertexCount, "Native Dress input topology changed.");
                if (normalsBeforeFrame != Time.frameCount)
                {
                    if (!normalsBefore.TryGetValue(c, out Vector3[] normals)) { normals = new Vector3[count]; normalsBefore[c] = normals; }
                    Require(normals.Length == count, "Native normal snapshot topology changed.");
                    for (int i = 0; i < count; ++i) { var n = MagicaManager.Simulation.collisionNormalArray[start + i]; normals[i] = new Vector3(n.x, n.y, n.z); Require(Finite(normals[i]), "Non-finite Pre native normal."); }
                    normalsBeforeFrame = Time.frameCount;
                }
                if (index < 0) return; // Native build/reset warmup is not an effect stimulus.
                ref var center = ref MagicaManager.Team.centerDataArray.GetRef(c.Process.TeamId);
                ref var parameters = ref MagicaManager.Team.GetParametersRef(c.Process.TeamId);
                var nativeCenter = c.Process.ProxyMeshContainer.GetCenterTransform();
                Require(nativeCenter != null && (nativeCenter == clone.transform || nativeCenter.IsChildOf(clone.transform)) && !EditorUtility.IsPersistent(nativeCenter) && team.syncTeamId == 0, "Native Dress center is missing, external or synchronized.");
                var inertia = parameters.inertiaConstraint; var old = center.oldComponentWorldPosition; var rotation = center.oldComponentWorldRotation.value;
                Vector3 oldPosition = new(old.x, old.y, old.z); Quaternion oldRotation = new(rotation.x, rotation.y, rotation.z, rotation.w);
                Vector3 initScale = new(team.initScale.x, team.initScale.y, team.initScale.z), scale = nativeCenter.lossyScale;
                Require(Finite(oldPosition) && Finite(oldRotation) && Finite(scale) && Finite(initScale) && scale.x > 0 && scale.y > 0 && scale.z > 0 && initScale.magnitude > .000001f && c.SerializeData.inertiaConstraint.anchor == null, "Unsupported native component/anchor frame for teleport proof.");
                float step = Vector3.Distance(nativeCenter.position, oldPosition), degrees = Quaternion.Angle(nativeCenter.rotation, oldRotation);
                var stats = current.cloth[0]; stats.maximumNativeComponentStepMetres = Mathf.Max(stats.maximumNativeComponentStepMetres, step); stats.maximumNativeComponentStepDegrees = Mathf.Max(stats.maximumNativeComponentStepDegrees, degrees);
                stats.nativeCenterPath = AnimationUtility.CalculateTransformPath(nativeCenter, clone.transform);
                stats.teleportMode = inertia.teleportMode.ToString(); stats.teleportDistance = inertia.teleportDistance; stats.teleportRotation = inertia.teleportRotation;
                Require(Finite(step) && Finite(degrees) && Finite(inertia.teleportDistance) && Finite(inertia.teleportRotation), "Non-finite native teleport comparison.");
                if (inertia.teleportMode != InertiaConstraint.TeleportMode.None)
                    Require(step < inertia.teleportDistance * scale.magnitude / initScale.magnitude && degrees < inertia.teleportRotation, "Owned stimulus would trigger the saved native auto-teleport threshold; parameters were not changed.");
            }
            void Post()
            {
                if (!ready || finished || Time.frameCount == lastFrame) return; lastFrame = Time.frameCount;
                try
                {
                    if (index < 0)
                    {
                        warmup += Mathf.Min(Time.deltaTime, .1f);
                        if (warmup >= 2f) { geometry = new CharacterStressGeometry(clone); report.neutralSolver = SnapshotCloths("neutral"); pendingNext = true; report.logs.Add("neutral warmup completed before geometry baseline"); }
                        return;
                    }
                    float hold = CaseHold;
                    foreach (var pair in fixedPositions) Require(Vector3.Distance(pair.Key.position, pair.Value) < .002f, "A fixed cloth root moved over 2 mm.");
                    for (int ci = 0; ci < cloths.Length; ci++)
                    {
                        var c = cloths[ci]; Require(c.IsValid() && c.Process.IsRunning() && c.Process.IsEnable && c.Process.HasProxyMesh, "A cloth stopped simulating.");
                        var stats = current.cloth[ci]; ref var team = ref MagicaManager.Team.GetTeamDataRef(c.Process.TeamId); int n = team.particleChunk.dataLength, start = team.particleChunk.startIndex;
                        Require(n == c.Process.ProxyMeshContainer.shareVirtualMesh.VertexCount && n > 0, "Particle topology changed."); stats.particles = n; stats.simulatedFrames++;
                        bool hadPrevious = previous.TryGetValue(c, out Vector3[] saved); if (!hadPrevious) { saved = new Vector3[n]; previous[c] = saved; } Require(saved.Length == n, "Particle count changed.");
                        bool attachmentPrevious = previousAttachment.TryGetValue(c, out Vector3[] attachmentSaved);
                        if (CurrentDressBatch(report.batch) && !attachmentPrevious) { attachmentSaved = new Vector3[n]; previousAttachment[c] = attachmentSaved; }
                        bool freshNormal = false;
                        if (CurrentDressBatch(report.batch)) { if (team.updateCount > 0) stats.nativeFrames++; stats.nativeSubsteps += Mathf.Max(0, team.updateCount); if (DynamicCase) dynamicDriver.ObserveNativeFrame(team.updateCount); if (time >= Enter + hold + Recover + Settle - .5f) stats.attachmentTailFrames++; }
                        for (int i = 0; i < n; i++)
                        {
                            var raw = MagicaManager.Simulation.dispPosArray[start + i]; var basis = MagicaManager.Simulation.basePosArray[start + i]; Vector3 position = new(raw.x, raw.y, raw.z), basePosition = new(basis.x, basis.y, basis.z); Vector3 local = clone.transform.InverseTransformPoint(position);
                            Require(Finite(position) && Finite(basePosition) && local.magnitude < 5, "Non-finite or escaped particle."); stats.maximumDeflection = Mathf.Max(stats.maximumDeflection, Vector3.Distance(position, basePosition));
                            if (hadPrevious && Time.deltaTime > .000001f) { float speed = Vector3.Distance(local, saved[i]) / Time.deltaTime; stats.maximumSpeed = Mathf.Max(stats.maximumSpeed, speed); if (time >= Enter + hold + Recover + Settle - .5f) stats.recoveryTailSpeed = Mathf.Max(stats.recoveryTailSpeed, speed); } saved[i] = local;
                            if (CurrentDressBatch(report.batch))
                            {
                                var normal = MagicaManager.Simulation.collisionNormalArray[start + i]; var contact = new Vector3(normal.x, normal.y, normal.z);
                                Require(Finite(contact), "Non-finite native collider contact normal.");
                                Vector3 attachment = Quaternion.Inverse(dressAttachment.rotation) * (position - dressAttachment.position);
                                Require(Finite(attachment), "Non-finite Dress attachment-frame response.");
                                if (c.Process.ProxyMeshContainer.shareVirtualMesh.attributes[i].IsMove())
                                {
                                    stats.movingParticleSamples++;
                                    if (contact.sqrMagnitude > .0001f)
                                    {
                                        stats.retainedNormalSamples++;
                                        Require(normalsBefore.TryGetValue(c, out Vector3[] before) && before.Length == n, "Missing paired native Pre normal snapshot.");
                                        if (team.updateCount > 0 && (contact - before[i]).sqrMagnitude > .0000000001f) { stats.freshNormalChanges++; freshNormal = true; }
                                    }
                                    if (attachmentPrevious && Time.deltaTime > .000001f)
                                    {
                                        float responseSpeed = Vector3.Distance(attachment, attachmentSaved[i]) / Time.deltaTime;
                                        stats.attachmentMaximumSpeed = Mathf.Max(stats.attachmentMaximumSpeed, responseSpeed);
                                        if (time >= Enter + hold + Recover + Settle - .5f) stats.attachmentRecoveryTailSpeed = Mathf.Max(stats.attachmentRecoveryTailSpeed, responseSpeed);
                                    }
                                }
                                attachmentSaved[i] = attachment;
                            }
                        }
                        if (freshNormal) stats.freshNormalFrames++;
                        foreach (var root in c.SerializeData.rootBones) if (root != null && fixedPositions.TryGetValue(root, out Vector3 fixedBefore)) stats.fixedRootError = Mathf.Max(stats.fixedRootError, Vector3.Distance(root.position, fixedBefore));
                    }
                    if (time < Enter) current.entryFrames++; else if (time < Enter + hold) current.holdFrames++; else if (time < Enter + hold + Recover) current.recoveryFrames++; else current.settleFrames++;
                    if (!entryCaptured && time >= .5f) { entryCaptured = true; CapturePhase("enter", false); }
                    if (DynamicCase && current.pose == "root_abrupt_stop" && !stopCaptured && current.dynamicInput.abruptStopObserved) { stopCaptured = true; CapturePhase("stop", true); }
                    if (!holdCaptured && time >= Enter + hold - .1f)
                    {
                        holdCaptured = true; if (!DynamicCase) current.heldPose = driver.Measure(current.pose);
                        if (!DynamicCase && !current.heldPose.targetReached) report.logs.Add("Pose endpoint specification not reached: " + current.pose + "; inspect heldPose before counting this case as completed.");
                        CapturePhase("hold", true);
                    }
                    if (!recoveryCaptured && time >= Enter + hold + .5f) { recoveryCaptured = true; CapturePhase("recover", false); }
                    if (time >= Enter + hold + Recover + Settle && current.settleFrames >= 10)
                    {
                        current.bodyRecoveryError = driver.RecoveryError(); Require(current.bodyRecoveryError < .0001f, "Body pose did not recover to neutral."); CapturePhase("settled", false);
                        Require(current.entryFrames >= 10 && current.holdFrames >= 10 && current.recoveryFrames >= 10, "Insufficient real transition frames.");
                        if (DynamicCase) dynamicDriver.Verify();
                        if (CurrentDressBatch(report.batch))
                        {
                            Require(current.cloth.All(s => Finite(s.attachmentMaximumSpeed) && Finite(s.attachmentRecoveryTailSpeed) && s.attachmentTailFrames >= 5 && s.nativeFrames >= 30 && s.nativeSubsteps >= 30), "Missing real native/tail frames or non-finite Dress settling response.");
                            current.attachmentSettled = current.cloth.All(s => s.attachmentRecoveryTailSpeed <= current.settlingThresholdMetresPerSecond);
                            if (!current.attachmentSettled) report.logs.Add(current.pose + ": attachment motion remained above the existing QA tail threshold; settling is unresolved, not an art/penetration acceptance.");
                        }
                        current.numericalChecksCompleted = (DynamicCase ? current.dynamicInput.inputChecksCompleted : current.heldPose != null && current.heldPose.targetReached) && current.geometry.All(s => s.finite) && (!CurrentDressBatch(report.batch) || current.attachmentSettled); pendingNext = true; Write();
                    }
                }
                catch (Exception e) { Complete(e.ToString()); }
            }
            List<ClothSnapshot> SnapshotCloths(string phase)
            {
                var snapshots = new List<ClothSnapshot>();
                foreach (var c in cloths)
                {
                    ref var team = ref MagicaManager.Team.GetTeamDataRef(c.Process.TeamId);
                    int count = team.particleChunk.dataLength, start = team.particleChunk.startIndex;
                    var mesh = c.Process.ProxyMeshContainer.shareVirtualMesh;
                    Require(count == mesh.VertexCount && count > 0, "Snapshot proxy topology changed.");
                    var s = new ClothSnapshot { part = c == cloths[0] ? "Dress" : "Hair", phase = phase, frame = Time.frameCount, registeredColliders = team.UseColliderCount, colliderCapacity = team.colliderChunk.dataLength,
                        particles = new Vector3[count], animationBase = new Vector3[count], triangles = new int[mesh.TriangleCount * 3] };
                    if (CurrentDressBatch(report.batch)) { s.attachmentWorldPosition = dressAttachment.position; s.attachmentWorldRotation = dressAttachment.rotation; s.attachmentParticles = new Vector3[count]; s.contactNormals = new Vector3[count]; s.contactNormalsBefore = normalsBefore.TryGetValue(c, out Vector3[] before) ? before.ToArray() : null; s.moving = new bool[count]; s.nativeSubsteps = team.updateCount; }
                    for (int i = 0; i < count; i++)
                    {
                        var p = MagicaManager.Simulation.dispPosArray[start + i]; var b = MagicaManager.Simulation.basePosArray[start + i];
                        s.particles[i] = clone.transform.InverseTransformPoint(new Vector3(p.x, p.y, p.z));
                        s.animationBase[i] = clone.transform.InverseTransformPoint(new Vector3(b.x, b.y, b.z));
                        Require(Finite(s.particles[i]) && Finite(s.animationBase[i]), "Non-finite solver snapshot: " + s.part + "/" + phase);
                        if (CurrentDressBatch(report.batch))
                        {
                            s.attachmentParticles[i] = Quaternion.Inverse(dressAttachment.rotation) * (new Vector3(p.x, p.y, p.z) - dressAttachment.position);
                            var normal = MagicaManager.Simulation.collisionNormalArray[start + i]; s.contactNormals[i] = new Vector3(normal.x, normal.y, normal.z); s.moving[i] = mesh.attributes[i].IsMove();
                            Require(Finite(s.attachmentParticles[i]) && Finite(s.contactNormals[i]), "Non-finite attachment/contact snapshot.");
                        }
                    }
                    for (int i = 0; i < mesh.TriangleCount; i++) { var t = mesh.triangles[i]; Require(t.x >= 0 && t.x < count && t.y >= 0 && t.y < count && t.z >= 0 && t.z < count, "Proxy triangle index is outside the snapshot particle range."); s.triangles[i * 3] = t.x; s.triangles[i * 3 + 1] = t.y; s.triangles[i * 3 + 2] = t.z; }
                    var bones = c.SerializeData.rootBones.Where(b => b != null).SelectMany(b => b.GetComponentsInChildren<Transform>(true)).Distinct().ToArray();
                    s.bonePaths = bones.Select(b => AnimationUtility.CalculateTransformPath(b, clone.transform)).ToArray();
                    s.bonePositions = bones.Select(b => clone.transform.InverseTransformPoint(b.position)).ToArray();
                    s.boneRotations = bones.Select(b => b.rotation).ToArray();
                    for (int i = 0; i < bones.Length; i++) Require(Finite(s.bonePositions[i]) && Finite(s.boneRotations[i]), "Non-finite bone snapshot: " + s.bonePaths[i]);
                    snapshots.Add(s);
                }
                return snapshots;
            }
            void CapturePhase(string phase, bool allViews)
            {
                string folder = Path.Combine(report.output, index.ToString("D2") + "-" + current.pose); Directory.CreateDirectory(folder);
                if (CurrentDressBatch(report.batch)) Require(CharacterDressOnlyStressPreparation.ParameterState(cloths[0]) == report.dressParameters, "Native Dress parameters changed during the stress run.");
                current.solver.AddRange(SnapshotCloths(phase));
                current.geometry.Add(geometry.Capture(current.pose, phase));
                Vector3 viewForward = DynamicCase ? dynamicDriver.RotatedView(anatomyForward) : anatomyForward;
                Vector3 viewRight = DynamicCase ? dynamicDriver.RotatedView(anatomyRight) : anatomyRight;
                CaptureImage(folder, phase + "-front", viewForward, null, false);
                CaptureImage(folder, phase + "-side", viewRight, null, false);
                if (allViews)
                {
                    CaptureImage(folder, phase + "-back", -viewForward, null, false);
                    Animator a = clone.GetComponentInChildren<Animator>(true);
                    CaptureImage(folder, phase + "-left-shoulder", viewForward, a.GetBoneTransform(HumanBodyBones.LeftUpperArm).position, false, true);
                    CaptureImage(folder, phase + "-right-shoulder", viewForward, a.GetBoneTransform(HumanBodyBones.RightUpperArm).position, false, true);
                    CaptureImage(folder, phase + "-hips", viewForward, a.GetBoneTransform(HumanBodyBones.Hips).position, false);
                    CaptureImage(folder, phase + "-body-hips", viewForward, a.GetBoneTransform(HumanBodyBones.Hips).position, false, true);
                    CaptureImage(folder, phase + "-body-hips-side", viewRight, a.GetBoneTransform(HumanBodyBones.Hips).position, false, true);
                    CaptureImage(folder, phase + "-physics-off-front", viewForward, null, true);
                    CaptureImage(folder, phase + "-physics-off-side", viewRight, null, true);
                    geometry.ExportObj(Path.Combine(folder, "hold-world.obj"));
                }
            }
            void CaptureImage(string folder, string name, Vector3 direction, Vector3? focus, bool physicsOff, bool bodyOnly = false)
            {
                Bounds bounds = default; bool found = false;
                foreach (var renderer in clone.GetComponentsInChildren<Renderer>(true)) if (renderer.enabled && renderer.gameObject.activeInHierarchy) { if (!found) { bounds = renderer.bounds; found = true; } else bounds.Encapsulate(renderer.bounds); }
                Require(found && Finite(bounds.center) && Finite(bounds.extents), "No finite render bounds.");
                Vector3 center = focus ?? bounds.center;
                float tangent = Mathf.Tan(camera.fieldOfView * .5f * Mathf.Deg2Rad);
                float distance = focus.HasValue ? 1.2f : Mathf.Max(2.5f, bounds.extents.y / tangent * 1.15f, Mathf.Max(bounds.extents.x, bounds.extents.z) / (tangent * camera.aspect) * 1.15f);
                camera.transform.position = center + direction * distance; camera.transform.LookAt(center); camera.cullingMask = 1 << (physicsOff ? 30 : 31); camera.targetTexture = target;
                var previousTarget = RenderTexture.active;
                var hidden = new List<Renderer>();
                try
                {
                    if (bodyOnly)
                    {
                        var renderers = clone.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                        Require(renderers.Count(r => r.name == "Cosha") == 1, "Body-only capture requires the unique current Cosha body renderer.");
                        foreach (var r in clone.GetComponentsInChildren<Renderer>(true)) if (r.enabled && r.name != "Cosha") { r.enabled = false; hidden.Add(r); }
                    }
                    light.enabled = true;
                    if (UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline != null) { var request = new UnityEngine.Rendering.RenderPipeline.StandardRequest { destination = target }; Require(UnityEngine.Rendering.RenderPipeline.SupportsRenderRequest(camera, request), "Pipeline capture is unsupported."); UnityEngine.Rendering.RenderPipeline.SubmitRenderRequest(camera, request); } else camera.Render();
                    RenderTexture.active = target; pixels.ReadPixels(new Rect(0, 0, 600, 900), 0, 0, false); pixels.Apply(false, false); string path = Path.Combine(folder, name + ".png"); File.WriteAllBytes(path, pixels.EncodeToPNG()); current.images.Add(path);
                }
                finally { foreach (var r in hidden) if (r != null) r.enabled = true; light.enabled = false; camera.targetTexture = null; RenderTexture.active = previousTarget; }
            }
            void Write() => File.WriteAllText(Path.Combine(report.output, "verification.json"), JsonUtility.ToJson(report, true));
            public void Complete(string error)
            {
                if (finished) return; finished = true;
                MagicaManager.OnPreSimulation -= Pre; MagicaManager.OnPostSimulation -= Post; EditorApplication.update -= Tick;
                try { dynamicDriver?.Dispose(); } catch (Exception e) { error = (error ?? "") + "\nDynamic graph cleanup: " + e; }
                try { geometry?.Dispose(); driver?.RestoreOriginal(); referenceDriver?.RestoreOriginal(); if (holder != null) Object.DestroyImmediate(holder); }
                catch (Exception e) { error = (error ?? "") + "\nCleanup: " + e; }
                finally { if (pixels != null) Object.DestroyImmediate(pixels); if (target != null) { target.Release(); Object.DestroyImmediate(target); } }
                try
                {
                    if (scene.IsValid() && scene.isLoaded)
                    {
                        var unload = SceneManager.UnloadSceneAsync(scene); if (unload != null) { string finalError = error; unload.completed += _ => done(finalError); return; }
                    }
                }
                catch (Exception e) { error = (error ?? "") + "\nScene cleanup: " + e; }
                done(error);
            }
        }
    }
}
