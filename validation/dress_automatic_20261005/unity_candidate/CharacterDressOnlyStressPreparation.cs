using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.RegularExpressions;
using MagicaCloth2;
using Unity.RandomRealm.CharacterPhysics;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Unity.RandomRealm.Editor
{
    // Candidate QA helper. Only an inactive, owned PreviewScene clone may be
    // changed. The saved profile is provenance/read-only input, never applied.
    internal static class CharacterDressOnlyStressPreparation
    {
        const string ModelPath = "Assets/Art/Character/Cosha/Cosha.fbx";
        const string OldWaist = "CoshaRig@0/Hips@0/SK_Dress_857c5a_Waist@0";
        const string NewWaist = "CoshaRig@0/Hips@0/SK_Dress_Waist@0";
        static readonly int[] RingOrder = { 4, 3, 2, 1, 8, 7, 6, 5 };
        static readonly Regex InstanceReference = new(@"\{\s*""instanceID""\s*:\s*-?\d+\s*\}");

        sealed class ColliderPlan
        {
            public CharacterPhysicsProfile.ColliderRecord Record;
            public CharacterPhysicsProfile.ColliderObjectRecord Pose;
            public Transform Parent, Symmetry;
        }

        public static MagicaCloth Prepare(GameObject clone, CharacterPhysicsProfile saved, Action<string> log)
        {
            Require(Unity.Multiplayer.PlayMode.CurrentPlayer.IsMainEditor && !AssetDatabase.IsAssetImportWorkerProcess()
                && !EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling
                && !EditorApplication.isUpdating && !AnimationMode.InAnimationMode(), "Dress QA requires the idle main Editor.");
            Require(clone != null && !EditorUtility.IsPersistent(clone) && !clone.activeInHierarchy
                && EditorSceneManager.IsPreviewScene(clone.scene), "Dress QA only changes an inactive owned PreviewScene clone.");
            Require(saved != null && EditorUtility.IsPersistent(saved) && (saved.Version == 1 || saved.Version == 2) && !saved.OwnerCheckpointRecorded
                && saved.Parts != null && saved.Colliders != null && saved.ColliderObjects != null,
                "A complete persistent Dress source record is required; temporary checkpoints cannot be used.");
            const string player = "Assets/Prefabs/Characters/Cosha/Cosha.Player.prefab";
            Require(saved.SourcePrefabGuid == AssetDatabase.AssetPathToGUID(player), "Dress provenance belongs to another Player prefab.");
            var records = saved.Parts.Where(p => p != null && p.Part == CharacterPhysicsPart.Dress).ToArray();
            Require(records.Length == 1, "Dress provenance must contain exactly one Dress record.");
            var record = records[0];
            Require(string.IsNullOrEmpty(record.HairStrandId) && !record.SelectionCheckpointRecorded
                && string.IsNullOrEmpty(record.SelectionJson) && string.IsNullOrEmpty(record.SelectionRootSignature),
                "This bounded rename fixture does not migrate authored painted selection or Hair records.");
            Require(record.Enabled && record.References != null && !string.IsNullOrEmpty(record.ParametersJson)
                && !record.ParametersJson.Contains("\"instanceID\""), "Dress provenance has incomplete or transient parameters.");
            var data = JsonUtility.FromJson<ClothSerializeData>(record.ParametersJson);
            Require(data != null && data.clothType == ClothProcess.ClothType.BoneCloth
                && data.connectionMode == RenderSetupData.BoneConnectionMode.SequentialLoopMesh
                && data.rootBones != null && data.rootBones.Count == 8
                && data.colliderCollisionConstraint?.colliderList?.Count == 3,
                "Only the existing eight-root closed-loop Dress and its three explicit colliders are supported.");

            var renderers = clone.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r => r.name == "Dress").ToArray();
            Require(renderers.Length == 1 && renderers[0].sharedMesh != null
                && AssetDatabase.GetAssetPath(renderers[0].sharedMesh) == ModelPath,
                "Dress must use the current imported Cosha.fbx mesh, not a stale or private Hair fixture.");
            var waist = Resolve(clone.transform, NewWaist);
            Require(waist != null && waist.parent == Resolve(clone.transform, "CoshaRig@0/Hips@0")
                && Resolve(clone.transform, OldWaist) == null, "The one exact renamed Waist hierarchy is not present.");
            var roots = new List<Transform>();
            var references = new Dictionary<string, CharacterPhysicsProfile.ObjectReference>(StringComparer.Ordinal);
            foreach (var reference in record.References)
                Require(reference != null && !string.IsNullOrEmpty(reference.PropertyPath)
                    && reference.PropertyPath.StartsWith("serializeData.", StringComparison.Ordinal)
                    && references.TryAdd(reference.PropertyPath, reference), "Dress native reference fields are missing or duplicated.");
            for (int i = 0; i < RingOrder.Length; ++i)
            {
                string number = RingOrder[i].ToString("D2", CultureInfo.InvariantCulture);
                string field = "serializeData.rootBones.Array.data[" + i + "]";
                string oldPath = OldWaist + "/SK_Dress_857c5a_DEF_" + number + "_01@0";
                string newPath = NewWaist + "/SK_Dress_DEF_" + number + "_01@0";
                Require(references.TryGetValue(field, out var reference)
                    && reference.Kind == CharacterPhysicsProfile.ReferenceKind.Transform && reference.TransformPath == oldPath,
                    "Dress root provenance/order changed at " + field + "; no guessed mapping is permitted.");
                var root = Resolve(clone.transform, newPath);
                Require(root != null && root.parent == waist && Resolve(clone.transform, oldPath) == null,
                    "Missing or ambiguous exact renamed Dress root: " + newPath);
                Transform segment = root;
                for (int j = 1; j <= 4; ++j)
                {
                    Require(segment != null && segment.name == "SK_Dress_DEF_" + number + "_" + j.ToString("D2", CultureInfo.InvariantCulture)
                        && segment.childCount == (j == 4 ? 0 : 1), "Dress must retain each exact four-segment chain.");
                    segment = j == 4 ? null : segment.GetChild(0);
                }
                roots.Add(root);
            }
            var discovered = CharacterPhysicsSetupService.DiscoverRoots(clone, CharacterPhysicsPart.Dress);
            Require(discovered.Count == 8 && new HashSet<Transform>(discovered).SetEquals(roots),
                "Current skin weights, fixed Waist and complete disjoint chains do not prove the exact Dress root set.");

            var colliderPlans = new List<ColliderPlan>();
            for (int i = 0; i < 3; ++i)
            {
                string field = "serializeData.colliderCollisionConstraint.colliderList.Array.data[" + i + "]";
                Require(references.TryGetValue(field, out var reference)
                    && reference.Kind == CharacterPhysicsProfile.ReferenceKind.Component
                    && reference.ComponentIndex == 0 && reference.ComponentType == typeof(MagicaCapsuleCollider).FullName,
                    "Dress collision provenance must identify the three exact native capsule components.");
                var matches = saved.Colliders.Where(c => c?.Component != null && SameReference(c.Component, reference)).ToArray();
                var poses = saved.ColliderObjects.Where(p => p != null && p.TransformPath == reference.TransformPath).ToArray();
                Require(matches.Length == 1 && poses.Length == 1 && matches[0].Enabled && poses[0].Active,
                    "An explicit Dress collider record or its dedicated object pose is absent or ambiguous.");
                var pose = poses[0]; var collider = matches[0];
                var parent = Resolve(clone.transform, ParentPath(pose.TransformPath));
                Require(parent != null && Finite(pose.LocalPosition) && Finite(pose.LocalScale)
                    && Finite(pose.LocalRotation) && pose.LocalScale.x > 0 && pose.LocalScale.y > 0 && pose.LocalScale.z > 0
                    && Finite(collider.Center) && Finite(collider.Size)
                    && collider.Size.x > 0 && collider.Size.y > 0 && collider.Size.z > 0,
                    "Dress collider attachment or dimensions cannot be copied safely.");
                var symmetry = ResolveTransformReference(clone.transform, collider.SymmetryTarget);
                colliderPlans.Add(new ColliderPlan { Record = collider, Pose = pose, Parent = parent, Symmetry = symmetry });
            }
            Require(colliderPlans.Select(p => p.Record.Component.TransformPath).Distinct().Count() == 3,
                "Dress collider provenance contains duplicate components.");
            // Preflight all remaining fields before creating anything. No production
            // Hair part, collider record or holder is ever applied to this clone.
            foreach (var pair in references)
            {
                if (IsRootField(pair.Key) || IsColliderField(pair.Key)) continue;
                Require(pair.Value.Kind == CharacterPhysicsProfile.ReferenceKind.None,
                    "Unsupported extra Dress native reference: " + pair.Key);
            }
            string sourceJson = JsonUtility.ToJson(saved);
            var protectedColliders = clone.GetComponentsInChildren<ColliderComponent>(true);
            var existingOwner = clone.GetComponent<CharacterPhysicsRig>();
            var protectedCloths = clone.GetComponentsInChildren<MagicaCloth>(true)
                .Where(c => existingOwner == null || c != existingOwner.Dress).ToArray();
            string nonDress = NonDressState(clone, protectedColliders, protectedCloths);
            var copies = new List<ColliderComponent>();
            for (int i = 0; i < colliderPlans.Count; ++i)
            {
                var plan = colliderPlans[i];
                var holder = new GameObject("Owned Dress QA Collider " + i);
                SceneManager.MoveGameObjectToScene(holder, clone.scene);
                holder.transform.SetParent(plan.Parent, false);
                holder.transform.SetLocalPositionAndRotation(plan.Pose.LocalPosition, plan.Pose.LocalRotation);
                holder.transform.localScale = plan.Pose.LocalScale;
                var collider = holder.AddComponent<MagicaCapsuleCollider>();
                collider.center = plan.Record.Center; collider.SetSize(plan.Record.Size);
                collider.symmetryMode = plan.Record.SymmetryMode; collider.symmetryTarget = plan.Symmetry;
                collider.direction = plan.Record.Direction; collider.reverseDirection = plan.Record.ReverseDirection;
                collider.radiusSeparation = plan.Record.RadiusSeparation; collider.alignedOnCenter = plan.Record.AlignedOnCenter;
                collider.enabled = true; collider.UpdateParameters();
                using (var serialized = new SerializedObject(collider))
                    Require(serialized.FindProperty("size").vector3Value.Equals(plan.Record.Size), "Native collider size changed during copy.");
                Require(collider.center.Equals(plan.Record.Center) && collider.symmetryMode == plan.Record.SymmetryMode
                    && collider.symmetryTarget == plan.Symmetry && collider.direction == plan.Record.Direction
                    && collider.reverseDirection == plan.Record.ReverseDirection && collider.radiusSeparation == plan.Record.RadiusSeparation
                    && collider.alignedOnCenter == plan.Record.AlignedOnCenter, "Native Dress collider parameters changed during copy.");
                copies.Add(collider);
            }
            var clothHolder = new GameObject("Owned Dress QA Native"); SceneManager.MoveGameObjectToScene(clothHolder, clone.scene);
            clothHolder.transform.SetParent(clone.transform, false);
            var cloth = clothHolder.AddComponent<MagicaCloth>(); cloth.enabled = false;
            JsonUtility.FromJsonOverwrite(record.ParametersJson, cloth.SerializeData);
            using (var serialized = new SerializedObject(cloth))
            {
                foreach (var pair in references)
                {
                    var field = serialized.FindProperty(pair.Key);
                    Require(field != null && field.propertyType == SerializedPropertyType.ObjectReference,
                        "The native Dress reference field changed: " + pair.Key);
                    if (IsRootField(pair.Key)) field.objectReferenceValue = roots[FieldIndex(pair.Key)];
                    else if (IsColliderField(pair.Key)) field.objectReferenceValue = copies[FieldIndex(pair.Key)];
                    else field.objectReferenceValue = null;
                }
                serialized.ApplyModifiedPropertiesWithoutUndo();
            }
            Require(cloth.SerializeData.rootBones.SequenceEqual(roots)
                && cloth.SerializeData.colliderCollisionConstraint.colliderList.SequenceEqual(copies)
                && Normalize(JsonUtility.ToJson(cloth.SerializeData)) == Normalize(JsonUtility.ToJson(data))
                && cloth.SerializeData.IsValid(), "The QA cloth changed native Dress parameters/order or has invalid references.");
            Require(JsonUtility.ToJson(saved) == sourceJson && NonDressState(clone, protectedColliders, protectedCloths) == nonDress,
                "Preparation changed saved profile or current Hair/collider parameters.");
            // This fixture measures Dress only. Keep other cloths stationary on
            // the disposable clone; their native settings/selection stay intact.
            foreach (var other in clone.GetComponentsInChildren<MagicaCloth>(true)) if (other != cloth) other.enabled = false;
            var rig = clone.GetComponent<CharacterPhysicsRig>();
            if (rig == null) rig = clone.AddComponent<CharacterPhysicsRig>();
            rig.Dress = cloth; cloth.enabled = true;
            log("Dress-only fixture: current imported Cosha skin; exact eight renamed roots, four weighted segments each; saved SequentialLoopMesh order/parameters and three QA-only colliders. No Hair setup/profile apply; other clone cloths are stationary.");
            foreach (var root in roots) log("Dress root: " + CharacterHairMotionRig.PathOf(clone.transform, root));
            return cloth;
        }

        static string NonDressState(GameObject root, IEnumerable<ColliderComponent> protectedColliders, IEnumerable<MagicaCloth> protectedCloths)
        {
            var rows = new List<string>();
            foreach (var cloth in protectedCloths)
                rows.Add(CharacterHairMotionRig.PathOf(root.transform, cloth.transform) + "|" + cloth.enabled + "|"
                    + JsonUtility.ToJson(cloth.SerializeData) + "|" + JsonUtility.ToJson(cloth.GetSerializeData2().selectionData));
            foreach (var hair in root.GetComponentsInChildren<CharacterHairMotionRig>(true)) rows.Add(JsonUtility.ToJson(hair));
            foreach (var collider in protectedColliders) rows.Add(JsonUtility.ToJson(collider));
            return string.Join("\n", rows);
        }
        public static string ParameterState(MagicaCloth cloth) => Normalize(JsonUtility.ToJson(cloth.SerializeData));
        static string Normalize(string json)
        {
            string result = InstanceReference.Replace(json, "null");
            Require(!result.Contains("\"instanceID\""), "Unity native object JSON format changed; do not normalize by guessing.");
            return result;
        }
        static bool SameReference(CharacterPhysicsProfile.ObjectReference a, CharacterPhysicsProfile.ObjectReference b)
            => a.Kind == b.Kind && a.TransformPath == b.TransformPath && a.ComponentType == b.ComponentType && a.ComponentIndex == b.ComponentIndex;
        static bool IsRootField(string field) => Regex.IsMatch(field, @"\AserializeData\.rootBones\.Array\.data\[[0-7]\]\z");
        static bool IsColliderField(string field) => Regex.IsMatch(field, @"\AserializeData\.colliderCollisionConstraint\.colliderList\.Array\.data\[[0-2]\]\z");
        static int FieldIndex(string field) => int.Parse(field.Substring(field.LastIndexOf('[') + 1).TrimEnd(']'), CultureInfo.InvariantCulture);
        static Transform ResolveTransformReference(Transform root, CharacterPhysicsProfile.ObjectReference reference)
        {
            if (reference == null || reference.Kind == CharacterPhysicsProfile.ReferenceKind.None) return null;
            Require(reference.Kind == CharacterPhysicsProfile.ReferenceKind.Transform, "Unsupported collider symmetry reference.");
            var node = Resolve(root, reference.TransformPath); Require(node != null, "Missing exact collider symmetry target."); return node;
        }
        static Transform Resolve(Transform root, string path)
        {
            Require(path != null, "Missing exact character path.");
            var node = root;
            if (path.Length == 0) return node;
            foreach (string segment in path.Split('/'))
            {
                int at = segment.LastIndexOf('@');
                Require(at > 0 && int.TryParse(segment.Substring(at + 1), out int ordinal) && ordinal >= 0, "Invalid exact ordinal path.");
                ordinal = int.Parse(segment.Substring(at + 1), CultureInfo.InvariantCulture);
                string name = Uri.UnescapeDataString(segment.Substring(0, at));
                Transform found = null;
                for (int i = 0; i < node.childCount; ++i) if (node.GetChild(i).name == name && ordinal-- == 0) { found = node.GetChild(i); break; }
                if (found == null) return null; node = found;
            }
            return node;
        }
        static string ParentPath(string path) => path.Substring(0, path.LastIndexOf('/'));
        static bool Finite(Vector3 v) => float.IsFinite(v.x) && float.IsFinite(v.y) && float.IsFinite(v.z);
        static bool Finite(Quaternion q) => float.IsFinite(q.x) && float.IsFinite(q.y) && float.IsFinite(q.z) && float.IsFinite(q.w)
            && q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w > .00001f;
        static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
    }
}
