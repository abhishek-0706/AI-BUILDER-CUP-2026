"""Offline safety checks for Spark-only REST deployment; no Google or model calls."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"gcp"))
import deploy_free as free


def test_static_bundle_excludes_credentials_tooling_and_documentation(tmp_path):
    for name in free.ROOT_FILES:
        (tmp_path/name).write_text("window.RETAILIQ_RUNTIME={backend:false};" if name=="runtime-config.js" else "public")
    (tmp_path/"demo/samples").mkdir(parents=True)
    (tmp_path/"demo/samples/shelf_compliant.jpg").write_bytes(b"reference")
    (tmp_path/"assets").mkdir()
    (tmp_path/"assets/photo.png").write_bytes(b"public-photo")
    (tmp_path/"assets/BRIEF.md").write_text("private documentation")
    (tmp_path/"assets/secret.key").write_text("never publish")
    (tmp_path/".env").write_text("never publish")
    files=free.collect_files(tmp_path)
    assert "/assets/photo.png" in files
    assert not any(p.endswith((".md",".key",".env")) for p in files)
    (tmp_path/"demo.html").write_text("public video player")
    (tmp_path/"demo/RetailIQ_Abhishek_voice_demo.mp4").write_bytes(b"public-final-video")
    (tmp_path/"demo/private-voice.ogg").write_bytes(b"private-sample")
    assert not any(path.endswith((".mp4",".ogg")) for path in free.collect_files(tmp_path))
    with_demo=free.collect_files(tmp_path,include_demo=True)
    assert with_demo["/demo.html"]==b"public video player"
    assert with_demo["/demo/RetailIQ_Abhishek_voice_demo.mp4"]==b"public-final-video"
    assert not any(path.endswith(".ogg") for path in with_demo)
    (tmp_path/"demo/RetailIQ_Abhishek_voice_demo.mp4").write_bytes(b"x"*(free.MAX_DEMO_BYTES+1))
    with pytest.raises(free.DeploymentError,match="bounded free-deployment limit"):free.collect_files(tmp_path,include_demo=True)
    (tmp_path/"runtime-config.js").write_text("window.RETAILIQ_RUNTIME={backend:true};")
    with pytest.raises(free.DeploymentError,match="backend:false"):free.collect_files(tmp_path)


@pytest.mark.parametrize("billing",[{"billingEnabled":True},{}])
def test_enabled_or_unknown_billing_stops_before_any_cloud_mutation(monkeypatch,billing):
    deploy=free.SparkDeployment("retailiq-free-test",free.DEFAULT_ACCOUNT,"gcloud")
    calls=[]
    def cli(*arguments):calls.append(arguments);return json.dumps(billing)
    monkeypatch.setattr(deploy,"cli",cli)
    monkeypatch.setattr(deploy,"request",lambda *a,**k:pytest.fail("Billing guard must stop before REST calls"))
    with pytest.raises(free.DeploymentError,match="refusing free-only"):deploy.deploy({"/index.html":b"public"})
    assert len(calls)==1 and calls[0][:3]==("billing","projects","describe")


def test_rest_flow_uses_gzip_hashes_and_rechecks_unbilled_before_release(monkeypatch):
    deploy=free.SparkDeployment("retailiq-free-test",free.DEFAULT_ACCOUNT,"gcloud")
    cli_calls=[];requests=[]
    def cli(*arguments):
        cli_calls.append(arguments)
        return '{"billingEnabled":false}' if arguments[0]=="billing" else ""
    files={"/index.html":b"public"};manifest,blobs=free.compressed_files(files)
    digest=manifest["/index.html"]
    version="sites/retailiq-free-test/versions/v123"
    def request(method,url,body=None,**kwargs):
        requests.append((method,url,body,kwargs))
        if method=="GET" and url.startswith(free.MANAGEMENT):return {"projectId":"retailiq-free-test"}
        if method=="GET":return {"sites":[{"type":"DEFAULT_SITE","name":"projects/retailiq-free-test/sites/retailiq-free-test"}]}
        if url.endswith("/versions"):return {"name":version}
        if url.endswith(":populateFiles"):
            assert body=={"files":manifest}
            return {"uploadRequiredHashes":[digest],"uploadUrl":"https://upload-firebasehosting.googleapis.com/upload/"+version+"/files"}
        if "upload-firebasehosting" in url:
            assert kwargs["binary"] and hashlib.sha256(body).hexdigest()==digest and gzip.decompress(body)==b"public"
            return {}
        if method=="PATCH":return {"status":"FINALIZED"}
        if "/releases?" in url:return {"type":"DEPLOY"}
        pytest.fail("Unexpected REST call")
    monkeypatch.setattr(deploy,"cli",cli);monkeypatch.setattr(deploy,"request",request)
    assert deploy.deploy(files)=="https://retailiq-free-test.web.app"
    assert len([c for c in cli_calls if c[0]=="billing"])==4
    enabled=next(c for c in cli_calls if c[:2]==("services","enable"))
    assert enabled[2:4]==("firebase.googleapis.com","firebasehosting.googleapis.com")
    assert not any("run" in c or "builds" in c for c in cli_calls)


def test_oauth_is_not_sent_to_untrusted_destinations(monkeypatch):
    deploy=free.SparkDeployment("retailiq-free-test",free.DEFAULT_ACCOUNT,"gcloud")
    monkeypatch.setattr(deploy,"cli",lambda *a:pytest.fail("Untrusted destination must be rejected before obtaining a token"))
    with pytest.raises(free.DeploymentError,match="unexpected Firebase API destination"):
        deploy.request("POST","https://not-google.example/upload",{})
    captured=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def read(self,size):return b"{}"
    class Opener:
        def open(self,request,timeout):captured.append(request);return Response()
    monkeypatch.setattr(deploy,"_opener",Opener())
    monkeypatch.setattr(deploy,"cli",lambda *a:"OFFLINE-TEST-TOKEN")
    deploy.request("GET",free.MANAGEMENT+"/projects/"+deploy.project)
    deploy.request("POST","https://upload-firebasehosting.googleapis.com/upload/sites/test/versions/v1/files/hash",b"offline-data",binary=True)
    assert len(captured)==2
    for request in captured:
        headers={key.lower():value for key,value in request.header_items()}
        assert headers["x-goog-user-project"]=="retailiq-free-test"
