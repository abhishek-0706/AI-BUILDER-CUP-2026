"""Contract checks for the explicitly selected, network-free fixture provider."""
from copy import deepcopy
import pytest
from gcp.fixtures import load_fixture
from gcp.synthetic import query

@pytest.fixture
def data():
    return load_fixture()


def test_bootstrap_queries_have_required_contract_fields(data):
    required={
      'product_catalog':{'id','name','cat','price','stock','predictedUnitsPerDay','caseSize'},
      'revenue_week':{'day','date','revenue','transactions','avg_basket'},
      'forecast_read':{'day','date','predicted','lower','upper','confidence_level','model_run_at'},
      'kpi_rollup':{'revenue_target','conversion_rate','return_customer_pct','nps','total_skus'},
      'segment_stats':{'name','pct','avg_basket','visits','descr'},
      'reorder_alerts':{'product','level','stock','reorder_at','recommended_order_units'},
      'top_movers':{'id','units_sold_last_30d','wow_growth','trending'},
    }
    for name,keys in required.items():
        rows=query(name,data)
        assert rows and all(keys<=set(row) for row in rows), name
    assert len(query('product_catalog',data))==len(data['products'])


def test_no_silent_unknown_or_semantic_retrieval_fallback(data):
    with pytest.raises(ValueError,match='Unsupported synthetic query'):
        query('missing_query',data)
    with pytest.raises(ValueError,match='Vector retrieval is unavailable'):
        query('rag_search_vector',data,query='protein')


def test_snapshot_cannot_invent_another_store_or_earlier_inventory(data):
    assert query('product_catalog',data,store_id='OTHER-STORE')==[]
    assert query('product_catalog',data,as_of_date='2026-01-01')==[]
    assert query('kpi_rollup',data,as_of_date='2026-01-01')==[]


def test_published_and_synthetic_passage_provenance_survives_retrieval(data):
    documents=query('knowledge_docs',data)
    for row in documents:
        original=next(doc for doc in data['kbDocs'] if doc['id']==row['doc_id'])
        assert row['fact']==original['fact']
        assert row['source_title']==original['title']
        assert row['source_url']==original.get('url')
        assert row['is_synthetic'] is (not bool(original.get('url')))
    found=query('rag_search_keyword',data,query='inventory audit sales',top_k=20)
    assert found and all(row['doc_id'] and row['fact'] and row['match_score']>0 for row in found)
    assert query('rag_search_keyword',data,query='zzzzzzunmatched')==[]


def test_inbound_and_explicit_zero_forecast_do_not_create_unnecessary_orders(data):
    p=next(product for product in data['products'] if product['id']=='R01')
    p.update(stock=20,unitsSoldLast30d=300,unitsOnOrder=0)
    first=next(row for row in query('reorder_alerts',data) if row['product_id']=='R01')
    assert first['recommended_order_units']>0
    p['unitsOnOrder']=250
    assert next(row for row in query('reorder_alerts',data) if row['product_id']=='R01')['recommended_order_units']==0
    p.update(unitsOnOrder=0,predictedUnitsPerDay=0)
    zero=next(row for row in query('reorder_alerts',data) if row['product_id']=='R01')
    assert zero['recommended_order_units']==0 and zero['demand_basis']=='forecast'


def test_short_life_products_use_loose_units_and_shelf_life_cover(data):
    rows=query('reorder_alerts',data)
    for p in data['products']:
        if not p.get('shelfLifeDays'):continue
        row=next(row for row in rows if row['product_id']==p['id'])
        assert row['case_size']==1
        assert row['cover_target_days']<=p['shelfLifeDays']
        assert row['recommended_order_units']<=max(0,__import__('math').ceil(p['unitsSoldLast30d']/30*p['shelfLifeDays'])-p['stock'])


def test_future_promotion_is_not_presented_as_active(data):
    rows=query('bootstrap_promotions',data)
    assert rows and all(row['name']!='Protein Pledge Bundle' for row in rows)
    assert [row['name'] for row in query('bootstrap_promotions',data,as_of_date='2026-11-03')]==['Protein Pledge Bundle']


def test_queries_return_copies_and_known_snapshot_provenance(data):
    original=deepcopy(data)
    products=query('product_catalog',data);products[0]['stock']=-100
    documents=query('knowledge_docs',data);documents[0]['fact']='changed'
    assert data==original
    assert all(row['model_name']=='synthetic_fixture_scenario' and row['model_run_at'] is None for row in query('forecast_read',data))
    assert all(row['wow_growth'] is None for row in query('top_movers',data))


def test_planogram_and_visit_contracts_use_canonical_ids(data):
    for key,count in [('planogram',8),('benchmark',7)]:
        rows=query('planogram_spec',data,planogram_id=data[key]['id'])
        assert len(rows)==count
        assert sum(row['weight'] for row in rows)==pytest.approx(1)
    visit=query('visit_brief',data,visit_id=data['visits'][0]['id'])[0]
    assert visit['account_id']==data['visits'][0]['accountId']
    assert visit['past_objections'][0]['objection_text']==data['visits'][0]['history']['pastObjections'][0]
    assert query('visit_brief',data,visit_id='MISSING')==[]
