"""Live deployment policy/REST/CLI checks. Entirely offline; no credentials or cloud calls."""
import base64
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'gcp'))
import deploy_live as live


@pytest.fixture
def deployment(tmp_path,monkeypatch):
    monkeypatch.setattr(live,'STATE',tmp_path/'state.json')
    d=live.LiveDeployment('retailiq-live-test','reviewer@example.com','gcloud')
    d.state.update(ai_project='retailiq-ai-free-test',runtime_sa='runtime@retailiq-live-test.iam.gserviceaccount.com',
        build_sa='build@retailiq-live-test.iam.gserviceaccount.com',image='us-central1-docker.pkg.dev/retailiq-live-test/retailiq-live/api:test',
        source_bucket='retailiq-live-test-source',build_id='test-build')
    d.state[live.AI_SECRET+'_version']='1';d.state[live.APP_SECRET+'_version']='1'
    return d


def test_existing_relative_cloud_cli_path_is_resolved(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path);(tmp_path/'gcloud.cmd').write_text('offline dummy')
    monkeypatch.setattr(live,'STATE',tmp_path/'unused-state.json')
    d=live.LiveDeployment('retailiq-live-test','reviewer@example.com','gcloud.cmd')
    assert Path(d.gcloud).is_absolute() and d.gcloud==str((tmp_path/'gcloud.cmd').resolve())


@pytest.mark.parametrize('case',[{'host':False},{'host':None},{'old':True},{'old':None},{'ai':True},{'ai':None},{'ai_account':'unexpected-billing-link'}])
def test_billing_policy_stops_before_any_preparation_mutation(deployment,monkeypatch,case):
    calls=[]
    def cli(*args):
        calls.append(args);project=args[3]
        if project==deployment.project:key='host';default=True
        elif project=='retailiq-demo-20261018-67a8b7':key='old';default=False
        else:key='ai';default=False
        value=case.get(key,default);result={} if value is None else {'billingEnabled':value}
        if key=='ai':result['billingAccountName']=case.get('ai_account','')
        return json.dumps(result)
    monkeypatch.setattr(deployment,'cli',cli)
    monkeypatch.setattr(deployment,'request',lambda *a,**k:pytest.fail('Bad billing policy must stop REST mutations'))
    with pytest.raises(live.DeploymentError):deployment.prepare()
    assert all(c[:3]==('billing','projects','describe') for c in calls)


@pytest.mark.parametrize('index_exists',[False,True])
def test_prepare_enables_quota_consumer_api_and_idempotent_manager_index(deployment,monkeypatch,index_exists):
    calls=[];monkeypatch.setattr(deployment,'policy',lambda:{'billingEnabled':True})
    monkeypatch.setattr(deployment,'ensure_service_account',lambda short,description:short+'@'+deployment.project+'.iam.gserviceaccount.com')
    def cli(*args):
        calls.append(args)
        if args[:2]==('projects','list'):return json.dumps([{'projectId':deployment.state['ai_project']}])
        if args[:2]==('projects','describe'):return '{"projectNumber":"123456"}'
        if args[:3]==('iam','roles','list'):return json.dumps([{'name':'projects/'+deployment.state['ai_project']+'/roles/retailiqBillingCheck'}])
        if args[:3]==('firestore','databases','list'):return json.dumps([{'name':'projects/test/databases/(default)'}])
        if args[:4]==('firestore','indexes','composite','list'):
            return json.dumps([{'fields':[{'fieldPath':'store_id','order':'ASCENDING'},{'fieldPath':'created_at','order':'DESCENDING'}],
                'queryScope':'COLLECTION','state':'READY'}] if index_exists else [])
        if args[:3]==('artifacts','repositories','list'):return '[{"name":"projects/test/locations/us-central1/repositories/retailiq-live"}]'
        return '{}'
    monkeypatch.setattr(deployment,'cli',cli)
    monkeypatch.setattr(deployment,'request',lambda *a,**k:{})
    deployment.prepare()
    host_enable=next(c for c in calls if c[:2]==('services','enable') and '--project='+deployment.project in c)
    assert 'apikeys.googleapis.com' in host_enable and 'cloudbilling.googleapis.com' in host_enable
    assert not any('bigquery.googleapis.com' in c or 'aiplatform.googleapis.com' in c for c in calls)
    indexes=[c for c in calls if c[:4]==('firestore','indexes','composite','create')]
    assert len(indexes)==(0 if index_exists else 1)
    if indexes:assert '--async' in indexes[0] and '--collection-group=visit_events' in indexes[0] and '--query-scope=collection' in indexes[0]
    assert not any(c[:3]==('billing','projects','link') for c in calls)


def test_deploy_uses_fixture_date_low_scaling_and_secret_references(deployment,tmp_path,monkeypatch):
    monkeypatch.setattr(live,'ROOT',tmp_path);(tmp_path/'tmp').mkdir()
    monkeypatch.setattr(live,'load_fixture',lambda:{'asOfDate':'2026-10-22'})
    monkeypatch.setattr(deployment,'policy',lambda:{'billingEnabled':True})
    monkeypatch.setattr(deployment,'build_status',lambda:{'status':'SUCCESS'})
    calls=[]
    def cli(*args):
        calls.append(args)
        return json.dumps({'status':{'url':'https://example.run.app','latestReadyRevisionName':'rev-test'}}) if args[:3]==('run','services','describe') else '{}'
    monkeypatch.setattr(deployment,'cli',cli);deployment.deploy()
    env=json.loads((tmp_path/'tmp/live-env.json').read_text())
    assert env['DEMO_AS_OF_DATE']=='2026-10-22'
    assert env['RETAILIQ_DATA_SOURCE']=='synthetic' and env['RETAILIQ_AI_PROVIDER']=='gemini_free'
    assert env['GEMINI_FREE_PROJECT_ID']==deployment.state['ai_project'] and env['AI_DAILY_REQUEST_LIMIT']=='50'
    assert not {'GEMINI_API_KEY','JUDGE_SESSION_SECRET','RETAILIQ_API_KEY'}&env.keys()
    command=next(c for c in calls if c[:2]==('run','deploy'))
    assert all(flag in command for flag in ['--min-instances=0','--max-instances=1','--max=1','--concurrency=2','--no-cpu-boost','--cpu-throttling'])
    assert any(c.startswith('--set-secrets=GEMINI_API_KEY=') and ':1' in c and 'JUDGE_SESSION_SECRET=' in c for c in command)


def test_publish_omits_static_runtime_and_uses_same_origin_run_rewrites(deployment,monkeypatch):
    monkeypatch.setattr(deployment,'policy',lambda:{'billingEnabled':True})
    monkeypatch.setattr(deployment,'ensure_firebase',lambda:None);monkeypatch.setattr(deployment,'ensure_site',lambda:deployment.project)
    monkeypatch.setattr(live,'collect_files',lambda **kwargs:{'/runtime-config.js':b'backend:false','/index.html':b'public','/pitch-slides.pdf':b'PDF'})
    version='sites/'+deployment.project+'/versions/testversion';requests=[]
    def request(method,url,body=None,**kwargs):
        requests.append((method,url,body,kwargs))
        if url.endswith('/versions'):return {'name':version}
        if url.endswith(':populateFiles'):
            assert '/runtime-config.js' not in body['files']
            return {'uploadUrl':'https://upload-firebasehosting.googleapis.com/upload/'+version+'/files','uploadRequiredHashes':[]}
        if '/releases?' in url:return {'type':'DEPLOY'}
        return {}
    monkeypatch.setattr(deployment,'request',request);deployment.publish()
    config=requests[0][2]['config'];rewrites={r['glob']:r['run'] for r in config['rewrites']}
    assert set(rewrites)=={'/api/**','/runtime-config.js','/health'}
    assert all(run=={'serviceId':'retailiq-live','region':'us-central1'} for run in rewrites.values())
    header_rules=config['headers']
    assert header_rules[0]['glob']=='**' and header_rules[0]['headers']['Cache-Control']=='no-cache'
    # Hosting applies matching headers in order; private routes must override the global static policy.
    assert [rule['glob'] for rule in header_rules[-3:]]==['/api/**','/runtime-config.js','/health']
    assert all(rule['headers']['Cache-Control']=='private, no-store' for rule in header_rules[-3:])


def test_secret_values_never_enter_cli_or_saved_state(deployment,monkeypatch):
    value='OFFLINE-EXAMPLE-SECRET';calls=[]
    monkeypatch.setattr(deployment,'cli',lambda *a:pytest.fail('A secret value must not travel through CLI argv'))
    def request(method,url,body=None,**kwargs):
        calls.append((method,url,body))
        return {'name':'projects/test/secrets/test-secret/versions/7'} if url.endswith(':addVersion') else {}
    monkeypatch.setattr(deployment,'request',request);deployment.put_secret('test-secret',value)
    assert calls[-1][2]['payload']['data']==base64.b64encode(value.encode()).decode()
    saved=live.STATE.read_text();assert value not in saved and base64.b64encode(value.encode()).decode() not in saved
    assert deployment.state['test-secret_version']=='7'


def test_request_rejects_untrusted_url_before_token_and_cli_output_is_bounded(deployment,monkeypatch):
    monkeypatch.setattr(deployment,'cli',lambda *a:pytest.fail('Must reject an untrusted host before fetching OAuth'))
    with pytest.raises(live.DeploymentError,match='Unexpected Google API destination'):deployment.request('POST','https://not-google.example/upload',{})
    monkeypatch.undo()
    monkeypatch.setattr(live.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout='x'*(2*1024*1024+1),stderr=''))
    with pytest.raises(live.DeploymentError,match='permitted size'):deployment.cli('projects','describe','retailiq-live-test')


def test_build_yaml_pins_free_default_pool_and_bounded_timeout():
    text=(Path(__file__).resolve().parents[1]/'gcp/cloudbuild.live.yaml').read_text(encoding='utf-8-sig')
    assert 'machineType: E2_STANDARD_2' in text and 'timeout: 600s' in text
    assert 'logging: CLOUD_LOGGING_ONLY' in text
    assert 'workerPool' not in text and 'privatePool' not in text


@pytest.mark.parametrize('prefix',['AIza','AQ.'])
def test_google_key_formats_are_bounded_without_storing_any_real_key(prefix):
    assert live.valid_google_api_key(prefix+'x'*40)
    assert live.valid_google_api_key(prefix+'x'*(2048-len(prefix)))
    assert not live.valid_google_api_key(prefix+'x'*(2049-len(prefix)))
    assert not live.valid_google_api_key(prefix+'short')
    assert not live.valid_google_api_key(prefix+'x'*40+'\n')


def test_new_key_format_is_redacted_before_error_truncation(deployment,monkeypatch):
    fake='AQ.'+'x'*1800
    monkeypatch.setattr(live.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=1,stdout='',stderr='failure '+fake+' end'))
    with pytest.raises(live.DeploymentError) as error:deployment.cli('projects','describe','retailiq-live-test')
    assert fake not in str(error.value) and 'x'*100 not in str(error.value) and '[redacted]' in str(error.value)
