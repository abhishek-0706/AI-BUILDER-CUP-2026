"""Explicit deployed-cloud smoke check; writes one labelled validation event/photo.

Run: python tests/cloud_smoke.py --url https://SERVICE.run.app --token-file PATH
No model calls are made. The token and private object URI never enter the report.
"""
from __future__ import annotations
import argparse
import base64
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import httpx

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', required=True)
parser.add_argument('--token-file', required=True)
args = parser.parse_args()
token = Path(args.token_file).read_text(encoding='utf-8-sig').strip()
report = {'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
          'url': args.url.rstrip('/'), 'mode': 'deployed_cloud', 'model_calls': 0,
          'checks': [], 'limitations': ['Synthetic demonstration data; no model-quality or business-impact claim.']}

def check(name, passed, **details):
    report['checks'].append({'name': name, 'pass': bool(passed), **details})
    print(('PASS ' if passed else 'FAIL ') + name, flush=True)
    if not passed:
        raise AssertionError(name)

def expect(response, code=200):
    if response.status_code != code:
        # Error content can expose infrastructure identifiers; keep it private.
        raise AssertionError(f'{response.request.url.path}: HTTP {response.status_code}, expected {code}')
    return response

try:
    with httpx.Client(base_url=report['url'], headers={'Authorization': 'Bearer '+token}, timeout=150) as client:
        public = httpx.Client(base_url=report['url'], timeout=90)
        try:
            health = expect(public.get('/health')).json()
            check('cloud_health_and_vertex_configuration', health['status']=='ok' and health['project_configured'], model=health['model'])
            cfg = expect(public.get('/api/config')).json()
            check('bearer_auth_and_private_evidence_configured', cfg['auth_mode']=='bearer' and cfg['evidence_enabled'])
            check('anonymous_warehouse_access_rejected', public.get('/api/bootstrap').status_code==401)
            for path in ['/.env', '/gcp/main.py', '/tmp/retailiq-judge.key', '/tests/test_api.py']:
                check('private_path_unavailable_'+path.replace('/','_'), public.get(path).status_code==404)
            recorded = expect(public.get('/?demo=recorded'))
            check('public_recorded_entry_available', 'guided-demo-btn' in recorded.text)
        finally:
            public.close()
        bootstrap = expect(client.get('/api/bootstrap')).json()
        check('bigquery_bootstrap', bootstrap['source']=='bigquery' and bootstrap['dataIsSynthetic'] is True,
              as_of_date=bootstrap['asOfDate'], products=len(bootstrap['products']))
        check('tracked_catalog_excludes_turnover_aggregate', len(bootstrap['products'])==13 and all(p['id']!='OTHER' for p in bootstrap['products']))
        check('warehouse_forecast_horizon', len(bootstrap['forecast'])==7)
        r01 = next(p for p in bootstrap['products'] if p['id']=='R01')
        check('canonical_catalog_facts', r01['price']==70 and r01['protein']==20)
        rag = expect(client.post('/api/rag/search', json={'query':'protein','top_k':5})).json()
        check('warehouse_retrieval_available', bool(rag.get('documents') or rag.get('docs') or rag.get('results')))
        for endpoint in ['/api/replenishment', '/api/alerts', '/api/top-movers', '/api/segments']:
            expect(client.get(endpoint))
            check('warehouse_widget_'+endpoint.rsplit('/',1)[-1], True)
        reference = (ROOT/'demo/samples/shelf_compliant.jpg').read_bytes()
        evidence = expect(client.post('/api/evidence', json={
            'visit_id':'release-validation', 'store_id':'BLR-KOR-014', 'rep_id':'release-validation',
            'image':{'mime_type':'image/jpeg','data':base64.b64encode(reference).decode('ascii')}
        })).json()
        check('private_gcs_photo_saved', evidence['sha256']==hashlib.sha256(reference).hexdigest() and evidence['bytes']==len(reference))
        image = expect(client.get('/api/evidence/image', params={'gcs_uri':evidence['gcs_uri']}))
        check('authenticated_photo_round_trip', image.content==reference and 'no-store' in image.headers.get('cache-control','') and image.headers.get('content-type')=='image/jpeg' and image.headers.get('x-content-type-options')=='nosniff')
        bad = client.get('/api/evidence/image',params={'gcs_uri':'gs://unrelated-private-bucket/secret.jpg'})
        check('unrelated_bucket_rejected', bad.status_code==400)
        event = {'visit_id':'release-validation','store_id':'BLR-KOR-014','rep_id':'release-validation',
                 'event_type':'audit', 'summary':'Release validation: retained reference image, not a customer visit. Synthetic demonstration.',
                 'metadata':{'release_validation':True,'evidence':{'retained':True,**evidence}}}
        saved = expect(client.post('/api/visits/log',json=event)).json()
        check('firestore_event_saved',saved.get('status')=='logged')
        events = expect(client.get('/api/visits/log')).json()
        check('manager_reads_saved_event',any(e.get('id')==saved['doc_id'] for e in events['events']), event_count=events['count'])
except Exception as exc:
    report['error'] = str(exc).replace(token, '[redacted]')
    print(report['error'], file=sys.stderr)
finally:
    report['pass'] = not report.get('error') and all(c['pass'] for c in report['checks'])
    report['summary'] = {'passed':sum(c['pass'] for c in report['checks']), 'total':len(report['checks'])}
    target = ROOT/'tmp/cloud-smoke-report.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2),encoding='utf-8')
    print('Report: tmp/cloud-smoke-report.json')
    sys.exit(0 if report['pass'] else 1)

