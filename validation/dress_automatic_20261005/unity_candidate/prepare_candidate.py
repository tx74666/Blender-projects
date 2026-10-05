"""Generate a review-only Unity diff. Writes only this X Validation directory."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import subprocess

candidate = Path(__file__).resolve().parent
ast.parse(Path(__file__).read_text(encoding="utf-8"))
project = Path("D:/Unity Projects/RandomRealm2")
relative = "Assets/Scripts/Editor/CharacterPoseStressVerification.cs"
source = project / relative
original = source.read_text(encoding="utf-8-sig")
text = original

def replace(old, new):
    global text
    if text.count(old) != 1:
        raise RuntimeError("Candidate base changed; review before rebuilding: " + old[:100])
    text = text.replace(old, new)

replace(
    '        [MenuItem(MenuRoot + "Cancel")] static void Cancel()',
    '        [MenuItem(MenuRoot + "Verify Current Dress Only (Transient Play)")] static void CurrentDress() => Start("dressCurrent");\n'
    '        [MenuItem(MenuRoot + "Cancel")] static void Cancel()')
replace(
    '        static bool CollisionBatch(string batch) => batch == "dressCollisionBaseline" || batch == "dressCollisionReference";',
    '        static bool CollisionBatch(string batch) => batch == "dressCollisionBaseline" || batch == "dressCollisionReference";\n'
    '        static bool CurrentDressBatch(string batch) => batch == "dressCurrent";')
replace(
    '            public string visualAcceptance = "Pending actual image review; numerical completion is not an art/penetration pass.";',
    '            public string dressParameters; // Populated only by the isolated current-Dress route.\n'
    '            public string visualAcceptance = "Pending actual image review; numerical completion is not an art/penetration pass.";')
replace(
    '''                    RecordPhysics(clone, "production prefab before profile restore");
                    var saved = CharacterPhysicsPersistence.Load(source); Require(saved != null, "Saved physics profile is missing.");
                    CharacterPhysicsPersistence.Restore(clone, saved);
                    RecordPhysics(clone, "owned fixture after saved profile restore");
                    Strip(clone);''',
    '''                    var saved = CharacterPhysicsPersistence.Load(source); Require(saved != null, "Saved physics profile is missing.");
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
                    Strip(clone, preserveHairMetadata: CurrentDressBatch(report.batch));''')
replace(
    '                report.logs.Add("fixture=current Player + saved Physics profile, stripped gameplay only; source/Avatar/mesh/material assets retained");',
    '                report.logs.Add(CurrentDressBatch(report.batch) ? "fixture=current Player + bounded saved Dress only; QA component/colliders, Hair stationary, no whole-profile restore or Hair setup/apply" : "fixture=current Player + saved Physics profile, stripped gameplay only; source/Avatar/mesh/material assets retained");')
replace(
    '''        static void Strip(GameObject clone)
        {
            foreach (var b in clone.GetComponentsInChildren<Behaviour>(true)) if (!(b is Animator || b is MagicaCloth || b is ColliderComponent || b is ForearmCorrection || b is CharacterPhysicsRig)) b.enabled = false;
            var removals = clone.GetComponentsInChildren<MonoBehaviour>(true).Where(b => !(b is MagicaCloth || b is ColliderComponent || b is ForearmCorrection || b is CharacterPhysicsRig)).ToList();''',
    '''        static void Strip(GameObject clone, bool preserveHairMetadata = false)
        {
            bool Kept(Behaviour b) => b is Animator || b is MagicaCloth || b is ColliderComponent || b is ForearmCorrection || b is CharacterPhysicsRig || preserveHairMetadata && b is CharacterHairMotionRig;
            foreach (var b in clone.GetComponentsInChildren<Behaviour>(true)) if (!Kept(b)) b.enabled = false;
            var removals = clone.GetComponentsInChildren<MonoBehaviour>(true).Where(b => !Kept(b)).ToList();''')
replace(
    '''                var rig = clone.GetComponent<CharacterPhysicsRig>(); Require(rig != null && rig.Dress != null && rig.Hair != null, "Both configured cloths are required."); cloths = new[] { rig.Dress, rig.Hair };''',
    '''                var rig = clone.GetComponent<CharacterPhysicsRig>();
                Require(rig != null && rig.Dress != null && (CurrentDressBatch(report.batch) || rig.Hair != null), "Required configured cloths are missing.");
                cloths = CurrentDressBatch(report.batch) ? new[] { rig.Dress } : new[] { rig.Dress, rig.Hair };''')
replace(
    '                string poseBatch = CollisionBatch(report.batch) ? "legs" : report.batch;',
    '                string poseBatch = CollisionBatch(report.batch) || CurrentDressBatch(report.batch) ? "legs" : report.batch;')
replace(
    '                            if (c == cloths[0] && report.batch == "dressCollisionReference") Require(count == 0 && capacity == 0, "Dress collision reference registered native colliders.");',
    '                            if (c == cloths[0] && report.batch == "dressCollisionReference") Require(count == 0 && capacity == 0, "Dress collision reference registered native colliders.");\n'
    '                            if (CurrentDressBatch(report.batch)) Require(count == 3 && c.Process.ProxyMeshContainer.shareVirtualMesh.VertexCount == 32 && c.SerializeData.rootBones.Count == 8 && CharacterDressOnlyStressPreparation.ParameterState(c) == report.dressParameters, "Dress-only native topology/collider registration or parameters changed.");')
replace(
    '                current.solver.AddRange(SnapshotCloths(phase));',
    '                if (CurrentDressBatch(report.batch)) Require(CharacterDressOnlyStressPreparation.ParameterState(cloths[0]) == report.dressParameters, "Native Dress parameters changed during the stress run.");\n'
    '                current.solver.AddRange(SnapshotCloths(phase));')

# Additional stimuli are confined to the current-Dress route; existing menus and
# their nine endpoint poses retain their original pose driver and completion rules.
replace('            public string dressParameters; // Populated only by the isolated current-Dress route.',
        '            public string dressParameters; // Populated only by the isolated current-Dress route.\n'
        '            public string walkBinding;\n'
        '            public bool nativeContactObserved;\n'
        '            public string contactLimits = "Edge-mode normals can persist after contact ends. A nonzero Pre/Post direction change in a real solver frame is a sufficient fresh collider-normal witness; unchanged/zero normals cannot establish contact frequency or absence. Normals describe friction/proximity at the final solver substep, not rendered-surface penetration or necessarily the displayed interpolated particle pose.";')
replace('            public string pose; public int entryFrames, holdFrames, recoveryFrames, settleFrames;',
        '            public string pose; public int entryFrames, holdFrames, recoveryFrames, settleFrames;\n'
        '            public CharacterDressDynamicStressDriver.Proof dynamicInput;\n'
        '            public bool attachmentSettled; public float settlingThresholdMetresPerSecond = .35f;')
replace('            public float maximumDeflection, maximumSpeed, recoveryTailSpeed, fixedRootError;',
        '            public float maximumDeflection, maximumSpeed, recoveryTailSpeed, fixedRootError;\n'
        '            public int movingParticleSamples, retainedNormalSamples, freshNormalChanges, freshNormalFrames, nativeFrames, nativeSubsteps, attachmentTailFrames;\n'
        '            public float attachmentMaximumSpeed, attachmentRecoveryTailSpeed;\n'
        '            public float maximumNativeComponentStepMetres, maximumNativeComponentStepDegrees, teleportDistance, teleportRotation; public string teleportMode, nativeCenterPath;\n'
        '            public string attachmentLimits = "Current-Dress response uses Waist translation/rotation removed in world metres; scale is not divided. Contact normals can persist in Edge mode; fresh Pre/Post changes are sufficient friction/proximity witnesses, not contact frequency or rendered-triangle penetration acceptance. Settling uses the existing QA 0.35 m/s tail threshold, not an art or game acceptance threshold.";')
replace('            public Vector3[] particles, animationBase; public int[] triangles;',
        '            public Vector3[] particles, animationBase; public int[] triangles;\n'
        '            public Vector3 attachmentWorldPosition; public Quaternion attachmentWorldRotation;\n'
        '            public Vector3[] attachmentParticles, contactNormals, contactNormalsBefore; public bool[] moving;\n'
        '            public int nativeSubsteps;')
replace('report.batch == "arms" || CollisionBatch(report.batch) ? 3 : 9)',
        'report.batch == "arms" || CollisionBatch(report.batch) ? 3 : CurrentDressBatch(report.batch) ? 12 : 9)')
replace('            CharacterStressPoseDriver driver, referenceDriver; CharacterStressGeometry geometry;',
        '            CharacterStressPoseDriver driver, referenceDriver; CharacterStressGeometry geometry;\n'
        '            CharacterDressDynamicStressDriver dynamicDriver; Transform dressAttachment;\n'
        '            readonly Dictionary<MagicaCloth, Vector3[]> previousAttachment = new();\n'
        '            readonly Dictionary<MagicaCloth, Vector3[]> normalsBefore = new(); int normalsBeforeFrame = -1; bool stopCaptured;\n'
        '            float CaseHold => dynamicDriver != null && current != null && CharacterDressDynamicStressDriver.IsDynamic(current.pose) ? dynamicDriver.HoldSeconds(current.pose) : Hold;\n'
        '            bool DynamicCase => dynamicDriver != null && current != null && CharacterDressDynamicStressDriver.IsDynamic(current.pose);')
replace('                foreach (var a in new[] { clone.GetComponentInChildren<Animator>(true), reference.GetComponentInChildren<Animator>(true) }) { Require(a != null, "Animator missing.");',
        '                var nativeWalk = CurrentDressBatch(report.batch) ? CharacterDressDynamicStressDriver.ResolveWalk(clone.GetComponentInChildren<Animator>(true)) : null;\n'
        '                if (nativeWalk != null) Require(nativeWalk.proof == report.walkBinding, "Walk_N/controller/Avatar binding changed after fixture preparation.");\n'
        '                foreach (var a in new[] { clone.GetComponentInChildren<Animator>(true), reference.GetComponentInChildren<Animator>(true) }) { Require(a != null, "Animator missing.");')
replace('                if (CollisionBatch(report.batch)) names = new[] { "leg_forward_R90", "squat", "lunge_R" };',
        '''                if (CollisionBatch(report.batch)) names = new[] { "leg_forward_R90", "squat", "lunge_R" };
                if (CurrentDressBatch(report.batch))
                {
                    dynamicDriver = new CharacterDressDynamicStressDriver(clone, reference, nativeWalk);
                    names = names.Concat(CharacterDressDynamicStressDriver.Names).ToArray();
                    dressAttachment = cloths[0].SerializeData.rootBones[0].parent;
                    Require(dressAttachment != null && dressAttachment.name == "SK_Dress_Waist" && cloths[0].SerializeData.rootBones.All(b => b != null && b.parent == dressAttachment), "Missing exact shared Dress attachment frame.");
                }''')
replace('                foreach (var c in cloths) current.cloth.Add(new ClothStats { part = c == cloths[0] ? "Dress" : "Hair" });',
        '''                foreach (var c in cloths) current.cloth.Add(new ClothStats { part = c == cloths[0] ? "Dress" : "Hair" });
                previousAttachment.Clear(); stopCaptured = false;
                if (DynamicCase) { dynamicDriver.BeginCase(current.pose, anatomyUp, anatomyForward); current.dynamicInput = dynamicDriver.Current; }''')
replace('                    weight = index < 0 ? 0 : time < Enter ? Mathf.Clamp01(time / Enter) : time < Enter + Hold ? 1 : time < Enter + Hold + Recover ? 1 - Mathf.Clamp01((time - Enter - Hold) / Recover) : 0;',
        '                    float hold = CaseHold;\n'
        '                    weight = index < 0 ? 0 : time < Enter ? Mathf.Clamp01(time / Enter) : time < Enter + hold ? 1 : time < Enter + hold + Recover ? 1 - Mathf.Clamp01((time - Enter - hold) / Recover) : 0;')
replace('                    driver.Apply(pose, weight); referenceDriver.Apply(pose, weight);',
        '                    driver.Apply(DynamicCase ? names[0] : pose, DynamicCase ? 0 : weight); referenceDriver.Apply(DynamicCase ? names[0] : pose, DynamicCase ? 0 : weight);\n'
        '                    if (DynamicCase) dynamicDriver.Apply(time, Enter, hold, Recover, weight);')
replace('                    fixedPositions.Clear(); foreach (var c in cloths) foreach (var root in c.SerializeData.rootBones) if (root != null) fixedPositions[root] = root.position;',
        '                    fixedPositions.Clear(); foreach (var c in cloths) foreach (var root in c.SerializeData.rootBones) if (root != null) fixedPositions[root] = root.position;\n'
        '                    if (CurrentDressBatch(report.batch)) CaptureNativeInput();')
replace('            void Post()\n            {',
        '''            void CaptureNativeInput()
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
            {''')
replace('                    foreach (var pair in fixedPositions) Require(Vector3.Distance(pair.Key.position, pair.Value) < .002f, "A fixed cloth root moved over 2 mm.");',
        '                    float hold = CaseHold;\n'
        '                    foreach (var pair in fixedPositions) Require(Vector3.Distance(pair.Key.position, pair.Value) < .002f, "A fixed cloth root moved over 2 mm.");')
replace('                        bool hadPrevious = previous.TryGetValue(c, out Vector3[] saved); if (!hadPrevious) { saved = new Vector3[n]; previous[c] = saved; } Require(saved.Length == n, "Particle count changed.");',
        '''                        bool hadPrevious = previous.TryGetValue(c, out Vector3[] saved); if (!hadPrevious) { saved = new Vector3[n]; previous[c] = saved; } Require(saved.Length == n, "Particle count changed.");
                        bool attachmentPrevious = previousAttachment.TryGetValue(c, out Vector3[] attachmentSaved);
                        if (CurrentDressBatch(report.batch) && !attachmentPrevious) { attachmentSaved = new Vector3[n]; previousAttachment[c] = attachmentSaved; }
                        bool freshNormal = false;
                        if (CurrentDressBatch(report.batch)) { if (team.updateCount > 0) stats.nativeFrames++; stats.nativeSubsteps += Mathf.Max(0, team.updateCount); if (DynamicCase) dynamicDriver.ObserveNativeFrame(team.updateCount); if (time >= Enter + hold + Recover + Settle - .5f) stats.attachmentTailFrames++; }''')
replace('if (time >= Enter + Hold + Recover + Settle - .5f) stats.recoveryTailSpeed',
        'if (time >= Enter + hold + Recover + Settle - .5f) stats.recoveryTailSpeed')
replace('                        foreach (var root in c.SerializeData.rootBones) if (root != null && fixedPositions.TryGetValue(root, out Vector3 fixedBefore)) stats.fixedRootError',
        '''                        if (freshNormal) stats.freshNormalFrames++;
                        foreach (var root in c.SerializeData.rootBones) if (root != null && fixedPositions.TryGetValue(root, out Vector3 fixedBefore)) stats.fixedRootError''')
replace(' } saved[i] = local;\n                        }',
        ''' } saved[i] = local;
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
                        }''')
replace('                    if (time < Enter) current.entryFrames++; else if (time < Enter + Hold) current.holdFrames++; else if (time < Enter + Hold + Recover) current.recoveryFrames++; else current.settleFrames++;',
        '                    if (time < Enter) current.entryFrames++; else if (time < Enter + hold) current.holdFrames++; else if (time < Enter + hold + Recover) current.recoveryFrames++; else current.settleFrames++;')
replace('                    if (!holdCaptured && time >= Enter + Hold - .1f)', '                    if (!holdCaptured && time >= Enter + hold - .1f)')
replace('                        holdCaptured = true; current.heldPose = driver.Measure(current.pose);\n                        if (!current.heldPose.targetReached)',
        '                        holdCaptured = true; if (!DynamicCase) current.heldPose = driver.Measure(current.pose);\n'
        '                        if (!DynamicCase && !current.heldPose.targetReached)')
replace('                    if (!recoveryCaptured && time >= Enter + Hold + .5f)', '                    if (!recoveryCaptured && time >= Enter + hold + .5f)')
replace('                    if (!entryCaptured && time >= .5f) { entryCaptured = true; CapturePhase("enter", false); }',
        '                    if (!entryCaptured && time >= .5f) { entryCaptured = true; CapturePhase("enter", false); }\n'
        '                    if (DynamicCase && current.pose == "root_abrupt_stop" && !stopCaptured && current.dynamicInput.abruptStopObserved) { stopCaptured = true; CapturePhase("stop", true); }')
replace('                    if (time >= Enter + Hold + Recover + Settle && current.settleFrames >= 10)', '                    if (time >= Enter + hold + Recover + Settle && current.settleFrames >= 10)')
replace('                        current.numericalChecksCompleted = current.heldPose != null && current.heldPose.targetReached && current.geometry.All(s => s.finite); pendingNext = true; Write();',
        '''                        if (DynamicCase) dynamicDriver.Verify();
                        if (CurrentDressBatch(report.batch))
                        {
                            Require(current.cloth.All(s => Finite(s.attachmentMaximumSpeed) && Finite(s.attachmentRecoveryTailSpeed) && s.attachmentTailFrames >= 5 && s.nativeFrames >= 30 && s.nativeSubsteps >= 30), "Missing real native/tail frames or non-finite Dress settling response.");
                            current.attachmentSettled = current.cloth.All(s => s.attachmentRecoveryTailSpeed <= current.settlingThresholdMetresPerSecond);
                            if (!current.attachmentSettled) report.logs.Add(current.pose + ": attachment motion remained above the existing QA tail threshold; settling is unresolved, not an art/penetration acceptance.");
                        }
                        current.numericalChecksCompleted = (DynamicCase ? current.dynamicInput.inputChecksCompleted : current.heldPose != null && current.heldPose.targetReached) && current.geometry.All(s => s.finite) && (!CurrentDressBatch(report.batch) || current.attachmentSettled); pendingNext = true; Write();''')
replace('                    for (int i = 0; i < count; i++)\n                    {\n                        var p = MagicaManager.Simulation.dispPosArray[start + i];',
        '''                    if (CurrentDressBatch(report.batch)) { s.attachmentWorldPosition = dressAttachment.position; s.attachmentWorldRotation = dressAttachment.rotation; s.attachmentParticles = new Vector3[count]; s.contactNormals = new Vector3[count]; s.contactNormalsBefore = normalsBefore.TryGetValue(c, out Vector3[] before) ? before.ToArray() : null; s.moving = new bool[count]; s.nativeSubsteps = team.updateCount; }
                    for (int i = 0; i < count; i++)
                    {
                        var p = MagicaManager.Simulation.dispPosArray[start + i];''')
replace('                        Require(Finite(s.particles[i]) && Finite(s.animationBase[i]), "Non-finite solver snapshot: " + s.part + "/" + phase);',
        '''                        Require(Finite(s.particles[i]) && Finite(s.animationBase[i]), "Non-finite solver snapshot: " + s.part + "/" + phase);
                        if (CurrentDressBatch(report.batch))
                        {
                            s.attachmentParticles[i] = Quaternion.Inverse(dressAttachment.rotation) * (new Vector3(p.x, p.y, p.z) - dressAttachment.position);
                            var normal = MagicaManager.Simulation.collisionNormalArray[start + i]; s.contactNormals[i] = new Vector3(normal.x, normal.y, normal.z); s.moving[i] = mesh.attributes[i].IsMove();
                            Require(Finite(s.attachmentParticles[i]) && Finite(s.contactNormals[i]), "Non-finite attachment/contact snapshot.");
                        }''')
replace('                CaptureImage(folder, phase + "-front", anatomyForward, null, false);\n                CaptureImage(folder, phase + "-side", anatomyRight, null, false);',
        '                Vector3 viewForward = DynamicCase ? dynamicDriver.RotatedView(anatomyForward) : anatomyForward;\n'
        '                Vector3 viewRight = DynamicCase ? dynamicDriver.RotatedView(anatomyRight) : anatomyRight;\n'
        '                CaptureImage(folder, phase + "-front", viewForward, null, false);\n'
        '                CaptureImage(folder, phase + "-side", viewRight, null, false);')
# Only this capture method's remaining view axes; no effect on old pose tests.
capture_start = text.index('            void CapturePhase(string phase, bool allViews)')
capture_end = text.index('            void CaptureImage(', capture_start)
capture = text[capture_start:capture_end]
capture = capture.replace(', anatomyForward,', ', viewForward,').replace(', -anatomyForward,', ', -viewForward,').replace(', anatomyRight,', ', viewRight,')
text = text[:capture_start] + capture + text[capture_end:]
replace('                try { geometry?.Dispose(); driver?.RestoreOriginal(); referenceDriver?.RestoreOriginal(); if (holder != null) Object.DestroyImmediate(holder); }',
        '                try { dynamicDriver?.Dispose(); } catch (Exception e) { error = (error ?? "") + "\\nDynamic graph cleanup: " + e; }\n'
        '                try { geometry?.Dispose(); driver?.RestoreOriginal(); referenceDriver?.RestoreOriginal(); if (holder != null) Object.DestroyImmediate(holder); }')
replace('        static bool Finite(Vector3 v)', '        static bool Finite(float v) => !float.IsNaN(v) && !float.IsInfinity(v);\n        static bool Finite(Vector3 v)')
replace('                    report.numericalChecksCompleted = (report.enteredPlay || report.endpointOnly)',
        '                    if (CurrentDressBatch(report.batch)) report.nativeContactObserved = report.cases.SelectMany(c => c.cloth).Any(s => s.freshNormalChanges > 0);\n'
        '                    report.numericalChecksCompleted = (!CurrentDressBatch(report.batch) || report.nativeContactObserved) && (report.enteredPlay || report.endpointOnly)')

output = candidate / "CharacterPoseStressVerification.cs"
output.write_text(text, encoding="utf-8", newline="\n")
helper = candidate / "CharacterDressOnlyStressPreparation.cs"
helper_text = helper.read_text(encoding="utf-8")
dynamic = candidate / "CharacterDressDynamicStressDriver.cs"
dynamic_text = dynamic.read_text(encoding="utf-8")
diff = "".join(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
                                  fromfile="a/" + relative, tofile="b/" + relative))
diff += "".join(difflib.unified_diff([], helper_text.splitlines(True), fromfile="/dev/null",
                                  tofile="b/Assets/Scripts/Editor/CharacterDressOnlyStressPreparation.cs"))
diff += "".join(difflib.unified_diff([], dynamic_text.splitlines(True), fromfile="/dev/null",
                                  tofile="b/Assets/Scripts/Editor/CharacterDressDynamicStressDriver.cs"))
(candidate / "dress_only_candidate.patch").write_text(diff, encoding="utf-8", newline="\n")
patch_check = subprocess.run(["git", "-C", str(project), "apply", "--check", str(candidate / "dress_only_candidate.patch")], capture_output=True, text=True, encoding="utf-8")
manifest = {
    "state": "review-only; no Unity Assets write, compiler, MCP, UI or native execution",
    "base_file": str(source), "base_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "candidate_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    "helper_sha256": hashlib.sha256(helper.read_bytes()).hexdigest(),
    "dynamic_sha256": hashlib.sha256(dynamic.read_bytes()).hexdigest(),
    "patch_sha256": hashlib.sha256((candidate / "dress_only_candidate.patch").read_bytes()).hexdigest(),
    "apply_check": {"command": "git apply --check (read-only)", "exit_code": patch_check.returncode, "diagnostics": (patch_check.stdout + patch_check.stderr).strip()},
    "generator_ast": "passed",
    "other_inputs": {p: hashlib.sha256((project/p).read_bytes()).hexdigest() for p in (
        "Assets/Scripts/Editor/CharacterPhysicsProfile.cs",
        "Assets/Scripts/Editor/CharacterPhysicsPersistence.cs",
        "Assets/Scripts/Editor/CharacterStressPoseDriver.cs",
        "Assets/Scripts/Editor/CharacterRoundtripAnimationPhysicsVerification.cs",
        "Assets/Plugins/MagicaCloth2/Scripts/Core/Cloth/Constraints/ColliderCollisionConstraint.cs",
        "Assets/Plugins/MagicaCloth2/Scripts/Core/Manager/Team/TeamManager.cs",
        "Assets/Art/Character/Cosha/Cosha.fbx",
        "Assets/Prefabs/Characters/Cosha/Cosha.Player.Physics.asset",
        "Assets/Prefabs/Characters/Cosha/Cosha.Player.prefab")},
    "menu": "Tools/RandomRealm/Character/Pose Stress/Verify Current Dress Only (Transient Play)",
    "scope": "Current imported production Cosha model; isolated saved-Dress simulation; nine poses plus native Walk_N two cycles/root turn/root abrupt stop; contact/attachment diagnostics; other cloth simulations disabled; no Hair migration/publication",
    "native_validation": "pending explicit Unity writer handoff and native compile/menu execution",
}
(candidate / "candidate_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
if patch_check.returncode:
    raise RuntimeError("Review-only candidate no longer applies to its current base: " + manifest["apply_check"]["diagnostics"])
print(json.dumps({"candidate": str(output), "patch": str(candidate/"dress_only_candidate.patch"),
                  "base_sha256": manifest["base_sha256"], "native_validation": "unrun"}))
