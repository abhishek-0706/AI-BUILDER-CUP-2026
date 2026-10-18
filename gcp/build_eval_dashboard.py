"""Build a credential-free, static evaluation dashboard from retained evidence."""
from pathlib import Path
import datetime as dt,json
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'submission/evidence'
REPO='https://github.com/abhishek-0706/AI-BUILDER-CUP-2026/blob/main/'
def read(*names):
    for name in names:
        p=E/name
        if p.exists():return json.loads(p.read_text(encoding='utf-8-sig'))
    return {}
def build():
    files={'live':'eval-live-backend.json','offline':'eval-offline.json','python':'python-regressions.json',
           'node':'software-regressions.json','backend':'live-deployment-smoke.json',
           'config':'live-deployment-config.json','ui':'live-ui-deployment-qa.json'}
    data={k:read(v,'evaluator-regressions.json') if k=='offline' else read(v) for k,v in files.items()}
    # Only factual case outcomes and assertion details enter the hosted summary.
    # Full reports remain public in the source repository for inspection.
    live=data['live']
    live.pop('responses',None)
    for item in live.get('results',[]):item.pop('response',None)
    cases=[('shake-facts','Shopper','Catalogue facts','R01 price, protein and stock'),
      ('competitor-facts','Shopper','Product identity','Competitor facts stay separate'),
      ('budget-discovery','Shopper','Discovery eligibility','All eligible in-stock own-brand items'),
      ('basket-arithmetic','Shopper','Basket arithmetic','Two R01 + one B01, no promotion'),
      ('trade-arithmetic','Field rep','Trade arithmetic','Retail price and margin; two-decimal result'),
      ('short-life-replenishment','Field rep','Shelf-life limit','Demand minus stock; cover capped by life'),
      ('stock-cover','Field rep','Inventory cover','Daily demand and days of stock cover'),
      ('source-grounding','Field rep','Evidence citation','Exact KB-103 fact; synthetic provenance'),
      ('unknown-product','Shopper','Honest abstention','Absent product facts remain unknown'),
      ('injection-and-uncertainty','Field rep','Untrusted note','No unseen expiry claim or instruction disclosure')]
    data.update(generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),prototype='https://retailiq-free-20261018-7ce297.web.app/',
      service_url='https://retailiq-live-olhqdslz2q-uc.a.run.app',model='gemini-3.5-flash-lite',
      dataset='Explicit synthetic catalogue and forecasts',
      case_matrix=[dict(zip(('id','role','contract','checks'),row)) for row in cases],
      evidence=[{'label':k.replace('_',' ').title(),'url':REPO+'submission/evidence/'+v} for k,v in files.items() if (E/v).exists()],
      limits={'AI requests/day':50,'API requests/day':500,'Visit saves/day':200,'AI requests/minute':6,'Cloud Run max instances':1},
      limitations=['Ten selected synthetic factual contracts are not a general accuracy score, RAGAS assessment or full prompt-injection defense.',
        'Offline evaluator acceptance/rejection tests validate the evaluator, not live model quality.',
        'Business figures are synthetic; time savings and sales lift remain pilot hypotheses.',
        'Free allowances are not a hard monetary cap. Hosting can incur overages; Gemini stays on an unbilled project.',
        'The public judge workspace is anonymous and synthetic. Production bearer/IAM controls are a separate deployment mode.'])
    out=ROOT/'evaluation-results.json';out.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print('Built evaluation-results.json from retained evidence: '+str(out.stat().st_size)+' bytes')
    return data
if __name__=='__main__':build()
