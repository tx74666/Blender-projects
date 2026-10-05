using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

namespace Unity.RandomRealm.Editor
{
    // QA-only: an existing clip is read, never authored or applied to a production controller.
    internal sealed class CharacterDressDynamicStressDriver : IDisposable
    {
        public static readonly string[] Names = { "walk_native_two_cycles", "root_yaw_turn", "root_abrupt_stop" };
        internal sealed class Binding { public AnimationClip clip; public string proof; }
        [Serializable] internal sealed class InputSample
        {
            public int frame; public float time, clipTime, frameDeltaTime, stimulusDeltaTime;
            public Vector3 rootLocalPosition, commandedVelocity, measuredVelocity, stimulusClockVelocity;
            public Quaternion rootLocalRotation;
            public float commandedYawDegrees;
        }
        [Serializable] internal sealed class CycleProof
        {
            public int sampledFrames, nativeFrames, nativeSubsteps; public float leftLegExcursionDegrees, rightLegExcursionDegrees;
        }
        [Serializable] internal sealed class Proof
        {
            public string kind, binding;
            public int inputFrames, stationaryAfterStopFrames;
            public float clipLength, completedWalkCycles, maximumRootSpeed, maximumApproachRootSpeed, maximumRootYawDegrees, rootReturnError;
            public bool abruptStopObserved, inputChecksCompleted;
            public CycleProof[] firstTwoCycles = { new(), new() };
            public List<InputSample> input = new();
            public string limits = "Native Humanoid clip/root stimuli on owned clones. Response and contacts are diagnostics; no gameplay publication, Hair acceptance, rendered-triangle collision safety or Blender/Magica equivalence is claimed.";
        }
        struct Pose { public Transform bone; public Vector3 position, scale; public Quaternion rotation; }
        readonly GameObject root, reference;
        readonly Animator animator, referenceAnimator;
        readonly Binding binding;
        readonly Pose[] neutral, referenceNeutral;
        readonly Transform leftLeg, rightLeg;
        readonly Vector3 rootPosition, rootScale;
        readonly Quaternion rootRotation;
        readonly Vector3 referencePosition, referenceScale;
        readonly Quaternion referenceRotation;
        readonly Quaternion[] cycleLeft = new Quaternion[2], cycleRight = new Quaternion[2];
        Vector3 anatomyUp, anatomyForward, previousPosition;
        float previousTime, previousCommandSpeed, lastEnter, lastHold;
        int lastInputFrame = -1;
        bool stopCommandObserved;
        string current;
        PlayableGraph graph, referenceGraph;
        AnimationClipPlayable playable, referencePlayable;
        public Proof Current { get; private set; }

        static void Require(bool okay, string message) { if (!okay) throw new InvalidOperationException(message); }
        static bool Finite(float f) => !float.IsNaN(f) && !float.IsInfinity(f);
        static bool Finite(Vector3 v) => Finite(v.x) && Finite(v.y) && Finite(v.z);
        static bool Finite(Quaternion q) => Finite(q.x) && Finite(q.y) && Finite(q.z) && Finite(q.w);
        static string Identity(UnityEngine.Object asset)
        {
            Require(asset != null && EditorUtility.IsPersistent(asset) && !EditorUtility.IsDirty(asset), "Walk binding requires a saved, unmodified asset identity.");
            Require(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(asset, out string guid, out long id) && !string.IsNullOrEmpty(guid), "Walk asset identity is unavailable.");
            return AssetDatabase.GetAssetPath(asset) + ":" + guid + ":" + id;
        }
        public static Binding ResolveWalk(Animator animator)
        {
            Require(animator != null && animator.avatar != null && animator.avatar.isValid && animator.avatar.isHuman, "Dress Walk QA requires the existing valid Humanoid Avatar.");
            var layers = new List<AnimatorOverrideController>(); var seen = new HashSet<RuntimeAnimatorController>();
            RuntimeAnimatorController controller = animator.runtimeAnimatorController;
            Require(controller != null, "Dress Walk QA requires the existing controller; no clip is guessed.");
            string controllerIdentity = Identity(controller);
            while (controller is AnimatorOverrideController layer)
            {
                Require(seen.Add(controller), "Override controller cycle."); Identity(layer); layers.Add(layer); controller = layer.runtimeAnimatorController;
            }
            Require(controller != null && seen.Add(controller), "Missing or cyclic base controller."); Identity(controller);
            var bases = controller.animationClips.Where(c => c != null).Distinct().ToArray();
            var matches = bases.Where(c => string.Equals(c.name, "Walk_N", StringComparison.Ordinal)).ToArray();
            Require(matches.Length == 1, "Expected one exact existing Walk_N base slot; found " + matches.Length + ".");
            var original = matches[0]; var effective = original;
            for (int i = layers.Count - 1; i >= 0; --i)
            {
                var pairs = new List<KeyValuePair<AnimationClip, AnimationClip>>(layers[i].overridesCount); layers[i].GetOverrides(pairs);
                var matching = pairs.Where(p => p.Key == original || p.Key == effective).ToArray();
                Require(matching.Length <= 1, "Ambiguous Walk_N override binding.");
                if (matching.Length == 1 && matching[0].Value != null) effective = matching[0].Value;
            }
            Require(effective != null && effective.humanMotion && effective.isLooping && !effective.legacy && Finite(effective.length) && effective.length > .1f && effective.length <= 5f, "Walk_N must resolve to an existing looping Humanoid clip of 0.1–5 seconds; no retiming/loop setting is guessed.");
            string baseIdentity = Identity(original), effectiveIdentity = Identity(effective);
            Require(AnimationUtility.GetObjectReferenceCurveBindings(effective).Length == 0, "Walk QA refuses object-reference animation bindings.");
            var bindings = AnimationUtility.GetCurveBindings(effective);
            Require(bindings.Length > 0, "Walk_N has no readable native animation bindings.");
            var muscleProperties = new HashSet<string>(HumanTrait.MuscleName, StringComparer.Ordinal);
            foreach (string side in new[] { "Left", "Right" }) foreach (string finger in new[] { "Thumb", "Index", "Middle", "Ring", "Little" })
            {
                for (int joint = 1; joint <= 3; ++joint) muscleProperties.Add(side + "Hand." + finger + "." + joint + " Stretched");
                muscleProperties.Add(side + "Hand." + finger + ".Spread");
            }
            foreach (string prefix in new[] { "Root", "Motion", "Body", "LeftFoot", "RightFoot", "LeftHand", "RightHand" })
            {
                foreach (string axis in new[] { "x", "y", "z" }) muscleProperties.Add(prefix + "T." + axis);
                foreach (string axis in new[] { "x", "y", "z", "w" }) muscleProperties.Add(prefix + "Q." + axis);
            }
            // Imported humanoid muscles/root curves target Animator. Explicit transform curves
            // must bind only mapped body bones, never Hair/Dress/helper or renderer descendants.
            var bodyPaths = new HashSet<string>(StringComparer.Ordinal);
            var pathCounts = animator.GetComponentsInChildren<Transform>(true).GroupBy(t => AnimationUtility.CalculateTransformPath(t, animator.transform), StringComparer.Ordinal).ToDictionary(g => g.Key, g => g.Count(), StringComparer.Ordinal);
            var transformProperties = new HashSet<string>(StringComparer.Ordinal);
            foreach (string property in new[] { "m_LocalPosition", "m_LocalScale", "localEulerAnglesRaw" }) foreach (string axis in new[] { "x", "y", "z" }) transformProperties.Add(property + "." + axis);
            foreach (string axis in new[] { "x", "y", "z", "w" }) transformProperties.Add("m_LocalRotation." + axis);
            for (int i = 0; i < (int)HumanBodyBones.LastBone; ++i)
            {
                var bone = animator.GetBoneTransform((HumanBodyBones)i);
                if (bone != null) bodyPaths.Add(AnimationUtility.CalculateTransformPath(bone, animator.transform));
            }
            foreach (var b in bindings)
                Require(b.type == typeof(Animator) && b.path == "" && muscleProperties.Contains(b.propertyName) || b.type == typeof(Transform) && bodyPaths.Contains(b.path) && pathCounts[b.path] == 1 && transformProperties.Contains(b.propertyName), "Walk_N has an unsupported, ambiguous or unmapped body binding: " + b.path + "/" + b.propertyName);
            foreach (var kind in new[] { HumanBodyBones.Hips, HumanBodyBones.LeftUpperLeg, HumanBodyBones.RightUpperLeg, HumanBodyBones.LeftLowerLeg, HumanBodyBones.RightLowerLeg, HumanBodyBones.LeftFoot, HumanBodyBones.RightFoot })
            {
                var bone = animator.GetBoneTransform(kind); Require(bone != null && (bone == animator.transform || bone.IsChildOf(animator.transform)), "Missing exact native Humanoid binding: " + kind);
            }
            return new Binding { clip = effective, proof = "slot=Walk_N; controller=" + controllerIdentity + "; base=" + baseIdentity + "; effective=" + effectiveIdentity + "; avatar=" + Identity(animator.avatar) + "; length=" + effective.length.ToString("R", System.Globalization.CultureInfo.InvariantCulture) + "; curveBindings=" + bindings.Length };
        }
        public CharacterDressDynamicStressDriver(GameObject root, GameObject reference, Binding binding)
        {
            Require(root != null && reference != null && !EditorUtility.IsPersistent(root) && !EditorUtility.IsPersistent(reference) && root.scene.IsValid() && root.scene == reference.scene && root.scene.name.StartsWith("CharacterPoseStress_", StringComparison.Ordinal) && Application.isPlaying, "Dynamic Dress stimuli require the lifecycle owner's transient Play clones.");
            this.root = root; this.reference = reference; this.binding = binding ?? throw new ArgumentNullException(nameof(binding));
            animator = root.GetComponentInChildren<Animator>(true); referenceAnimator = reference.GetComponentInChildren<Animator>(true);
            Require(animator != null && referenceAnimator != null && animator.isHuman && referenceAnimator.isHuman && animator.avatar == referenceAnimator.avatar && root.GetComponentsInChildren<Animator>(true).Length == 1 && reference.GetComponentsInChildren<Animator>(true).Length == 1, "Ambiguous or incompatible owned Humanoid bindings.");
            neutral = CaptureBody(animator); referenceNeutral = CaptureBody(referenceAnimator);
            leftLeg = animator.GetBoneTransform(HumanBodyBones.LeftUpperLeg); rightLeg = animator.GetBoneTransform(HumanBodyBones.RightUpperLeg);
            rootPosition = root.transform.localPosition; rootRotation = root.transform.localRotation; rootScale = root.transform.localScale;
            referencePosition = reference.transform.localPosition; referenceRotation = reference.transform.localRotation; referenceScale = reference.transform.localScale;
        }
        static Pose[] CaptureBody(Animator animator)
        {
            var bones = new HashSet<Transform> { animator.transform };
            for (int i = 0; i < (int)HumanBodyBones.LastBone; ++i)
                for (var bone = animator.GetBoneTransform((HumanBodyBones)i); bone != null; bone = bone == animator.transform ? null : bone.parent)
                { Require(bone == animator.transform || bone.IsChildOf(animator.transform), "Humanoid ancestor escaped its Animator."); bones.Add(bone); }
            return bones.Select(t => new Pose { bone = t, position = t.localPosition, rotation = t.localRotation, scale = t.localScale }).ToArray();
        }
        static void Restore(Pose[] poses) { foreach (var p in poses) { p.bone.SetLocalPositionAndRotation(p.position, p.rotation); p.bone.localScale = p.scale; } }
        static void BlendToSample(Pose[] poses, float weight)
        {
            // These are only mapped native body bones and ancestors. Cloth bones are untouched.
            foreach (var p in poses) { p.bone.SetLocalPositionAndRotation(Vector3.Lerp(p.position, p.bone.localPosition, weight), Quaternion.Slerp(p.rotation, p.bone.localRotation, weight)); p.bone.localScale = Vector3.Lerp(p.scale, p.bone.localScale, weight); }
        }
        public static bool IsDynamic(string name) => Names.Contains(name);
        public float HoldSeconds(string name) => name == Names[0] ? Mathf.Max(2f, binding.clip.length * 2f) : 2f;
        public void BeginCase(string name, Vector3 up, Vector3 forward)
        {
            Require(IsDynamic(name) && Finite(up) && Finite(forward) && up.sqrMagnitude > .9f && forward.sqrMagnitude > .9f, "Invalid Dress dynamic stimulus.");
            StopGraphs(); current = name;
            anatomyUp = root.transform.parent != null ? root.transform.parent.InverseTransformDirection(up).normalized : up.normalized;
            anatomyForward = root.transform.parent != null ? root.transform.parent.InverseTransformDirection(forward).normalized : forward.normalized;
            previousPosition = rootPosition; previousTime = 0; previousCommandSpeed = 0; lastInputFrame = -1; stopCommandObserved = false;
            Current = new Proof { kind = name, binding = name == Names[0] ? binding.proof : "Explicit QA root transform stimulus; no controller/settings write", clipLength = name == Names[0] ? binding.clip.length : 0 };
            if (name == Names[0])
            {
                graph = CreateGraph(animator, "Owned Dress Walk", out playable);
                referenceGraph = CreateGraph(referenceAnimator, "Owned Dress Walk Reference", out referencePlayable);
            }
        }
        PlayableGraph CreateGraph(Animator a, string name, out AnimationClipPlayable clip)
        {
            a.applyRootMotion = false; a.fireEvents = false; a.enabled = true;
            var g = PlayableGraph.Create(name);
            try
            {
                g.SetTimeUpdateMode(DirectorUpdateMode.Manual);
                clip = AnimationClipPlayable.Create(g, binding.clip); clip.SetApplyFootIK(true); clip.SetApplyPlayableIK(false); clip.SetSpeed(0d);
                var output = AnimationPlayableOutput.Create(g, "Existing native Walk_N", a); output.SetSourcePlayable(clip); g.Play(); return g;
            }
            catch { if (g.IsValid()) g.Destroy(); a.enabled = false; throw; }
        }
        public void Apply(float time, float enter, float hold, float recover, float weight)
        {
            Require(Current != null && Finite(time) && time >= previousTime, "Dynamic stimulus time did not advance monotonically.");
            bool newInputFrame = lastInputFrame != Time.frameCount; lastEnter = enter; lastHold = hold;
            Vector3 displacement = Vector3.zero, commanded = Vector3.zero; float yaw = 0, clipTime = 0;
            if (current == Names[0])
            {
                Restore(neutral); Restore(referenceNeutral);
                float elapsed = Mathf.Clamp(time - enter, 0, hold); clipTime = Mathf.Repeat(elapsed, binding.clip.length);
                playable.SetTime(clipTime); referencePlayable.SetTime(clipTime); graph.Evaluate(0f); referenceGraph.Evaluate(0f);
                BlendToSample(neutral, weight); BlendToSample(referenceNeutral, weight);
                if (newInputFrame && time >= enter && time < enter + hold)
                {
                    int cycle = Mathf.FloorToInt((time - enter) / binding.clip.length);
                    if (cycle < 2)
                    {
                        var p = Current.firstTwoCycles[cycle];
                        if (p.sampledFrames == 0) { cycleLeft[cycle] = leftLeg.localRotation; cycleRight[cycle] = rightLeg.localRotation; }
                        p.sampledFrames++; p.leftLegExcursionDegrees = Mathf.Max(p.leftLegExcursionDegrees, Quaternion.Angle(cycleLeft[cycle], leftLeg.localRotation)); p.rightLegExcursionDegrees = Mathf.Max(p.rightLegExcursionDegrees, Quaternion.Angle(cycleRight[cycle], rightLeg.localRotation));
                    }
                }
                Current.completedWalkCycles = Mathf.Min(hold, Mathf.Max(0, time - enter)) / binding.clip.length;
            }
            else if (current == Names[1]) yaw = 90f * weight;
            else
            {
                float travelled = Mathf.Min(time, enter);
                if (time >= enter + hold) travelled *= 1f - Mathf.Clamp01((time - enter - hold) / recover);
                displacement = anatomyForward * (.5f * travelled);
                commanded = time < enter ? anatomyForward * .5f : time >= enter + hold && time < enter + hold + recover ? -anatomyForward * (.5f * enter / recover) : Vector3.zero;
                if (previousCommandSpeed > .1f && time >= enter && time < enter + hold) stopCommandObserved = true;
            }
            // Both clones receive exactly the same transform input. Source root motion is
            // suppressed; explicit QA movement is continuous in position at the sudden stop.
            root.transform.SetLocalPositionAndRotation(rootPosition + displacement, Quaternion.AngleAxis(yaw, anatomyUp) * rootRotation); root.transform.localScale = rootScale;
            reference.transform.SetLocalPositionAndRotation(referencePosition + displacement, Quaternion.AngleAxis(yaw, anatomyUp) * referenceRotation); reference.transform.localScale = referenceScale;
            if (!newInputFrame) return;
            float delta = time - previousTime, realDelta = Time.deltaTime;
            Vector3 step = root.transform.localPosition - previousPosition;
            Vector3 measured = realDelta > .000001f ? step / realDelta : Vector3.zero;
            Vector3 stimulusSpeed = delta > .000001f ? step / delta : Vector3.zero;
            Require(Finite(root.transform.localPosition) && Finite(root.transform.localRotation) && Finite(measured), "Non-finite dynamic root/body input.");
            Current.maximumRootSpeed = Mathf.Max(Current.maximumRootSpeed, measured.magnitude); Current.maximumRootYawDegrees = Mathf.Max(Current.maximumRootYawDegrees, Quaternion.Angle(rootRotation, root.transform.localRotation));
            if (current == Names[2])
            {
                if (time < enter) Current.maximumApproachRootSpeed = Mathf.Max(Current.maximumApproachRootSpeed, measured.magnitude);
                if (newInputFrame && time > enter + .1f && time < enter + hold && commanded.sqrMagnitude < .000001f && measured.sqrMagnitude < .000001f)
                { Current.stationaryAfterStopFrames++; if (stopCommandObserved) Current.abruptStopObserved = true; }
            }
            Current.inputFrames++; Current.input.Add(new InputSample { frame = Time.frameCount, time = time, clipTime = clipTime, frameDeltaTime = realDelta, stimulusDeltaTime = delta, rootLocalPosition = root.transform.localPosition, rootLocalRotation = root.transform.localRotation, commandedVelocity = commanded, measuredVelocity = measured, stimulusClockVelocity = stimulusSpeed, commandedYawDegrees = yaw });
            previousPosition = root.transform.localPosition; previousTime = time; previousCommandSpeed = commanded.magnitude; lastInputFrame = Time.frameCount;
        }
        public void ObserveNativeFrame(int nativeSubsteps)
        {
            if (Current == null || nativeSubsteps <= 0 || current != Names[0] || previousTime < lastEnter || previousTime >= lastEnter + lastHold) return;
            int cycle = Mathf.FloorToInt((previousTime - lastEnter) / binding.clip.length);
            if (cycle < 2) { Current.firstTwoCycles[cycle].nativeFrames++; Current.firstTwoCycles[cycle].nativeSubsteps += nativeSubsteps; }
        }
        public void Verify()
        {
            Require(Current != null && Current.inputFrames >= 30, "Insufficient real dynamic input frames.");
            Current.rootReturnError = Mathf.Max(Vector3.Distance(root.transform.localPosition, rootPosition), Quaternion.Angle(root.transform.localRotation, rootRotation) * Mathf.Deg2Rad);
            Require(Current.rootReturnError < .0001f, "QA root input did not return to its initial frame.");
            if (current == Names[0]) Require(Current.completedWalkCycles >= 2f && Current.firstTwoCycles.All(c => c.sampledFrames >= 10 && c.nativeFrames >= 10 && c.nativeSubsteps >= 10 && c.leftLegExcursionDegrees > .5f && c.rightLegExcursionDegrees > .5f), "Walk_N did not produce two actual native cycles with left/right leg motion and real cloth substeps.");
            if (current == Names[1]) Require(Current.maximumRootYawDegrees >= 89f, "Native root yaw did not reach its commanded turn.");
            if (current == Names[2]) Require(Current.abruptStopObserved && Current.maximumApproachRootSpeed >= .45f && Current.stationaryAfterStopFrames >= 10, "Moving-root abrupt stop was not observed at the requested real-frame approach speed.");
            Current.inputChecksCompleted = true;
        }
        public Vector3 RotatedView(Vector3 initial) => root.transform.rotation * Quaternion.Inverse(root.transform.parent != null ? root.transform.parent.rotation * rootRotation : rootRotation) * initial;
        void StopGraphs()
        {
            if (graph.IsValid()) graph.Destroy(); if (referenceGraph.IsValid()) referenceGraph.Destroy();
            if (animator != null) animator.enabled = false; if (referenceAnimator != null) referenceAnimator.enabled = false;
        }
        public void Dispose() { StopGraphs(); Restore(neutral); Restore(referenceNeutral); root.transform.SetLocalPositionAndRotation(rootPosition, rootRotation); root.transform.localScale = rootScale; reference.transform.SetLocalPositionAndRotation(referencePosition, referenceRotation); reference.transform.localScale = referenceScale; }
    }
}
