from pathlib import Path
import hashlib,json,subprocess,sys
E=Path(__file__).resolve().parent
R=Path(r"D:\MyRepository\Blender-addons-by-Randy")
read=lambda n:json.loads((E/n).read_text(encoding="utf-8"))
m=read("release_projection_07724.json")
sha=hashlib.sha256((E/"release_projection_07724.json").read_bytes()).hexdigest()
proof=read("isolated_report.json")
assert proof["completed"] and proof["runtime_projection"]["manifest_sha256"]==sha
assert proof["runtime_projection"]["all_file_hashes_match"]
assert proof["runtime"]["blender"]=="5.2.0 LTS"
pure=read("pure_test_receipt.json")
assert pure["passed"] and pure["projection_sha256"]==sha
build=read("release_build_receipt.json")
assert build["projection_sha256"]==sha and build["archive_files_match_projection"]
assert hashlib.sha256(Path(build["archive"]).read_bytes()).hexdigest()==build["archive_sha256"]
for n,h in m["source_provenance"]["canonical_overlays"].items():
 assert hashlib.sha256((R/"addons/character_designer"/n).read_bytes()).hexdigest()==h
args=[sys.executable,"tools/deploy_local.py","--module","character_designer","--blender-version","5.2","--project-addons",r"D:\Blender\Projects\Character\X\addons","--projection",str(E/"release_projection_07724.json")]
report={"projection_sha256":sha,"version":m["version"],"runs":[],"completed":False}
for check in (False,True):
 result=subprocess.run(args+(["--check"] if check else []),cwd=R,capture_output=True,text=True,encoding="utf-8")
 report["runs"].append({"check":check,"exit_code":result.returncode,"stdout":result.stdout,"stderr":result.stderr})
 (E/"release_deployment_receipt.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
 print(result.stdout)
 assert result.returncode==0,result.stderr
report["completed"]=True
(E/"release_deployment_receipt.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
