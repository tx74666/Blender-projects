// Explicit native acceptance only. Never runs on load, through TestRunner, or against production model imports.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace CharacterDesigner.Unity.Editor
{
    public static class CharacterMaterialMatchingVerification
    {
        const string SourceModel = "Assets/Art/Character/Cosha/Cosha.fbx";
        const string SourceMaterial = "Assets/Art/Materials/Crystal/M_CrystalBlue.mat";
        const string SourceName = "Crystal_Blue";
        const string MissingSource = "__MaterialMatchVerificationMissingSource__";
        static readonly PropertyInfo DirtyId = typeof(Scene).GetProperty("dirtyID", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        static bool running;

        sealed class Stamp
        {
            internal string path, hash;
            internal bool exists, assetDirty, importerDirty;
        }
        sealed class Run
        {
            internal string id, folder, model, manifest, root, directory;
            internal Material first, alternate;
            internal JObject document, report;
            internal CharacterMaterialMatching.VerificationSession session;
            internal int revision;
        }

        [MenuItem("Tools/Character Designer/Validation/Verify Material Matching (Isolated)")]
        public static void Verify()
        {
            if (running) { Debug.LogWarning("Character material verification is already running."); return; }
            running = true;
            try { VerifyCore(); }
            finally { running = false; }
        }
        static void VerifyCore()
        {
            string id = Guid.NewGuid().ToString("N");
            string root = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            var run = new Run { id = id, root = root, folder = "Assets/~QA_MaterialMatching_" + id,
                directory = Path.Combine(root, ".codex", "task-staging", "character2-material-match-20261010", "native-verification", id) };
            run.model = run.folder + "/Fixture.fbx";
            run.manifest = run.folder + "/Fixture.cdesigner.json";
            run.report = new JObject { ["schema"] = "cdesigner.material-match-verification/1", ["utc"] = DateTime.UtcNow.ToString("O"),
                ["unity_version"] = Application.unityVersion, ["run_id"] = id, ["fixture_folder"] = run.folder,
                ["cases"] = new JArray(), ["passed"] = false, ["undo_native_verified"] = false,
                ["limitations"] = new JArray("Global Undo/Redo is deliberately not invoked or registered for the fixture.",
                    "The native Material picker, preview, immediate Loading repaint and busy-editor recovery need separate UI evidence.",
                    "This uses copied current FBX bytes with fresh manifests; a genuine changed-FBX Blender re-export remains separate.",
                    "Runtime prefab/Forearm regeneration is outside this fixture; no forearm sidecar is copied.") };
            Object[] selection = Selection.objects;
            Object activeSelection = Selection.activeObject;
            string scenes = SceneState();
            int undoGroup = Undo.GetCurrentGroup();
            string undoName = Undo.GetCurrentGroupName();
            List<Stamp> originals = null, fixtureMaterials = null;
            Dictionary<string, string> receipts = null;
            string sourceRenderers = null;
            try
            {
                Require(CharacterMaterialMatching.MainEditor && !CharacterMaterialMatching.EditorBusy,
                    "Use the idle main Editor with Play stopped and no build, compilation or import in progress.");
                Require(AssetDatabase.LoadAssetAtPath<GameObject>(SourceModel) != null, "The current Cosha source model is missing.");
                var sourceMaterial = AssetDatabase.LoadAssetAtPath<Material>(SourceMaterial);
                Require(sourceMaterial != null && !EditorUtility.IsDirty(sourceMaterial), "The existing Crystal Material must have no pending asset edits.");
                var sourceImporter = AssetImporter.GetAtPath(SourceModel);
                Require(sourceImporter != null && !EditorUtility.IsDirty(sourceImporter), "The source model has pending Inspector edits.");
                run.session = CharacterMaterialMatching.BeginIsolatedVerification(run.model, run.id);
                originals = CaptureOriginals(run.session.ProtectedAssetPaths);
                receipts = ReceiptSnapshot(run.session.StorePath, run.id);
                sourceRenderers = RendererIdentity(SourceModel);
                run.report["scene_before"] = scenes;
                run.report["undo_group_before"] = undoGroup;
                run.report["undo_name_before"] = undoName;
                Require(!string.IsNullOrEmpty(AssetDatabase.CreateFolder("Assets", run.folder.Substring(7))), "Could not create the new fixture folder.");
                Require(AssetDatabase.CopyAsset(SourceModel, run.model), "Could not copy the source FBX.");
                string firstPath = run.folder + "/Matched.mat", alternatePath = run.folder + "/Alternate.mat";
                Require(AssetDatabase.CopyAsset(SourceMaterial, firstPath) && AssetDatabase.CopyAsset(SourceMaterial, alternatePath), "Could not copy the two Material fixtures.");
                AssetDatabase.ImportAsset(run.model, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
                run.first = AssetDatabase.LoadAssetAtPath<Material>(firstPath);
                run.alternate = AssetDatabase.LoadAssetAtPath<Material>(alternatePath);
                Require(run.first != null && run.alternate != null && run.first != run.alternate, "The fixture Materials have no distinct persistent identities.");
                fixtureMaterials = new[] { firstPath, alternatePath }.SelectMany(path => new[] { path, path + ".meta" }).Select(Capture).ToList();
                var originalManifest = JObject.Parse(File.ReadAllText(Path.ChangeExtension(Full(run, SourceModel), ".cdesigner.json")));
                Require(originalManifest["materials"] is JArray inventory && inventory.OfType<JValue>().Any(value => value.Value<string>() == SourceName), "The current source manifest does not contain Crystal_Blue.");
                run.document = new JObject { ["schema"] = "cdesigner.unity-character.v1", ["ok"] = true,
                    ["asset_id"] = run.id, ["filename"] = "Fixture.fbx", ["files"] = new JObject { ["Fixture.fbx"] = Hash(Full(run, run.model)) },
                    ["materials"] = originalManifest["materials"].DeepClone(), ["simple_materials"] = new JArray(), ["unity_material_matches"] = new JArray() };
                run.session.SetFixtureRemap(SourceName, null);
                Publish(run, new JArray(), new JArray());

                Case(run, "native_inventory_and_new_identities", () =>
                {
                    run.session.ValidateSource(SourceName);
                    Require(AssetDatabase.AssetPathToGUID(SourceModel) != AssetDatabase.AssetPathToGUID(run.model), "The fixture FBX reused the source GUID.");
                    Require(AssetDatabase.AssetPathToGUID(SourceMaterial) != AssetDatabase.AssetPathToGUID(firstPath), "The fixture Material reused the source GUID.");
                    Require(!Map(run).ContainsKey(Key(SourceName)), "The initial fixture remap was not cleared.");
                    Evidence(run)["source_inventory"] = NativeInventory(run.model);
                });
                Case(run, "cancel_and_timeout_leave_map_unchanged", () =>
                {
                    var before = Map(run);
                    var cancelled = run.session.CreateRequest(SourceName);
                    run.session.Cancel(cancelled); run.session.Enqueue(cancelled);
                    CheckResult(run, cancelled, "cancelled");
                    var expired = run.session.CreateRequest(SourceName, 181);
                    run.session.Enqueue(expired); CheckResult(run, expired, "failed");
                    Require(SameMap(before, Map(run)), "Cancelled or expired input changed a remap.");
                });
                Case(run, "duplicate_and_first_match", () =>
                {
                    var request = run.session.CreateRequest(SourceName);
                    run.session.Enqueue(request); run.session.Enqueue(request);
                    Require(run.session.QueuedCount(request) == 1 && run.session.Result(request) == null, "A duplicate request was not queued exactly once.");
                    var duplicateSource = run.session.CreateRequest(SourceName);
                    run.session.Enqueue(duplicateSource); CheckResult(run, duplicateSource, "failed");
                    var result = run.session.ApplyRequest(request, run.first);
                    Require(result != null && result.status == "matched", "The native first match failed: " + result?.error);
                    CheckResult(run, request, "matched"); Matched(run, run.first);
                    string resultHash = Hash(Path.Combine(run.session.StorePath, "requests", request.request_id + ".result.json"));
                    run.session.Enqueue(request);
                    Require(resultHash == Hash(Path.Combine(run.session.StorePath, "requests", request.request_id + ".result.json")), "A terminal duplicate rewrote the result.");
                });
                Case(run, "fresh_manifest_and_latest_manual_match", () =>
                {
                    Publish(run, Matches(run, run.first), new JArray()); run.session.Process(); Matched(run, run.first);
                    var request = run.session.CreateRequest(SourceName); run.session.Enqueue(request);
                    var result = run.session.ApplyRequest(request, run.alternate);
                    Require(result != null && result.status == "matched", "The alternate manual match failed: " + result?.error);
                    run.session.Process(); Matched(run, run.alternate);
                    Require(run.session.Receipt(SourceName).explicit_choice, "The latest manual receipt lost its explicit choice.");
                    Publish(run, Matches(run, run.first), new JArray()); run.session.Process(); Matched(run, run.first);
                });
                Case(run, "failed_manual_receipt_only_verifies_across_restart", () =>
                {
                    Publish(run, Matches(run, run.first), new JArray()); run.session.Process(); Matched(run, run.first);
                    var request = run.session.CreateRequest(SourceName); run.session.Enqueue(request);
                    var result = run.session.ApplyRequest(request, run.alternate);
                    Require(result != null && result.status == "matched", "The manual override precondition failed: " + result?.error);
                    Matched(run, run.alternate);
                    foreach (Material reverted in new[] { run.first, null })
                    {
                        // These private map changes simulate Undo/Redo state; they never touch the global Undo stack.
                        run.session.SetFixtureRemap(SourceName, reverted);
                        var before = Map(run);
                        run.session.Process(false); FailedManual(run, run.alternate);
                        Require(SameMap(before, Map(run)), "Verification repaired a manually reverted map.");
                        run.session.ForgetVerifiedSignature();
                        run.session.Process(); FailedManual(run, run.alternate);
                        Require(SameMap(before, Map(run)) && !RendererUses(run.model, run.alternate), "Restart-style verification replayed the failed latest choice or the older declared match.");
                        run.session.SetFixtureRemap(SourceName, run.alternate);
                        run.session.Process(false); Matched(run, run.alternate);
                        Require(CurrentReceipt(run, "matched").explicit_choice, "Restoring the exact map lost the explicit manual choice.");
                    }
                    // A manual match may be newer than an unchanged Simple report as well as an unchanged match report.
                    Publish(run, new JArray(), Simple()); run.session.Process();
                    var simpleRequest = run.session.CreateRequest(SourceName); run.session.Enqueue(simpleRequest);
                    var simpleResult = run.session.ApplyRequest(simpleRequest, run.alternate);
                    Require(simpleResult != null && simpleResult.status == "matched", "The manual-after-Simple precondition failed: " + simpleResult?.error);
                    run.session.SetFixtureRemap(SourceName, null);
                    var cleared = Map(run);
                    run.session.Process(false); FailedManual(run, run.alternate);
                    run.session.ForgetVerifiedSignature(); run.session.Process(); FailedManual(run, run.alternate);
                    Require(SameMap(cleared, Map(run)), "An old Simple report replayed a failed latest manual choice.");
                    run.session.SetFixtureRemap(SourceName, run.alternate); run.session.Process(false); Matched(run, run.alternate);
                    Require(CurrentReceipt(run, "matched").explicit_choice, "The old Simple report cleared the restored latest manual choice.");
                    Publish(run, Matches(run, run.first), new JArray()); run.session.Process(); Matched(run, run.first);
                    Require(!CurrentReceipt(run, "matched").explicit_choice, "The new report did not restore automatic binding intent.");
                    run.session.SetFixtureRemap(SourceName, null);
                    run.session.Process(false);
                    var automaticFailure = CurrentReceipt(run, "failed");
                    Require(!automaticFailure.explicit_choice && automaticFailure.material_guid == AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(run.first)) && !Map(run).ContainsKey(Key(SourceName)), "The automatic temporary-failure precondition is invalid.");
                    Evidence(run)["automatic_failure_receipt"] = JObject.FromObject(automaticFailure);
                    // A new event retries the unchanged valid report; no polling, new manifest or signature-forget helper is used here.
                    run.session.ProcessQueued(); Matched(run, run.first);
                    Require(!CurrentReceipt(run, "matched").explicit_choice, "Automatic report retry became a manual choice.");
                });
                Case(run, "fresh_simplified_then_original", () =>
                {
                    Publish(run, new JArray(), Simple()); run.session.Process();
                    Require(!Map(run).ContainsKey(Key(SourceName)), "A fresh Simplified export retained its owned remap.");
                    Require(!RendererUses(run.model, run.first) && !RendererUses(run.model, run.alternate), "Simplified renderers retained a copied target Material.");
                    var simple = CurrentReceipt(run, "failed");
                    Require(simple.error.StartsWith("Using Simplified:", StringComparison.Ordinal), "The Simplified receipt was not reported truthfully.");
                    Evidence(run)["simplified_receipt"] = JObject.FromObject(simple);
                    Publish(run, Matches(run, run.first), new JArray()); run.session.Process(); Matched(run, run.first);
                });
                Case(run, "foreign_remap_retained_for_simplified", () =>
                {
                    run.session.SetFixtureRemap(SourceName, run.alternate);
                    Publish(run, new JArray(), Simple()); run.session.Process();
                    Require(Map(run).TryGetValue(Key(SourceName), out var retained) && retained == run.alternate && RendererUses(run.model, run.alternate), "Simplified removed or replaced a user-changed remap.");
                    var review = CurrentReceipt(run, "failed");
                    Require(review.error.StartsWith("Review:", StringComparison.Ordinal), "A foreign remap did not request review.");
                    Evidence(run)["retained_receipt"] = JObject.FromObject(review);
                });
                Case(run, "missing_native_source_rejects_entire_map_batch", () =>
                {
                    var before = Map(run);
                    ((JArray)run.document["materials"]).Add(MissingSource);
                    var matches = Matches(run, run.first); matches.Add(Match(run, run.alternate, MissingSource));
                    Publish(run, matches, new JArray()); run.session.Process();
                    Require(SameMap(before, Map(run)) && !Map(run).ContainsKey(Key(MissingSource)), "Invalid source validation left a partial remap batch.");
                    var rejected = CurrentReceipt(run, "failed");
                    Require(rejected.material_guid == AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(run.first)) && rejected.error.Contains("source material"), "The missing native source did not reject the current valid binding batch.");
                    Evidence(run)["failure_receipt"] = JObject.FromObject(rejected);
                    var request = run.session.CreateRequest(MissingSource); run.session.Enqueue(request);
                    var result = run.session.ApplyRequest(request, run.first);
                    Require(result != null && result.status == "failed" && SameMap(before, Map(run)), "A request for a nonexistent native source altered a remap.");
                    CheckResult(run, request, "failed");
                    ((JArray)run.document["materials"]).Remove(((JArray)run.document["materials"]).First(value => value.Value<string>() == MissingSource));
                });
                Case(run, "missing_target_and_foreign_manifest_do_not_mutate", () =>
                {
                    var before = Map(run);
                    JObject missing = Match(run, run.first, SourceName); missing["material_guid"] = new string('0', 32);
                    Publish(run, new JArray(missing), new JArray()); run.session.Process();
                    Require(SameMap(before, Map(run)) && CurrentReceipt(run, "failed").material_guid == new string('0', 32), "A missing target changed the map or did not record this current failed target.");
                    Evidence(run)["missing_target_receipt"] = JObject.FromObject(run.session.Receipt(SourceName));
                    JObject foreign = Match(run, run.first, SourceName); foreign["export_asset_id"] = Guid.NewGuid().ToString("N");
                    Publish(run, new JArray(foreign), new JArray()); run.session.Process();
                    Require(SameMap(before, Map(run)), "A foreign export identity changed the fixture map.");
                    run.document["asset_id"] = Guid.NewGuid().ToString("N");
                    Publish(run, new JArray(), new JArray()); run.session.Process();
                    Require(SameMap(before, Map(run)), "A different profile changed the fixture map.");
                    var request = run.session.CreateRequest(SourceName); run.session.Enqueue(request);
                    var result = run.session.ApplyRequest(request, run.first);
                    Require(result != null && result.status == "failed" && result.error.Contains("export profile") && SameMap(before, Map(run)), "A request for a different export profile was not rejected before mutation.");
                    CheckResult(run, request, "failed");
                    run.document["asset_id"] = run.id;
                    Publish(run, Matches(run, run.first), new JArray()); run.session.Process(); Matched(run, run.first);
                });
            }
            catch (Exception error) { run.report["error"] = error.ToString(); }
            finally
            {
                try { run.session?.Dispose(); }
                catch (Exception error) { AddError(run, "Session recovery: " + error); }
                try
                {
                    if (!Selection.objects.SequenceEqual(selection)) Selection.objects = selection;
                    if (Selection.activeObject != activeSelection) Selection.activeObject = activeSelection;
                }
                catch (Exception error) { AddError(run, "Selection recovery: " + error); }
                try
                {
                    string after = SceneState();
                    run.report["scene_after"] = after;
                    bool scenesPreserved = scenes == after;
                    bool selectionPreserved = Selection.objects.SequenceEqual(selection) && Selection.activeObject == activeSelection;
                    bool originalsPreserved = originals != null && originals.All(Unchanged) && sourceRenderers == RendererIdentity(SourceModel);
                    bool materialsPreserved = fixtureMaterials != null && fixtureMaterials.All(Unchanged);
                    bool receiptsPreserved = receipts != null && SameSnapshot(receipts, ReceiptSnapshot(Path.Combine(root, ".codex", "character-material-matches"), id));
                    bool undoGroupPreserved = undoGroup == Undo.GetCurrentGroup() && undoName == Undo.GetCurrentGroupName();
                    run.report["preservation"] = new JObject { ["scenes"] = scenesPreserved, ["selection"] = selectionPreserved,
                        ["original_assets_and_shared_materials"] = originalsPreserved, ["copied_material_contents"] = materialsPreserved,
                        ["other_profiles_receipts"] = receiptsPreserved, ["undo_group_and_name"] = undoGroupPreserved,
                        ["undo_record_suppressed_for_exact_fixture"] = true, ["undo_full_history_verified"] = false };
                    run.report["original_file_stamps"] = originals == null ? new JArray() : new JArray(originals.Select(value => new JObject { ["path"] = value.path, ["exists"] = value.exists, ["sha256"] = value.hash, ["asset_dirty"] = value.assetDirty, ["importer_dirty"] = value.importerDirty }));
                    if (!scenesPreserved || !selectionPreserved || !originalsPreserved || !materialsPreserved || !receiptsPreserved || !undoGroupPreserved)
                        AddError(run, "Scene, selection, asset, Material, receipt or Undo-group preservation failed. No production restoration was attempted.");
                    run.report["passed"] = run.report["error"] == null && ((JArray)run.report["cases"]).Count == 9 && ((JArray)run.report["cases"]).All(value => value["passed"].Value<bool>());
                }
                catch (Exception error) { AddError(run, "Preservation check: " + error); }
                try
                {
                    Directory.CreateDirectory(run.directory);
                    string path = Path.Combine(run.directory, "report.json");
                    File.WriteAllText(path, run.report.ToString(), new UTF8Encoding(false));
                    if (run.report["passed"].Value<bool>()) Debug.Log("Character material isolated verification passed. Native Undo/UI/re-export acceptance remains separate: " + path);
                    else Debug.LogError("Character material isolated verification failed: " + path + "\n" + run.report["error"]);
                }
                finally { running = false; }
            }
        }

        static void Case(Run run, string name, Action action)
        {
            var evidence = new JObject { ["name"] = name, ["passed"] = false };
            ((JArray)run.report["cases"]).Add(evidence);
            try { action(); evidence["passed"] = true; }
            catch (Exception error) { evidence["error"] = error.Message; throw; }
        }
        static JObject Evidence(Run run) => (JObject)((JArray)run.report["cases"]).Last;
        static void Publish(Run run, JArray matches, JArray simple)
        {
            run.document["unity_material_matches"] = matches;
            run.document["simple_materials"] = simple;
            run.document["verification_revision"] = ++run.revision;
            File.WriteAllText(Full(run, run.manifest), run.document.ToString(), new UTF8Encoding(false));
            AssetDatabase.ImportAsset(run.manifest, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
        }
        static JArray Simple() => new JArray(new JObject { ["material"] = SourceName });
        static JArray Matches(Run run, Material material) => new JArray(Match(run, material, SourceName));
        static JObject Match(Run run, Material material, string source)
        {
            Require(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out string guid, out long local), "A copied Material has no persistent identity.");
            return new JObject { ["source_material"] = source, ["material_guid"] = guid, ["material_local_id"] = local, ["project_root"] = run.root, ["export_asset_id"] = run.id };
        }
        static void Matched(Run run, Material material)
        {
            Require(Map(run).TryGetValue(Key(SourceName), out var mapped) && mapped == material && RendererUses(run.model, material), "The exact remap and imported renderer do not agree.");
            var receipt = CurrentReceipt(run, "matched");
            Require(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out string guid, out long local), "The copied Material lost its identity.");
            Require(receipt.material_guid == guid && receipt.material_local_id == local, "The receipt does not describe the verified exact Material.");
            Evidence(run)["matched_receipt"] = JObject.FromObject(receipt);
        }
        static CharacterMaterialMatching.Record CurrentReceipt(Run run, string status)
        {
            var receipt = run.session.Receipt(SourceName);
            Require(receipt != null && receipt.schema == CharacterMaterialMatching.ReceiptSchema && receipt.status == status &&
                receipt.project_root == run.root && receipt.export_asset_id == run.id && receipt.model_path == run.model && receipt.source_material == SourceName &&
                receipt.fbx_sha256 == Hash(Full(run, run.model)) && receipt.manifest_sha256 == Hash(Full(run, run.manifest)), "The receipt does not identify this verified current publication and status.");
            return receipt;
        }
        static void FailedManual(Run run, Material wanted)
        {
            var receipt = CurrentReceipt(run, "failed");
            Require(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(wanted, out string guid, out long local), "The intended fixture Material lost its persistent identity.");
            Require(receipt.explicit_choice && receipt.material_guid == guid && receipt.material_local_id == local && receipt.error.Contains("exact source material remap"), "Failed verification lost the latest manual identity or its mismatch reason.");
            if (Evidence(run)["failed_manual_receipts"] == null) Evidence(run)["failed_manual_receipts"] = new JArray();
            ((JArray)Evidence(run)["failed_manual_receipts"]).Add(JObject.FromObject(receipt));
        }
        static void CheckResult(Run run, CharacterMaterialMatching.Request request, string status)
        {
            var result = run.session.Result(request);
            Require(result != null && result.schema == CharacterMaterialMatching.ResultSchema && result.status == status && result.request_id == request.request_id &&
                result.created_unix == request.created_unix && result.project_root == run.root && result.model_path == run.model &&
                result.export_asset_id == run.id && result.source_material == request.source_material, "The request did not publish its complete expected terminal identity.");
            if (Evidence(run)["results"] == null) Evidence(run)["results"] = new JArray();
            ((JArray)Evidence(run)["results"]).Add(JObject.FromObject(result));
        }
        static AssetImporter.SourceAssetIdentifier Key(string source) => new AssetImporter.SourceAssetIdentifier(typeof(Material), source);
        static Dictionary<AssetImporter.SourceAssetIdentifier, Object> Map(Run run)
        {
            var importer = AssetImporter.GetAtPath(run.model) as ModelImporter;
            Require(importer != null, "The fixture importer is missing.");
            return importer.GetExternalObjectMap();
        }
        static bool SameMap(Dictionary<AssetImporter.SourceAssetIdentifier, Object> first, Dictionary<AssetImporter.SourceAssetIdentifier, Object> second)
            => first.Count == second.Count && first.All(pair => second.TryGetValue(pair.Key, out var value) && value == pair.Value);
        static bool RendererUses(string model, Material material)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(model);
            return asset != null && asset.GetComponentsInChildren<Renderer>(true).Any(renderer => renderer.sharedMaterials.Contains(material));
        }
        static JArray NativeInventory(string model)
        {
            var result = new JArray();
            var serialized = new SerializedObject(AssetImporter.GetAtPath(model));
            var materials = serialized.FindProperty("m_Materials");
            Require(materials != null && materials.isArray, "Unity m_Materials is unavailable.");
            for (int i = 0; i < materials.arraySize; i++)
            {
                var item = materials.GetArrayElementAtIndex(i);
                result.Add(new JObject { ["name"] = item.FindPropertyRelative("name")?.stringValue,
                    ["type"] = item.FindPropertyRelative("type")?.stringValue, ["assembly"] = item.FindPropertyRelative("assembly")?.stringValue });
            }
            return result;
        }
        static List<Stamp> CaptureOriginals(IEnumerable<string> known)
        {
            string[] fixedPaths = { SourceModel, SourceMaterial, Path.ChangeExtension(SourceModel, ".cdesigner.json"),
                "Assets/Art/Character/Cosha/Cosha.Runtime.prefab", "Assets/Prefabs/Characters/Cosha/Cosha.Player.prefab" };
            var paths = new HashSet<string>(fixedPaths.Concat(known), StringComparer.Ordinal);
            foreach (string model in known.Where(value => value.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase))) paths.Add(Path.ChangeExtension(model, ".cdesigner.json"));
            foreach (string path in AssetDatabase.GetDependencies(fixedPaths.Where(File.Exists).ToArray(), true))
                if (path.StartsWith("Assets/", StringComparison.Ordinal) && File.Exists(path)) paths.Add(path);
            foreach (string path in paths.ToArray()) paths.Add(path + ".meta");
            foreach (string path in LoadedScenePaths()) paths.Add(path);
            Require(paths.Count <= 4096, "The protected asset set is too large for this bounded acceptance run.");
            return paths.OrderBy(path => path, StringComparer.Ordinal).Select(Capture).ToList();
        }
        static Stamp Capture(string path)
        {
            var asset = AssetDatabase.LoadMainAssetAtPath(path);
            var importer = AssetImporter.GetAtPath(path);
            return new Stamp { path = path, exists = File.Exists(path), hash = File.Exists(path) ? Hash(path) : "", assetDirty = asset != null && EditorUtility.IsDirty(asset), importerDirty = importer != null && EditorUtility.IsDirty(importer) };
        }
        static bool Unchanged(Stamp before)
        {
            Stamp after = Capture(before.path);
            return before.exists == after.exists && before.hash == after.hash && before.assetDirty == after.assetDirty && before.importerDirty == after.importerDirty;
        }
        static Dictionary<string, string> ReceiptSnapshot(string store, string ownProfile)
        {
            string directory = Path.Combine(store, "receipts");
            if (!Directory.Exists(directory)) return new Dictionary<string, string>(StringComparer.Ordinal);
            string excluded = Path.Combine(directory, ownProfile) + Path.DirectorySeparatorChar;
            string[] paths = Directory.GetFiles(directory, "*.json", SearchOption.AllDirectories).Where(path => !path.StartsWith(excluded, StringComparison.OrdinalIgnoreCase)).ToArray();
            Require(paths.Length <= 8192, "The protected receipt set is too large for this bounded acceptance run.");
            return paths.ToDictionary(path => path, Hash, StringComparer.Ordinal);
        }
        static bool SameSnapshot(Dictionary<string, string> first, Dictionary<string, string> second)
            => first.Count == second.Count && first.All(pair => second.TryGetValue(pair.Key, out string hash) && hash == pair.Value);
        static string RendererIdentity(string model)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(model);
            Require(asset != null, "The protected source model is unavailable.");
            return string.Join("\n", asset.GetComponentsInChildren<Renderer>(true).Select(renderer => ObjectIdentity(renderer) + ":" +
                string.Join(",", renderer.sharedMaterials.Select(material => material == null ? "null" : ObjectIdentity(material) + ":" + AssetDatabase.GetAssetPath(material)))));
        }
        static IEnumerable<string> LoadedScenePaths()
        {
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                string path = SceneManager.GetSceneAt(i).path;
                if (!string.IsNullOrEmpty(path)) yield return path;
            }
        }
        static string SceneState()
        {
            var values = new List<string> { "active=" + SceneManager.GetActiveScene().handle, "count=" + SceneManager.sceneCount,
                "preview=" + EditorSceneManager.previewSceneCount };
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                Scene scene = SceneManager.GetSceneAt(i);
                values.Add(scene.handle + ":" + scene.path + ":" + scene.isLoaded + ":" + scene.isDirty + ":" + DirtyId?.GetValue(scene) + ":" +
                    (scene.isLoaded ? string.Join(",", scene.GetRootGameObjects().Select(ObjectIdentity)) : ""));
            }
            return string.Join("\n", values);
        }
        static string ObjectIdentity(Object value)
        {
#if UNITY_6000_5_OR_NEWER
            return value.GetEntityId().ToString();
#else
            return value.GetInstanceID().ToString();
#endif
        }
        static string Full(Run run, string path) => Path.GetFullPath(Path.Combine(run.root, path));
        static string Hash(string path)
        {
            using (var input = File.OpenRead(path)) using (var digest = SHA256.Create()) return BitConverter.ToString(digest.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
        }
        static void AddError(Run run, string error) { run.report["error"] = (run.report["error"]?.Value<string>() ?? "") + "\n" + error; run.report["passed"] = false; }
        static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
    }
}
