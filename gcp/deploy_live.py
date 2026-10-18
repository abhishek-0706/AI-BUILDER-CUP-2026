"""Deploy the explicitly consented live, allowance-limited RetailIQ judge profile.

This is separate from deploy_free.py: that Spark-only helper remains fail-closed
when billing is enabled. Gemini MUST use a separate project with no billing.
Keys travel only in memory from API Keys to Secret Manager, never files or argv.
"""
from __future__ import annotations
import argparse, base64, datetime, json, os, re, secrets, subprocess, sys, time
from pathlib import Path
import urllib.error, urllib.parse, urllib.request
from deploy_free import SparkDeployment, DeploymentError, HOSTING, collect_files, compressed_files
from fixtures import load_fixture

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'tmp/live-deployment.json'
REGION = 'us-central1'
SERVICE = 'retailiq-live'
APP_SECRET = 'retailiq-judge-session'
AI_SECRET = 'retailiq-gemini-free'
ALLOWED = {'cloudbilling.googleapis.com','apikeys.googleapis.com','secretmanager.googleapis.com',
           'cloudresourcemanager.googleapis.com','firebasehosting.googleapis.com',
           'firebase.googleapis.com','upload-firebasehosting.googleapis.com',
           'generativelanguage.googleapis.com','storage.googleapis.com'}

def valid_google_api_key(value: str) -> bool:
    # Google currently issues both legacy and newer opaque API-key formats.
    return 20 <= len(value) <= 2048 and re.fullmatch(r'(?:AIza|AQ\.)[A-Za-z0-9_.-]+', value) is not None


class LiveDeployment(SparkDeployment):
    def __init__(self, project, account, gcloud):
        executable = Path(gcloud).expanduser()
        if executable.exists():
            gcloud = str(executable.resolve())
        super().__init__(project, account, gcloud)
        self.state = json.loads(STATE.read_text()) if STATE.exists() else {'hosting_project':project}
        if self.state['hosting_project'] != project:
            raise DeploymentError('State belongs to a different project')

    def save(self):
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(self.state, indent=2))

    def cli(self, *args):
        result = subprocess.run([self.gcloud,*args,'--account='+self.account,'--quiet'],
                                capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=360)
        if result.returncode:
            # These commands never contain API keys or secret values. Still redact
            # credential-shaped strings from diagnostics before reporting a failure.
            err = re.sub(r'((?:AIza|AQ\.)[A-Za-z0-9_.-]+|ya29\.[\w.-]+|Bearer\s+\S+)', '[redacted]', result.stderr)[-1600:]
            raise DeploymentError('Google CLI '+ ' '.join(args[:3])+' failed: '+err)
        if len(result.stdout.encode('utf-8')) > 2*1024*1024:
            raise DeploymentError('Google CLI response exceeded the permitted size; output withheld')
        return result.stdout.strip()

    def request(self, method, url, body=None, *, binary=False, allow_missing=False):
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname not in ALLOWED or parsed.username or parsed.password or parsed.port not in (None,443):
            raise DeploymentError('Unexpected Google API destination')
        if self._token is None:
            self._token = self.cli('auth','print-access-token')
            if not self._token or any(c.isspace() for c in self._token):
                raise DeploymentError('Could not obtain a valid in-memory OAuth token')
        data = body if binary else (json.dumps(body).encode() if body is not None else None)
        req=urllib.request.Request(url,data=data,method=method,headers={
            'Authorization':'Bearer '+self._token,'X-Goog-User-Project':self.project,
            'Content-Type':'application/octet-stream' if binary else 'application/json'})
        try:
            with self._opener.open(req,timeout=60) as response: raw=response.read(2*1024*1024+1)
            if len(raw)>2*1024*1024: raise DeploymentError('Oversized Google response')
            return {} if binary or not raw else json.loads(raw)
        except urllib.error.HTTPError as exc:
            if allow_missing and exc.code==404: return None
            # API Keys and Secret Manager responses can contain credentials.
            # Do not expose their error bodies, even for troubleshooting.
            raise DeploymentError(f'{parsed.hostname} {method} returned HTTP {exc.code}; response withheld') from None

    def policy(self):
        host=json.loads(self.cli('billing','projects','describe',self.project,'--format=json'))
        if host.get('billingEnabled') is not True:
            raise DeploymentError('Live hosting project must have the explicitly approved billing link')
        old=json.loads(self.cli('billing','projects','describe','retailiq-demo-20261018-67a8b7','--format=json'))
        if old.get('billingEnabled') is not False:
            raise DeploymentError('Retired project billing must remain disabled')
        ai=self.state.get('ai_project')
        if ai:
            info=json.loads(self.cli('billing','projects','describe',ai,'--format=json'))
            if info.get('billingEnabled') is not False or info.get('billingAccountName'):
                raise DeploymentError('Gemini project must remain entirely unbilled')
        return host

    def ensure_service_account(self, short, description):
        email=short+'@'+self.project+'.iam.gserviceaccount.com'
        rows=json.loads(self.cli('iam','service-accounts','list','--project='+self.project,'--format=json'))
        if not any(x.get('email')==email for x in rows):
            self.cli('iam','service-accounts','create',short,'--project='+self.project,'--display-name='+description)
        return email

    def grant(self, project, email, role):
        self.cli('projects','add-iam-policy-binding',project,'--member=serviceAccount:'+email,'--role='+role,'--condition=None','--format=json')

    def put_secret(self, name, value):
        base='https://secretmanager.googleapis.com/v1/projects/'+self.project+'/secrets'
        existing=self.request('GET',base+'/'+name,allow_missing=True)
        if existing is None:
            self.request('POST',base+'?secretId='+name,{'replication':{'automatic':{}}})
        version=self.request('POST',base+'/'+name+':addVersion',{'payload':{'data':base64.b64encode(value.encode()).decode()}})
        self.state[name+'_version']=version['name'].rsplit('/',1)[-1]
        self.save()

    def prepare(self):
        self.policy()
        print('Enabling only the live app/build/storage/secret and billing-verification APIs',flush=True)
        self.cli('services','enable','run.googleapis.com','cloudbuild.googleapis.com','artifactregistry.googleapis.com',
                 'firestore.googleapis.com','secretmanager.googleapis.com','iam.googleapis.com','cloudbilling.googleapis.com',
                 'firebase.googleapis.com','firebasehosting.googleapis.com','apikeys.googleapis.com','--project='+self.project)
        if not self.state.get('ai_project'):
            self.state['ai_project']='retailiq-ai-free-261018-'+secrets.token_hex(3)
            self.save()
        ai=self.state['ai_project']
        listing=json.loads(self.cli('projects','list','--filter=projectId='+ai,'--format=json'))
        if not any(p.get('projectId')==ai for p in listing):
            print('Creating separate Gemini project with NO billing account',flush=True)
            self.cli('projects','create',ai,'--name=RetailIQ Gemini Free Only','--format=json')
        self.policy()
        self.cli('services','enable','generativelanguage.googleapis.com','apikeys.googleapis.com','--project='+ai)
        detail=json.loads(self.cli('projects','describe',ai,'--format=json'))
        self.state['ai_project_number']=detail['projectNumber'];self.save()
        print('Creating narrowly scoped runtime and build service accounts',flush=True)
        runtime=self.ensure_service_account('retailiq-live','RetailIQ allowance-limited runtime')
        build=self.ensure_service_account('retailiq-build','RetailIQ default-pool build')
        self.state.update(runtime_sa=runtime,build_sa=build);self.save()
        self.grant(self.project,runtime,'roles/datastore.user')
        self.grant(self.project,runtime,'roles/serviceusage.serviceUsageConsumer')
        self.grant(self.project,build,'roles/run.builder')
        # A custom role can only read AI-project metadata, enabling the mandatory
        # billing-disabled check before inference. It cannot link billing or read keys.
        role='projects/'+ai+'/roles/retailiqBillingCheck'
        roles=json.loads(self.cli('iam','roles','list','--project='+ai,'--format=json'))
        if not any(x.get('name')==role for x in roles):
            self.cli('iam','roles','create','retailiqBillingCheck','--project='+ai,'--title=RetailIQ unbilled project verification',
                     '--permissions=resourcemanager.projects.get','--stage=GA','--format=json')
        self.grant(ai,runtime,role)
        dbs=json.loads(self.cli('firestore','databases','list','--project='+self.project,'--format=json'))
        # gcloud versions return either a resource list or a wrapped dictionary.
        if isinstance(dbs,dict): dbs=dbs.get('databases',[])
        if not any(x.get('name','').endswith('/databases/(default)') for x in dbs):
            print('Creating the single default Firestore database in us-central1',flush=True)
            self.cli('firestore','databases','create','--database=(default)','--location='+REGION,'--type=firestore-native','--project='+self.project,'--format=json')
        indexes=json.loads(self.cli('firestore','indexes','composite','list','--database=(default)',
            '--filter=COLLECTION_GROUP:visit_events','--project='+self.project,'--format=json'))
        if isinstance(indexes,dict): indexes=indexes.get('indexes',[])
        wanted=[('store_id','ASCENDING'),('created_at','DESCENDING')]
        if not any([(f.get('fieldPath'),f.get('order')) for f in row.get('fields',[]) if f.get('fieldPath')!='__name__']==wanted
                   and row.get('queryScope')=='COLLECTION' and row.get('state') in ('READY','CREATING') for row in indexes):
            print('Provisioning the manager visit-events composite index',flush=True)
            self.cli('firestore','indexes','composite','create','--async','--database=(default)','--collection-group=visit_events',
                '--query-scope=collection','--field-config=field-path=store_id,order=ascending',
                '--field-config=field-path=created_at,order=descending','--project='+self.project,'--format=json')
        repos=json.loads(self.cli('artifacts','repositories','list','--location='+REGION,'--project='+self.project,'--format=json'))
        if not any(x.get('name','').endswith('/repositories/retailiq-live') for x in repos):
            self.cli('artifacts','repositories','create','retailiq-live','--repository-format=docker','--location='+REGION,'--project='+self.project,'--format=json')
        if not self.state.get(AI_SECRET+'_version'):
            print('Provisioning a Gemini-only API key directly into Secret Manager (no key output)',flush=True)
            keys='https://apikeys.googleapis.com/v2/projects/'+str(detail['projectNumber'])+'/locations/global/keys'
            keyname=keys.rsplit('/v2/',1)[-1]+'/retailiq-free-backend'
            existing=self.request('GET','https://apikeys.googleapis.com/v2/'+keyname,allow_missing=True)
            if existing is None:
                op=self.request('POST',keys+'?keyId=retailiq-free-backend',{'displayName':'RetailIQ free Gemini only',
                    'restrictions':{'apiTargets':[{'service':'generativelanguage.googleapis.com'}]}})
                for _ in range(40):
                    if op.get('done'): break
                    time.sleep(2)
                    op=self.request('GET','https://apikeys.googleapis.com/v2/'+op['name'])
                if not op.get('done') or op.get('error'): raise DeploymentError('API key creation did not complete')
            data=self.request('GET','https://apikeys.googleapis.com/v2/'+keyname+'/keyString')
            key=data.get('keyString','')
            if not valid_google_api_key(key): raise DeploymentError('Unexpected key format; stopped')
            self.policy()
            self.put_secret(AI_SECRET,key)
            del key,data
            self.state['ai_key_name']=keyname;self.save()
        if not self.state.get(APP_SECRET+'_version'): self.put_secret(APP_SECRET,secrets.token_hex(32))
        for name in (AI_SECRET,APP_SECRET):
            self.cli('secrets','add-iam-policy-binding',name,'--project='+self.project,'--member=serviceAccount:'+runtime,
                     '--role=roles/secretmanager.secretAccessor','--format=json')
        # Private, bounded build-source storage; it is not used for photos or app data.
        bucket=self.project+'-live-build-source'
        b=self.request('GET','https://storage.googleapis.com/storage/v1/b/'+bucket,allow_missing=True)
        if b is None:
            self.cli('storage','buckets','create','gs://'+bucket,'--project='+self.project,'--location='+REGION,
                     '--uniform-bucket-level-access','--public-access-prevention')
        self.request('PATCH','https://storage.googleapis.com/storage/v1/b/'+bucket,{
            'lifecycle':{'rule':[{'action':{'type':'Delete'},'condition':{'age':1}}]},
            'softDeletePolicy':{'retentionDurationSeconds':'0'}})
        self.cli('storage','buckets','add-iam-policy-binding','gs://'+bucket,'--member=serviceAccount:'+build,'--role=roles/storage.objectViewer','--format=json')
        self.state['source_bucket']=bucket;self.save();self.policy()
        print('Prepared: Gemini project unbilled; default Firestore; two secrets; no BigQuery/Vertex/photo retention',flush=True)

    def build(self):
        self.policy()
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
        image=f'{REGION}-docker.pkg.dev/{self.project}/retailiq-live/api:{stamp}'
        self.state['image']=image;self.save()
        print('Submitting one E2_STANDARD_2 default-pool build (10-minute maximum)',flush=True)
        raw=self.cli('builds','submit',str(ROOT),'--project='+self.project,'--region='+REGION,
                     '--config='+str(ROOT/'gcp/cloudbuild.live.yaml'),'--substitutions=_IMAGE='+image,
                     '--service-account=projects/'+self.project+'/serviceAccounts/'+self.state['build_sa'],
                     '--gcs-source-staging-dir=gs://'+self.state['source_bucket']+'/source','--async','--format=json')
        info=json.loads(raw);self.state['build_id']=info['id'];self.save()
        print(json.dumps({'build_id':info['id'],'image':image}),flush=True)

    def build_status(self):
        data=json.loads(self.cli('builds','describe',self.state['build_id'],'--project='+self.project,'--region='+REGION,'--format=json'))
        result={k:data.get(k) for k in ('id','status','createTime','finishTime','logUrl')}
        self.state['build_status']=data.get('status');self.save();print(json.dumps(result,indent=2),flush=True)
        return data

    def deploy(self):
        self.policy()
        if self.build_status().get('status') != 'SUCCESS': raise DeploymentError('Build is not successful')
        env={'GCP_PROJECT':self.project,'RETAILIQ_DATA_SOURCE':'synthetic','RETAILIQ_AI_PROVIDER':'gemini_free',
             'GEMINI_FREE_TIER_CONFIRMED':'true','GEMINI_FREE_PROJECT_ID':self.state['ai_project'],
             'RETAILIQ_PUBLIC_JUDGE':'true','GEMINI_MODEL':'gemini-3.5-flash-lite','DEMO_AS_OF_DATE':load_fixture()['asOfDate'],
             'AI_DAILY_REQUEST_LIMIT':'50','JUDGE_DAILY_REQUEST_LIMIT':'500','JUDGE_DAILY_VISIT_LIMIT':'200',
             'AI_REQUESTS_PER_MINUTE':'6','RETAILIQ_OPEN_DEMO':'false','LOG_LEVEL':'WARNING'}
        envfile=ROOT/'tmp/live-env.json';envfile.write_text(json.dumps(env))
        print('Deploying Cloud Run: request CPU, min 0 / max 1, 512 MiB, concurrency 2, no CPU boost',flush=True)
        self.cli('run','deploy',SERVICE,'--project='+self.project,'--region='+REGION,'--image='+self.state['image'],
                 '--service-account='+self.state['runtime_sa'],'--allow-unauthenticated','--cpu=1','--memory=512Mi',
                 '--min-instances=0','--max-instances=1','--max=1','--concurrency=2','--timeout=120','--cpu-throttling',
                 '--no-cpu-boost','--env-vars-file='+str(envfile),
                 '--set-secrets=GEMINI_API_KEY='+AI_SECRET+':'+self.state[AI_SECRET+'_version']+',JUDGE_SESSION_SECRET='+APP_SECRET+':'+self.state[APP_SECRET+'_version'],
                 '--format=json')
        data=json.loads(self.cli('run','services','describe',SERVICE,'--project='+self.project,'--region='+REGION,'--format=json'))
        self.state['service_url']=data['status']['url'];self.state['revision']=data['status'].get('latestReadyRevisionName');self.save()
        print(json.dumps({'service_url':self.state['service_url'],'revision':self.state['revision']}),flush=True)

    def publish(self):
        self.policy()
        self.ensure_firebase();site=self.ensure_site()
        files=collect_files(include_deck=True,include_demo=False)
        del files['/runtime-config.js'] # Static files precede rewrites; serve live config from Run.
        # These two public, credential-free dashboard assets are explicit additions.
        for asset in ('eval-dashboard.html', 'evaluation-results.json'):
            source = ROOT / asset
            if source.exists():
                if source.is_symlink() or not source.resolve().is_relative_to(ROOT.resolve()):
                    raise DeploymentError('Unsafe dashboard asset path')
                raw = source.read_bytes()
                if len(raw) > 8 * 1024 * 1024:
                    raise DeploymentError('Dashboard asset exceeds the public file limit')
                files['/' + asset] = raw
        if sum(map(len, files.values())) > 32 * 1024 * 1024:
            raise DeploymentError('Live bundle exceeds the bounded public bundle limit')
        run={'serviceId':SERVICE,'region':REGION}
        config={'rewrites':[{'glob':'/api/**','run':run},{'glob':'/runtime-config.js','run':run},{'glob':'/health','run':run}],
                'headers':[{'glob':'**','headers':{'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff',
                    'Referrer-Policy':'strict-origin-when-cross-origin'}},
                    *[{'glob':path,'headers':{'Cache-Control':'private, no-store'}}
                      for path in ('/api/**','/runtime-config.js','/health')]]}
        version=self.request('POST',HOSTING+'/sites/'+site+'/versions',{'config':config})
        name=version['name']
        if not re.fullmatch(r'sites/'+re.escape(site)+r'/versions/[A-Za-z0-9_-]+',name): raise DeploymentError('Invalid hosting version')
        manifest,blobs=compressed_files(files)
        # Video is managed independently by the owner. Reuse the active version's
        # two known media hashes instead of reading or overwriting local media.
        previous = self.state.get('hosting_version')
        if previous:
            if not re.fullmatch(r'sites/' + re.escape(site) + r'/versions/[A-Za-z0-9_-]+', previous):
                raise DeploymentError('Invalid prior hosting version')
            listing = self.request('GET', HOSTING + '/' + previous + '/files?pageSize=1000')
            if listing.get('nextPageToken'):
                raise DeploymentError('Prior media manifest exceeds the bounded page size')
            for item in listing.get('files', []):
                if item.get('path') in ('/demo.html', '/demo/RetailIQ_Abhishek_voice_demo.mp4'):
                    digest = item.get('hash', '')
                    if not re.fullmatch(r'[a-f0-9]{64}', digest):
                        raise DeploymentError('Invalid existing public media hash')
                    manifest[item['path']] = digest
        populated=self.request('POST',HOSTING+'/'+name+':populateFiles',{'files':manifest})
        upload=populated['uploadUrl'].rstrip('/')
        if upload!='https://upload-firebasehosting.googleapis.com/upload/'+name+'/files': raise DeploymentError('Invalid upload destination')
        for digest in populated.get('uploadRequiredHashes',[]):
            if digest not in blobs: raise DeploymentError('Requested unknown upload')
            self.request('POST',upload+'/'+digest,blobs[digest],binary=True)
        self.policy()
        self.request('PATCH',HOSTING+'/'+name+'?update_mask=status',{'status':'FINALIZED'})
        release=self.request('POST',HOSTING+'/sites/'+site+'/releases?'+urllib.parse.urlencode({'versionName':name}))
        if release.get('type')!='DEPLOY': raise DeploymentError('No deployment confirmation')
        self.state.update(hosting_url='https://'+site+'.web.app',hosting_version=name);self.save()
        print('Live same-origin Firebase/Cloud Run site: '+self.state['hosting_url'],flush=True)

    def status(self):
        host=self.policy()
        print(json.dumps({'hosting_billing_enabled':host['billingEnabled'],**self.state},indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=['prepare','build','build-status','deploy','publish','status'])
    p.add_argument('--project',required=True);p.add_argument('--account',required=True);p.add_argument('--gcloud',required=True)
    p.add_argument('--accept-free-tier-overages',action='store_true')
    a=p.parse_args()
    if a.phase not in ('status','build-status') and not a.accept_free_tier_overages: p.error('Explicit allowance-overage consent is required')
    try:
        d=LiveDeployment(a.project,a.account,a.gcloud)
        getattr(d,a.phase.replace('-','_'))()
    except (DeploymentError,OSError,ValueError,subprocess.SubprocessError) as exc:
        print('Live deployment stopped: '+str(exc),file=sys.stderr);return 1
    return 0
if __name__=='__main__': raise SystemExit(main())
