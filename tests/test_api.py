"""Regression checks use in-memory cloud doubles; no credentials or billed calls."""
import base64
import datetime as dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"gcp"))
import main as api
from fixtures import load_fixture
from seed_data import generate


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api,"API_KEY","test-access")
    monkeypatch.setattr(api,"PROJECT","test-project")
    monkeypatch.setattr(api,"LOG_API_KEY","")
    api._AI_WINDOWS.clear()
    with TestClient(api.app,headers={"Authorization":"Bearer test-access"}) as c:
        yield c


def test_api_requires_access_and_disables_unconfigured_mode(client,monkeypatch):
    assert client.get("/api/products",headers={"Authorization":"Bearer wrong"}).status_code==401
    monkeypatch.setattr(api,"API_KEY","")
    monkeypatch.setattr(api,"TRUST_IAM",False)
    monkeypatch.setattr(api,"DEMO_OPEN_LOGS",False)
    assert client.post("/api/chat",json={"message":"hi"}).status_code==503
    assert client.get("/runtime-config.js").status_code==200


def test_log_route_is_not_intercepted_by_visit_id(client,monkeypatch):
    class Events:
        def collection(self,*args):return self
        def where(self,*args,**kwargs):return self
        def order_by(self,*args,**kwargs):return self
        def limit(self,*args):return self
        def stream(self):return []
    monkeypatch.setattr(api,"firestore_client",lambda:Events())
    monkeypatch.setattr(api,"run_query",lambda *a,**k:pytest.fail("Dynamic visit route intercepted log"))
    assert client.get("/api/visits/log").json()["events"]==[]


def test_logging_persists_required_ids_and_metadata(client,monkeypatch):
    saved=[]
    class DB:
        id="test-doc"
        def collection(self,*args):return self
        def document(self):return self
        def set(self,data):saved.append(data)
    monkeypatch.setattr(api,"firestore_client",lambda:DB())
    event={"visit_id":"V-00118","store_id":"BLR-KOR-014","rep_id":"TSE-4417", "event_type":"capture",
           "summary":"No shake facings", "metadata":{"capture":{"R01":{"onShelf":0}}}}
    assert client.post("/api/visits/log",json=event).json()["status"]=="logged"
    assert saved[0]["store_id"]==event["store_id"] and saved[0]["metadata"]==event["metadata"]
    monkeypatch.setattr(api,"firestore_client",lambda:None)
    assert client.post("/api/visits/log",json=event).status_code==503
    del event["rep_id"]
    assert client.post("/api/visits/log",json=event).status_code==422


def test_multiple_images_reach_model_and_sources_are_bounded():
    image={"mime_type":"image/jpeg","data":base64.b64encode(b"test image").decode()}
    req=api.ChatRequest(message="Audit",images=[image]*6)
    assert len(api._build_contents(req)[-1].parts)==7
    with pytest.raises(ValueError):api.ChatRequest(message="Audit",images=[image]*7)
    with pytest.raises(ValueError):api.ChatRequest(message="Audit",image=image,images=[image])
    with pytest.raises(ValueError):api.ChatImage(mime_type="text/html",data="abc")
    with pytest.raises(ValueError):api.ChatImage(mime_type="image/jpeg",gcs_uri="gs://another-bucket/private")


def pitch_model(monkeypatch,output,seen):
    def model(**kwargs):
        seen.append(kwargs["contents"][0].parts[0].text)
        return SimpleNamespace(text=json.dumps(output))
    monkeypatch.setattr(api,"genai_client",lambda:SimpleNamespace(models=SimpleNamespace(generate_content=model)))
    monkeypatch.setattr(api,"run_query",lambda *a,**k:[{"doc_id":"KB-108","fact":"Protiva carries 20g protein."}])


def test_pitch_contains_exact_retrieved_facts(client,monkeypatch):
    seen=[]
    output={"opening_style":"category","claim_doc_ids":["KB-108"],"close_style":"trial"}
    pitch_model(monkeypatch,output,seen)
    response=client.post("/api/agent/pitch-brief",json={"buyer_category":"protein","buyer_context":"Small trial with shrink review"})
    assert response.status_code==200,response.text
    assert "Protiva carries 20g protein." in seen[0]
    result=response.json()
    assert result["sources"]==["KB-108"]
    assert result["key_claims"]==["Protiva carries 20g protein. [KB-108]"]
    assert result["evidence"][0]["fact"]=="Protiva carries 20g protein."
    assert result["validation"]["claims_rewritten_by_model"] is False
    assert result["validation"]["source_truth_verified"] is False


@pytest.mark.parametrize("changes",[
    {"claim_doc_ids":["KB-99999"]},
    {"claim_doc_ids":[]},
    {"claim_doc_ids":[123]},
    {"claim_doc_ids":None},
    {"opening_style":"Invented 99% sales uplift"},
    {"key_claims":["Fake sales uplift [KB-108]"]},
    {"close_style":"invented guarantee"},
])
def test_pitch_rejects_invalid_citations_and_invented_prose(client,monkeypatch,changes):
    output={"opening_style":"category","claim_doc_ids":["KB-108"],"close_style":"review"}
    output.update(changes);pitch_model(monkeypatch,output,[])
    assert client.post("/api/agent/pitch-brief",json={"buyer_category":"protein"}).status_code==502


def test_pitch_empty_retrieval_never_calls_model(client,monkeypatch):
    monkeypatch.setattr(api,"run_query",lambda *a,**k:[])
    monkeypatch.setattr(api,"genai_client",lambda:pytest.fail("No evidence must stop inference"))
    assert client.post("/api/agent/pitch-brief",json={"buyer_category":"unsupported"}).status_code==404


def test_ai_rate_limit_stops_billed_work(client,monkeypatch):
    monkeypatch.setattr(api,"AI_REQUESTS_PER_MINUTE",1)
    monkeypatch.setattr(api,"genai_client",lambda: (_ for _ in ()).throw(api.HTTPException(503,"test unavailable")))
    assert client.post("/api/chat",json={"message":"hi"}).status_code==503
    response=client.post("/api/chat",json={"message":"hi"})
    assert response.status_code==429 and response.headers["retry-after"]=="60"


def test_bootstrap_uses_warehouse_inventory_and_never_falls_back(client,monkeypatch):
    d=load_fixture();products=d["products"]
    products[0]["price"]=991;products[0]["stock"]=0
    def query(name,**kwargs):
        return {"product_catalog":products,"revenue_week":d["revenueWeek"],"forecast_read":d["forecast"],
            "kpi_rollup":[{"revenue_target":420000,"conversion_rate":.68,"return_customer_pct":.72,"nps":61,"total_skus":13}],
            "segment_stats":[],"bootstrap_promotions":[],"knowledge_docs":d["kbDocs"],"reorder_alerts":[]}[name]
    monkeypatch.setattr(api,"run_query",query)
    response=client.get("/api/bootstrap");assert response.status_code==200,response.text
    assert response.json()["products"][0]["price"]==991 and response.json()["products"][0]["stock"]==0
    assert response.json()["source"]=="bigquery"
    monkeypatch.setattr(api,"run_query",lambda *a,**k: (_ for _ in ()).throw(api.HTTPException(503,"warehouse down")))
    assert client.get("/api/bootstrap").status_code==503


def test_seed_data_reconciles_with_browser_fixture(tmp_path):
    d=load_fixture();day=dt.date.fromisoformat(d["asOfDate"])
    generate(day,30,tmp_path)
    read=lambda name:[json.loads(line) for line in (tmp_path/(name+".ndjson")).read_text(encoding="utf-8").splitlines()]
    products={p["product_id"]:p for p in read("products")}
    for p in d["products"]:
        assert products[p["id"]]["product_name"]==p["name"]
        assert products[p["id"]]["protein_grams"]==p["protein"]
    totals=defaultdict(int);baskets=defaultdict(set);units=Counter()
    for row in read("sales_transactions"):
        totals[row["txn_date"]]+=round(row["line_revenue"]*100)
        baskets[row["txn_date"]].add(row["transaction_id"])
        units[row["product_id"]]+=row["quantity"]
        assert round(row["unit_price"]*row["quantity"]-row["discount_amount"],2)==row["line_revenue"]
    for age in range(7):
        key=str(day-dt.timedelta(days=age));expected=d["revenueWeek"][6-age]
        assert totals[key]==expected["revenue"]*100
        assert len(baskets[key])==expected["transactions"]
    for p in d["products"]:assert units[p["id"]]==p["unitsSoldLast30d"]
    assert {r["doc_id"]:r["fact"] for r in read("kb_documents")}=={r["id"]:r["fact"] for r in d["kbDocs"]}
    assert read("visits")[0]["objective"]==d["visits"][0]["objective"]


@pytest.mark.parametrize("fields,expected,basis",[
    ({"unitsSoldLast30d":88,"stock":7,"shelfLifeDays":4},5,"30-day sales average"),
    ({"unitsSoldLast30d":300,"stock":7,"shelfLifeDays":4,"predictedUnitsPerDay":2},1,"forecast"),
    ({"unitsSoldLast30d":300,"stock":7,"predictedUnitsPerDay":0},0,"forecast"),
    ({"unitsSoldLast30d":300,"stock":10,"unitsOnOrder":12,"caseSize":12},192,"30-day sales average"),
    ({"unitsSoldLast30d":300,"stock":10,"unitsOnOrder":500},0,"30-day sales average"),
    ({"unitsSoldLast30d":300,"stock":0,"shelfLifeDays":4,"caseSize":24},40,"30-day sales average"),
])
def test_replenishment_caps_shrink_and_nets_inbound(fields,expected,basis):
    result=api.replenishment(fields)
    assert result["recommendedOrderUnits"]==expected
    assert result["recommendationBasis"]==basis
    if fields.get("shelfLifeDays",99)<21:assert result["caseSize"]==1


def test_products_and_replenishment_share_one_calculation(client,monkeypatch):
    rows=[{"id":"salad","ours":True,"unitsSoldLast30d":88,"stock":7,"shelfLifeDays":4},
          {"id":"other","ours":False,"unitsSoldLast30d":300,"stock":0}]
    monkeypatch.setattr(api,"run_query",lambda *a,**k:rows)
    product=client.get("/api/products").json()["rows"][0]
    order=client.get("/api/replenishment").json()["rows"]
    assert len(order)==1 and product["recommendedOrderUnits"]==order[0]["recommendedOrderUnits"]==5


def test_application_bearer_also_authorizes_logs_when_legacy_key_set(client,monkeypatch):
    monkeypatch.setattr(api,"LOG_API_KEY","obsolete-different-key")
    monkeypatch.setattr(api,"firestore_client",lambda:None)
    # 503 is the known unconfigured storage response, rather than a second-key 401.
    response=client.get("/api/visits/log")
    assert response.status_code==503 and response.json()["detail"]=="Firestore is not configured"
    assert client.get("/api/visits/log",headers={"Authorization":"Bearer wrong","X-Log-Key":"obsolete-different-key"}).status_code==401


def test_visit_write_failure_and_metadata_bounds_are_honest(client,monkeypatch):
    class BrokenDB:
        def collection(self,*a):raise RuntimeError("credentials unavailable")
    monkeypatch.setattr(api,"firestore_client",lambda:BrokenDB())
    event={"visit_id":"V1","store_id":"S1","rep_id":"R1","event_type":"audit","score":87,
           "metadata":{"score_basis":"visible rules","visible_rules":7,"total_rules":8}}
    assert client.post("/api/visits/log",json=event).status_code==503
    event["metadata"]={"oversized":"a"*25000}
    assert client.post("/api/visits/log",json=event).status_code==422


def evidence_body(raw=b"\xff\xd8\xff\xe0test-jpeg"):
    return {"visit_id":"V-00118","store_id":"BLR-KOR-014","rep_id":"TSE-4417",
            "image":{"mime_type":"image/jpeg","data":base64.b64encode(raw).decode()}}


def test_evidence_is_private_bounded_and_hashed(client,monkeypatch):
    uploads=[]
    class Blob:
        def upload_from_string(self,raw,**kwargs):uploads.append((self,raw,kwargs))
    class Storage:
        def bucket(self,name):assert name=="private-evidence";return self
        def blob(self,name):self.object_name=name;return Blob()
    store=Storage()
    monkeypatch.setattr(api,"PHOTO_BUCKET","private-evidence")
    monkeypatch.setattr(api,"storage_client",lambda:store)
    response=client.post("/api/evidence",json=evidence_body())
    assert response.status_code==200,response.text
    result=response.json()
    assert result["gcs_uri"].startswith("gs://private-evidence/shelf-evidence/")
    assert len(result["sha256"])==64 and result["expires_after_days"]==30
    blob,raw,options=uploads[0]
    assert blob.cache_control=="private, no-store"
    assert blob.metadata["visit_id"]=="V-00118" and options["if_generation_match"]==0
    assert "public" not in options and result["bytes"]==len(raw)
    assert client.post("/api/evidence",json=evidence_body(b"<svg onload=alert(1)>")).status_code==400
    assert client.post("/api/evidence",json={**evidence_body(),"visit_id":"../escape"}).status_code==422
    monkeypatch.setattr(api,"PHOTO_BUCKET","")
    assert client.post("/api/evidence",json=evidence_body()).status_code==503


def test_evidence_storage_failure_does_not_report_saved(client,monkeypatch):
    monkeypatch.setattr(api,"PHOTO_BUCKET","private-evidence")
    monkeypatch.setattr(api,"storage_client",lambda:(_ for _ in ()).throw(RuntimeError("unavailable")))
    assert client.post("/api/evidence",json=evidence_body()).status_code==503


def test_forecast_migration_and_materialization_are_column_explicit():
    root=Path(__file__).resolve().parents[1]
    schema=(root/"gcp/schema.sql").read_text(encoding="utf-8")
    forecast=(root/"gcp/forecast.sql").read_text(encoding="utf-8")
    for field in ["day_label","model_name"]:
        assert f"ADD COLUMN IF NOT EXISTS {field} STRING" in schema
        assert f"ADD COLUMN IF NOT EXISTS {field} STRING" in forecast
    import re
    match=re.search(r"INSERT INTO `[^`]*demand_forecast_daily`\s*\((.*?)\)\s*SELECT",forecast,re.S)
    assert match and len(match[1].split(","))==9
    assert "case_size INT64" in schema


def test_deployment_is_private_by_default_and_provisions_required_storage():
    root=Path(__file__).resolve().parents[1]
    deploy=(root/"gcp/deploy.sh").read_text(encoding="utf-8")
    assert 'PUBLIC_DEMO="${PUBLIC_DEMO:-false}"' in deploy
    assert 'access=(--no-allow-unauthenticated)' in deploy
    assert 'RETAILIQ_OPEN_DEMO="false"' in deploy
    assert 'PUBLIC_DEMO requires APP_KEY_FILE' in deploy
    assert 'create_firestore' in deploy and "indexes composite create" in deploy
    assert '--public-access-prevention' in deploy and '--lifecycle-file=' in deploy
    assert 'roles/storage.objectAdmin' not in deploy
    indexes=json.loads((root/"gcp/firestore.indexes.json").read_text(encoding="utf-8"))
    assert indexes["indexes"][0]["fields"][1]=={"fieldPath":"created_at","order":"DESCENDING"}
    assert 'PYTHON_BIN="${PYTHON_BIN:-python3}"' in deploy


def test_top_movers_omit_untracked_aggregate_and_sql_policy_agrees():
    query=api.sql_for("top_movers")
    assert "p.is_active AND p.is_tracked" in query
    alerts=api.sql_for("reorder_alerts")
    assert "p.is_ours" in alerts and "p.shelf_life_days" in alerts and "p.case_size" in alerts
    assert "units_on_hand-units_on_order" in alerts


def test_visit_agent_no_alerts_avoids_billed_generation(client,monkeypatch):
    monkeypatch.setattr(api,"run_query",lambda *a,**k:[])
    monkeypatch.setattr(api,"genai_client",lambda:SimpleNamespace())
    response=client.post("/api/agent/visit-plan",json={})
    assert response.status_code==200 and response.json()["steps_taken"]==1


@pytest.mark.parametrize("checklist",[None,[],[{"task":"Invented action","priority":"guaranteed"}],"fake"])
def test_visit_agent_rejects_invalid_checklist(client,monkeypatch,checklist):
    outputs=iter([SimpleNamespace(text="Check shelf stock."),SimpleNamespace(text=json.dumps({"checklist":checklist}))])
    monkeypatch.setattr(api,"run_query",lambda *a,**k:[{"product":"Salad","recommended_order_units":5}])
    monkeypatch.setattr(api,"genai_client",lambda:SimpleNamespace(models=SimpleNamespace(generate_content=lambda **k:next(outputs))))
    assert client.post("/api/agent/visit-plan",json={}).status_code==502


def test_manager_read_failure_is_explicit(client,monkeypatch):
    class BrokenDB:
        def collection(self,*a):raise RuntimeError("index not ready")
    monkeypatch.setattr(api,"firestore_client",lambda:BrokenDB())
    response=client.get("/api/visits/log")
    assert response.status_code==503 and "composite index" in response.json()["detail"]


def test_guided_reference_image_is_available_in_local_api_and_container(client):
    response=client.get("/demo/samples/shelf_compliant.jpg")
    assert response.status_code==200 and response.headers["content-type"]=="image/jpeg"
    assert response.content.startswith(b"\xff\xd8\xff")
    root=Path(__file__).resolve().parents[1]
    assert "COPY demo/samples/shelf_compliant.jpg ./static/demo/samples/shelf_compliant.jpg" in (root/"Dockerfile").read_text()
    assert client.get("/demo/tooling/script.json").status_code==404


@pytest.fixture
def retained_photo(monkeypatch):
    downloads=[]
    class Blob:
        size=15
        generation=7
        content_type="image/jpeg"
        raw=b"\xff\xd8\xff\xe0retained-jpeg"
        def reload(self,**kwargs):pass
        def download_as_bytes(self,**kwargs):downloads.append(kwargs);return self.raw
    class Storage:
        def bucket(self,name):assert name=="private-evidence";return self
        def blob(self,name):return blob
    blob=Blob()
    monkeypatch.setattr(api,"PHOTO_BUCKET","private-evidence")
    monkeypatch.setattr(api,"storage_client",lambda:Storage())
    return blob,downloads,"gs://private-evidence/shelf-evidence/2026/10/18/BLR-KOR-014/"+"a"*32+".jpg"


def test_manager_views_private_photo_with_bounded_generation_read(client,retained_photo):
    blob,downloads,uri=retained_photo
    response=client.get("/api/evidence/image",params={"gcs_uri":uri})
    assert response.status_code==200 and response.content==blob.raw
    assert response.headers["content-type"]=="image/jpeg"
    assert response.headers["cache-control"]=="private, no-store"
    assert response.headers["x-content-type-options"]=="nosniff"
    assert downloads==[{"start":0,"end":api.MAX_IMAGE_BYTES,"if_generation_match":7,"timeout":30}]
    assert client.get("/api/evidence/image",params={"gcs_uri":uri},headers={"Authorization":"Bearer wrong"}).status_code==401


@pytest.mark.parametrize("uri",[
    "gs://other-bucket/shelf-evidence/2026/10/18/S1/"+"a"*32+".jpg",
    "gs://private-evidence/private-other-data.jpg",
    "gs://private-evidence/shelf-evidence/2026/10/18/../"+"a"*32+".jpg",
    "https://storage.googleapis.com/private-evidence/photo.jpg",
])
def test_private_photo_rejects_other_bucket_and_unowned_paths(client,retained_photo,uri):
    assert client.get("/api/evidence/image",params={"gcs_uri":uri}).status_code==400


def test_private_photo_enforces_metadata_download_and_mime_bounds(client,retained_photo):
    blob,downloads,uri=retained_photo
    blob.size=api.MAX_IMAGE_BYTES+1
    assert client.get("/api/evidence/image",params={"gcs_uri":uri}).status_code==413
    assert not downloads
    blob.size=15;blob.content_type="text/html"
    assert client.get("/api/evidence/image",params={"gcs_uri":uri}).status_code==415
    blob.content_type="image/jpeg";blob.raw=b"a"*(api.MAX_IMAGE_BYTES+1)
    assert client.get("/api/evidence/image",params={"gcs_uri":uri}).status_code==413
    blob.raw=b"<html>not an image</html>"
    assert client.get("/api/evidence/image",params={"gcs_uri":uri}).status_code==400


def test_private_photo_reports_missing_expired_object(client,retained_photo,monkeypatch):
    from google.api_core.exceptions import NotFound
    blob,_,uri=retained_photo
    monkeypatch.setattr(blob,"reload",lambda **k:(_ for _ in ()).throw(NotFound("expired")))
    response=client.get("/api/evidence/image",params={"gcs_uri":uri})
    assert response.status_code==404 and "expired" in response.json()["detail"]


def test_public_health_alias_matches_original_handler(client):
    response=client.get("/health",headers={"Authorization":""})
    original=client.get("/healthz",headers={"Authorization":""})
    assert response.status_code==200 and response.json()["status"]=="ok"
    assert response.json()==original.json()



def test_chat_forwards_optional_type_schema_to_gemini_json_config(client,monkeypatch):
    seen=[]
    def generate(**kwargs):
        seen.append(kwargs["config"])
        return iter([SimpleNamespace(text='{"available":true,"reason":"visible"}')])
    monkeypatch.setattr(api,"genai_client",lambda:SimpleNamespace(models=SimpleNamespace(generate_content_stream=generate)))
    schema={"type":"object","properties":{"available":{"type":"boolean"},"reason":{"type":"string"}},
            "required":["available","reason"]}
    response=client.post("/api/chat",json={"message":"Describe availability","response_schema":schema})
    assert response.status_code==200
    envelope=json.loads(response.text.split("\n")[0].removeprefix("data: "))
    assert json.loads(envelope["candidates"][0]["content"]["parts"][0]["text"])=={"available":True,"reason":"visible"}
    assert seen[0].response_mime_type=="application/json"
    assert seen[0].response_json_schema==schema
    response=client.post("/api/chat",json={"message":"Ordinary plain text"})
    assert response.status_code==200
    assert seen[1].response_mime_type is None and seen[1].response_json_schema is None


def test_chat_rejects_oversized_response_schema_before_model_call(client,monkeypatch):
    monkeypatch.setattr(api,"genai_client",lambda:pytest.fail("Invalid schema must not reach Gemini"))
    response=client.post("/api/chat",json={"message":"test","response_schema":{"type":"object","description":"x"*17000}})
    assert response.status_code==422 and "16KB" in response.text


@pytest.mark.parametrize("model,expected",[("gemini-3.6-flash",None),("gemini-3.5-flash-lite",0.2)])
def test_chat_sampling_is_omitted_only_for_3_6(client,monkeypatch,model,expected):
    seen=[]
    def generate(**kwargs):
        seen.append(kwargs["config"])
        return iter([SimpleNamespace(text="Response")])
    monkeypatch.setattr(api,"GEMINI_MODEL",model)
    monkeypatch.setattr(api,"genai_client",lambda:SimpleNamespace(models=SimpleNamespace(generate_content_stream=generate)))
    response=client.post("/api/chat",json={"message":"Hello","temperature":0.2,"max_output_tokens":4096})
    assert response.status_code==200
    assert seen[0].temperature==expected and seen[0].max_output_tokens==4096
    assert seen[0].thinking_config is None


def test_agent_generation_allows_reasoning_tokens_and_default_sampling(monkeypatch):
    from google.genai import types
    seen=[]
    def generate(**kwargs):seen.append(kwargs["config"]);return SimpleNamespace(text="A plan")
    monkeypatch.setattr(api,"GEMINI_MODEL","gemini-3.6-flash")
    client=SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    assert api.generate_text(client,prompt="Plan",config=types.GenerateContentConfig(temperature=0.3,max_output_tokens=512))=="A plan"
    assert seen[0].temperature is None and seen[0].max_output_tokens==4096


def test_pitch_agent_uses_reasoning_output_budget(client,monkeypatch):
    seen=[]
    def generate(**kwargs):
        seen.append(kwargs["config"])
        return SimpleNamespace(text=json.dumps({"opening_style":"category","claim_doc_ids":["KB-108"],"close_style":"review"}))
    monkeypatch.setattr(api,"GEMINI_MODEL","gemini-3.6-flash")
    monkeypatch.setattr(api,"genai_client",lambda:SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    monkeypatch.setattr(api,"run_query",lambda *a,**k:[{"doc_id":"KB-108","fact":"Protiva carries 20g protein."}])
    response=client.post("/api/agent/pitch-brief",json={"buyer_category":"protein"})
    assert response.status_code==200
    assert seen[0].max_output_tokens==4096 and seen[0].temperature is None


class MemoryJudgeFirestore:
    """Atomic-operation double; each document path has its own persisted value."""
    def __init__(self):self.docs={};self.next_id=0;self.read_limits=[]
    def collection(self,name):return self.Ref(self,(name,))
    def transaction(self):return self.Transaction(self)
    class Transaction:
        def __init__(self,db):self.db=db
        def set(self,ref,data,merge=False):ref.set(data,merge=merge)
    class Ref:
        def __init__(self,db,path):self.db=db;self.path=path;self.filters=[];self.read_limit=20
        def collection(self,name):return self.__class__(self.db,self.path+(name,))
        def document(self,name=None):
            if name is None:self.db.next_id+=1;name='doc-'+str(self.db.next_id)
            ref=self.__class__(self.db,self.path+(name,));ref.id=name;return ref
        def get(self,transaction=None):return SimpleNamespace(to_dict=lambda:dict(self.db.docs.get(self.path,{})))
        def set(self,data,merge=False):
            from google.cloud import firestore
            resolved={key:(dt.datetime.now(dt.timezone.utc) if value is firestore.SERVER_TIMESTAMP else value) for key,value in data.items()}
            self.db.docs[self.path]={**(self.db.docs.get(self.path,{}) if merge else {}),**resolved}
        def where(self,filter):self.filters.append(filter);return self
        def order_by(self,*args,**kwargs):return self
        def limit(self,n):self.read_limit=n;self.db.read_limits.append(n);return self
        def stream(self):
            rows=[]
            for path,data in self.db.docs.items():
                if path[:-1]==self.path and all(data.get(f.field_path)==f.value for f in self.filters):
                    rows.append(SimpleNamespace(id=path[-1],to_dict=lambda data=data:dict(data)))
            return rows[:self.read_limit]


@pytest.fixture
def public_profile(monkeypatch):
    from google.cloud import firestore
    for key,value in {'API_KEY':'','TRUST_IAM':False,'DEMO_OPEN_LOGS':False,'PROJECT':'offline-public-project',
        'PUBLIC_JUDGE':True,'DATA_SOURCE':'synthetic','AI_PROVIDER':'gemini_free','FREE_TIER_CONFIRMED':True,
        'GEMINI_FREE_PROJECT_ID':'offline-free-ai-project','GEMINI_MODEL':'gemini-3.5-flash-lite','JUDGE_SESSION_SECRET':'s'*64,'PHOTO_BUCKET':'',
        'AI_DAILY_REQUEST_LIMIT':50,'JUDGE_DAILY_REQUEST_LIMIT':500,'JUDGE_DAILY_VISIT_LIMIT':200,
        'AI_REQUESTS_PER_MINUTE':6,'DEMO_AS_OF_DATE':'2026-10-22','_FREE_PROVIDER_EXHAUSTED_DAY':''}.items():monkeypatch.setattr(api,key,value)
    monkeypatch.setenv('GEMINI_API_KEY','offline-attested-key')
    monkeypatch.setattr(firestore,'transactional',lambda function:function)
    db=MemoryJudgeFirestore();monkeypatch.setattr(api,'firestore_client',lambda:db)
    api._AI_WINDOWS.clear();api._PUBLIC_BLOCKED.clear()
    yield db
    api._AI_WINDOWS.clear();api._PUBLIC_BLOCKED.clear()


def test_public_profile_truthful_and_bootstrap_never_queries_bigquery(public_profile,monkeypatch):
    monkeypatch.setattr(api,'bq_client',lambda:pytest.fail('Explicit synthetic mode must not access BigQuery'))
    with TestClient(api.app,base_url='https://testserver') as c:
        config=c.get('/api/config').json()
        assert config['provider']=='gemini_free' and config['data_source']=='synthetic_fixture'
        assert config['auth_mode']=='anonymous_synthetic_session' and not config['evidence_enabled']
        runtime=c.get('/runtime-config.js').text
        assert '"token_required": false' in runtime and '"model": "gemini-3.5-flash-lite"' in runtime
        response=c.get('/api/bootstrap')
        assert response.status_code==200,response.text
        assert response.json()['source']=='synthetic_fixture' and response.json()['dataIsSynthetic']
        assert len(response.json()['products'])==len(load_fixture()['products'])
        assert response.headers['cache-control']=='private, no-store'
        assert c.get('/health').json()['provider']=='gemini_free'


@pytest.mark.parametrize('changes',[{'DATA_SOURCE':'bigquery'},{'AI_PROVIDER':'vertex'},{'FREE_TIER_CONFIRMED':False},
    {'JUDGE_SESSION_SECRET':'short'},{'GEMINI_MODEL':'gemini-3.6-flash'}])
def test_public_access_fails_closed_on_inconsistent_profile(public_profile,monkeypatch,changes):
    for key,value in changes.items():monkeypatch.setattr(api,key,value)
    monkeypatch.setattr(api,'genai_client',lambda:pytest.fail('Misconfigured profile must not call a model'))
    with TestClient(api.app,base_url='https://testserver') as c:
        assert c.get('/api/bootstrap').status_code==503
    assert public_profile.docs=={}


def test_public_judges_save_real_namespaced_events_and_cannot_read_another_session(public_profile):
    f=load_fixture();event={'visit_id':f['visits'][0]['id'],'store_id':f['visits'][0]['storeId'],
        'rep_id':f['rep']['employeeId'],'event_type':'audit','summary':'Synthetic shelf check','score':80,
        'metadata':{'audit':{'criteria':[{'rule_id':'P1','status':'PASS'}]}}}
    with TestClient(api.app,base_url='https://testserver') as first, TestClient(api.app,base_url='https://testserver') as second:
        saved=first.post('/api/visits/log',json=event)
        assert saved.status_code==200,saved.text
        assert 'HttpOnly' in saved.headers['set-cookie'] and 'Secure' in saved.headers['set-cookie']
        assert first.get('/api/visits/log?limit=200').json()['count']==1
        assert public_profile.read_limits[-1]==20
        assert second.get('/api/visits/log').json()['events']==[]
        first.cookies.set('__session','tampered.signature')
        assert first.get('/api/visits/log').json()['events']==[]
    paths=[path for path in public_profile.docs if path[0]=='judge_sessions']
    assert len(paths)==1 and paths[0][2]=='visit_events'


def test_public_logs_reject_non_demo_identifiers_and_photo_storage(public_profile):
    with TestClient(api.app,base_url='https://testserver') as c:
        response=c.post('/api/visits/log',json={'visit_id':'private-client','store_id':'other-store',
            'rep_id':'outside-rep','event_type':'audit'})
        assert response.status_code==422
        assert c.get('/api/evidence/image?gcs_uri=gs://anything/private').status_code==404
    assert not any(path[0]=='judge_sessions' for path in public_profile.docs)


def test_persisted_public_allowance_is_atomic_shared_and_stops_work(public_profile,monkeypatch):
    monkeypatch.setattr(api,'AI_DAILY_REQUEST_LIMIT',1)
    api.reserve_public_budget(ai_calls=1)
    with pytest.raises(api.HTTPException) as error:api.reserve_public_budget(ai_calls=1)
    assert error.value.status_code==429
    stored=next(iter(public_profile.docs.values()))
    assert stored['ai_calls']==1 and stored['requests']==1
    api._PUBLIC_BLOCKED.clear()  # Simulate a new instance; the persisted limit must still hold.
    with pytest.raises(api.HTTPException):api.reserve_public_budget(ai_calls=1)
    assert next(iter(public_profile.docs.values()))['ai_calls']==1


def test_quota_store_failure_blocks_model_before_inference(public_profile,monkeypatch):
    monkeypatch.setattr(api,'firestore_client',lambda:(_ for _ in ()).throw(RuntimeError('offline datastore outage')))
    monkeypatch.setattr(api,'genai_client',lambda:pytest.fail('A quota failure must stop inference'))
    with TestClient(api.app,base_url='https://testserver') as c:
        assert c.post('/api/chat',json={'message':'Hi'}).status_code==503


def test_free_provider_initialization_never_falls_back_and_disables_retries(public_profile,monkeypatch):
    from google import genai
    original=api.genai_client;original.cache_clear();seen=[]
    monkeypatch.setattr(genai,'Client',lambda **kwargs:seen.append(kwargs) or object())
    try:
        original()
        assert seen[0]['api_key']=='offline-attested-key' and 'vertexai' not in seen[0]
        assert seen[0]['http_options'].retry_options.attempts==1
        original.cache_clear();monkeypatch.delenv('GEMINI_API_KEY')
        with pytest.raises(api.HTTPException) as error:original()
        assert error.value.status_code==503 and len(seen)==1
    finally:original.cache_clear()


def test_provider_quota_error_persists_daily_stop_without_paid_fallback(public_profile):
    class QuotaError(Exception):code=429
    assert api.stop_free_provider(QuotaError()) is True
    assert next(iter(public_profile.docs.values()))['provider_exhausted'] is True
    with pytest.raises(api.HTTPException) as error:api.ensure_free_provider_open()
    assert error.value.status_code==429
    api._FREE_PROVIDER_EXHAUSTED_DAY=''  # Another instance still reads the persisted stop.
    with pytest.raises(api.HTTPException):api.reserve_public_budget(ai_calls=1)


@pytest.mark.parametrize('info,status',[
    ({'projectId':'offline-free-ai-project','billingEnabled':True},200),
    ({'projectId':'offline-free-ai-project'},200),
    ({'projectId':'different-project','billingEnabled':False},200),
    ({'projectId':'offline-free-ai-project','billingEnabled':False},403),
])
def test_free_inference_billing_check_fails_closed(public_profile,monkeypatch,info,status):
    monkeypatch.setattr(api,'billing_session',lambda:SimpleNamespace(get=lambda *a,**k:SimpleNamespace(status_code=status,json=lambda:info)))
    monkeypatch.setattr(api,'genai_client',lambda:pytest.fail('Billed or unverifiable key project must stop inference'))
    with TestClient(api.app,base_url='https://testserver') as c:
        response=c.post('/api/chat',json={'message':'Hi'})
        assert response.status_code==503 and 'unbilled' in response.json()['detail']


def test_free_model_checks_billing_each_call_and_preserves_native_json(public_profile,monkeypatch):
    lookups=[];calls=[];raw='{"quote":"20%", "items":[]}'
    def billing_get(url,**kwargs):
        lookups.append((url,kwargs));return SimpleNamespace(status_code=200,json=lambda:{'projectId':'offline-free-ai-project','billingEnabled':False})
    def model(**kwargs):
        calls.append(kwargs);return iter([SimpleNamespace(text=raw)])
    monkeypatch.setattr(api,'billing_session',lambda:SimpleNamespace(get=billing_get))
    monkeypatch.setattr(api,'genai_client',lambda:SimpleNamespace(models=SimpleNamespace(generate_content_stream=model)))
    with TestClient(api.app,base_url='https://testserver') as c:
        for _ in range(2):
            response=c.post('/api/chat',json={'message':'Return this schema','max_output_tokens':8192,
                'response_schema':{'type':'object','properties':{'quote':{'type':'string'},'items':{'type':'array','items':{'type':'string'}}}}})
            assert response.status_code==200 and '20%' in response.text
    assert len(lookups)==len(calls)==2
    assert lookups[0][1]['timeout']==5 and lookups[0][1]['headers']['X-Goog-User-Project']=='offline-public-project'
    assert all(call['model']=='gemini-3.5-flash-lite' and call['config'].max_output_tokens==4096 for call in calls)
    assert calls[0]['config'].response_mime_type=='application/json'


def test_public_request_size_limit_precedes_quota_or_model_work(public_profile,monkeypatch):
    monkeypatch.setattr(api,'genai_client',lambda:pytest.fail('Oversized requests must not reach Gemini'))
    with TestClient(api.app,base_url='https://testserver') as c:
        assert c.post('/api/chat',content=b'x'*(6*1024*1024+1)).status_code==413
    assert public_profile.docs=={}
