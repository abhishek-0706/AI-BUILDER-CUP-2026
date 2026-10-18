"""Explicit synthetic query provider; no network, cloud SDK or fallback.

Rows come from the canonical fixture, not BigQuery. Snapshot dates and published
passage provenance are preserved. Select this provider deliberately in main.py.
"""
from __future__ import annotations
from copy import deepcopy
import datetime as dt
import math
import re
from typing import Any

NAMES = frozenset({'product_catalog','revenue_week','forecast_read','reorder_alerts',
 'segment_stats','top_movers','kpi_rollup','promotions_active','visit_brief',
 'planogram_spec','rag_search_keyword','rag_search_vector','knowledge_docs','bootstrap_promotions'})
ALIASES = {'forecasts':'forecast_read','kpis':'kpi_rollup','segments':'segment_stats'}


def _date(value: Any) -> dt.date:
    if isinstance(value,dt.datetime): return value.date()
    if isinstance(value,dt.date): return value
    try: return dt.date.fromisoformat(str(value))
    except (TypeError,ValueError) as exc: raise ValueError('Synthetic query requires an ISO as-of date') from exc


def _number(value: Any, default: float = 0) -> float:
    return float(value) if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) else default


def _round(value: float) -> int:
    return int(math.floor(value + .5))


def _products(fixture: dict) -> list[dict]:
    rows=[]
    for item in fixture.get('products',[]):
        if item.get('isActive',True) is False or item.get('isTracked',True) is False: continue
        row=deepcopy(item)
        life=row.get('shelfLifeDays')
        row.setdefault('shelfLifeDays',None)
        row.setdefault('predictedUnitsPerDay',None)
        row.setdefault('unitsOnOrder',0)
        row.setdefault('leadTimeDays',1 if life else 7)
        row.setdefault('caseSize',1 if 0 < _number(life) < 21 else 12)
        rows.append(row)
    return sorted(rows,key=lambda row:(row.get('cat',''),row.get('id','')))


def _knowledge(fixture: dict) -> list[dict]:
    rows=[]
    for item in fixture.get('kbDocs',[]):
        row=deepcopy(item)
        row['doc_id']=item.get('doc_id',item.get('id'))
        row['id']=row['doc_id']
        url=item.get('source_url',item.get('url'))
        row['url']=url
        row['source_url']=url
        row['source_title']=item.get('source_title',item.get('title',''))
        row['is_synthetic']=item.get('is_synthetic',item.get('isSynthetic',not bool(url)))
        row['source_type']=item.get('source_type','synthetic' if row['is_synthetic'] else 'published')
        row.setdefault('published_date',None)
        row.setdefault('publisher',None)
        row.setdefault('published',None)
        rows.append(row)
    return sorted(rows,key=lambda row:row.get('doc_id') or '')


def _inventory_rows(fixture: dict) -> list[dict]:
    alerts=[]
    for p in _products(fixture):
        if not p.get('ours',False): continue
        forecast=p.get('predictedUnitsPerDay')
        has_forecast=isinstance(forecast,(int,float)) and not isinstance(forecast,bool) and math.isfinite(forecast)
        daily=max(0,float(forecast) if has_forecast else _number(p.get('unitsSoldLast30d'))/30)
        life=_number(p.get('shelfLifeDays'));target=min(21,life) if life>0 else 21
        case=1 if 0<life<21 else max(1,int(_number(p.get('caseSize'),12)))
        stock=max(0,_number(p.get('stock')));inbound=max(0,_number(p.get('unitsOnOrder')))
        reorder=_number(p.get('reorderAt'));lead=max(1,_number(p.get('leadTimeDays'),7))
        cover=stock/daily if daily>0 else None
        if not(stock<=reorder*1.5 or (cover is not None and cover<target)):continue
        gap=max(0,math.ceil(daily*target)-stock-inbound)
        critical=stock<=reorder or (cover is not None and cover<lead)
        alerts.append({'product_id':p['id'],'product':p['name'],'category':p['cat'],
          'stock':stock,'reorder_at':reorder,'units_on_order':inbound,
          'units_per_day':round(daily,1),'days_of_cover':round(cover,1) if cover is not None else None,
          'demand_basis':'forecast' if has_forecast else '30-day sales average',
          'cover_target_days':target,'case_size':case,'level':'critical' if critical else 'warning',
          'recommended_order_units':int(math.ceil(gap/case)*case)})
    return sorted(alerts,key=lambda row:(row['level']!='critical',row['days_of_cover'] if row['days_of_cover'] is not None else math.inf,row['product_id']))


def query(name: str, fixture: dict, **params: Any) -> list[dict[str,Any]]:
    """Return SQL-shaped rows from one labelled, immutable fixture snapshot.

    Unknown queries and synthetic semantic/vector retrieval fail explicitly.
    This provider never imports BigQuery or an embedding/model client.
    """
    name=ALIASES.get(name,name)
    if name not in NAMES: raise ValueError('Unsupported synthetic query: '+str(name))
    if name=='rag_search_vector':
        raise ValueError('Vector retrieval is unavailable in synthetic mode; explicitly select keyword retrieval')
    if not isinstance(fixture,dict): raise ValueError('Synthetic fixture must be an object')
    anchor=_date(fixture['asOfDate']);as_of=_date(params.get('as_of_date') or anchor)
    store=params.get('store_id')
    if store is not None and store!=fixture['store']['storeId']: return []
    try: limit=max(1,min(200,int(params.get('limit') or 50)))
    except (TypeError,ValueError) as exc: raise ValueError('Synthetic limit must be an integer') from exc
    rows: list[dict[str,Any]]=[]
    if name in {'knowledge_docs','rag_search_keyword'}:
        rows=_knowledge(fixture)
        if name=='rag_search_keyword':
            terms=set(re.findall(r'[a-z0-9]{3,}',str(params.get('query','')).lower()))
            for row in rows:
                corpus=(row.get('title','')+' '+row.get('fact','')).lower()
                row['match_score']=sum(term in corpus for term in terms)
                row['retrieval_method']='synthetic_keyword'
            top_k=max(1,min(20,int(params.get('top_k') or 4)))
            rows=sorted((row for row in rows if row['match_score']>0),key=lambda row:(-row['match_score'],row['doc_id']))[:top_k]
        return deepcopy(rows)
    if name=='product_catalog':
        rows=_products(fixture) if anchor<=as_of<=anchor+dt.timedelta(days=14) else []
    elif name=='revenue_week':
        data=fixture.get('revenueWeek',[])
        for index,item in enumerate(data):
            date=anchor-dt.timedelta(days=len(data)-index-1)
            if not(as_of-dt.timedelta(days=6)<=date<=as_of):continue
            transactions=item.get('transactions',0);revenue=item.get('revenue',0)
            rows.append({**deepcopy(item),'date':date.isoformat(),'day':date.strftime('%a'),
                         'avg_basket':_round(revenue/transactions) if transactions else None})
    elif name=='forecast_read':
        for index,item in enumerate(fixture.get('forecast',[])):
            date=anchor+dt.timedelta(days=index+1)
            if date<=as_of:continue
            rows.append({**deepcopy(item),'date':date.isoformat(),'day':date.strftime('%a'),
                         'confidence_level':None,'model_run_at':None,'model_name':'synthetic_fixture_scenario'})
        rows=rows[:7]
    elif name=='kpi_rollup':
        day_index=(as_of-anchor).days+len(fixture.get('revenueWeek',[]))-1
        if 0<=day_index<len(fixture.get('revenueWeek',[])):
            today=fixture['revenueWeek'][day_index];k=fixture['kpis'];products=_products(fixture)
            revenue=today['revenue'];transactions=today['transactions']
            rows=[{'revenue_today':revenue,'revenue_target':k['revenueTarget'],
              'transactions_today':transactions,'avg_basket':_round(revenue/transactions) if transactions else None,
              'conversion_rate':k['conversionRate'],'return_customer_pct':k['returnCustomerPct'],
              'nps':k['nps'],'out_of_stock_skus':sum(p.get('stock',0)<=0 for p in products),
              'total_skus':k.get('totalSKUs',len(products)),'tracked_skus':len(products)}]
    elif name=='segment_stats':
        if as_of>=anchor:
            rows=[{**deepcopy(row),'avg_basket':row['avgBasket'],'descr':row.get('desc',''),
                  'customers_90d':None,'baskets_90d':None,'revenue_90d':None,'revenue_share_90d':None}
                  for row in fixture.get('segments',[])]
            rows.sort(key=lambda row:-row['pct'])
    elif name=='reorder_alerts':
        rows=_inventory_rows(fixture)[:limit] if anchor<=as_of<=anchor+dt.timedelta(days=14) else []
    elif name=='top_movers':
        for p in _products(fixture):
            revenue=p['price']*p['unitsSoldLast30d']
            rows.append({'id':p['id'],'name':p['name'],'cat':p['cat'],'price':p['price'],
               'units_sold_last_30d':p['unitsSoldLast30d'],'revenue_last_30d':_round(revenue),
               'margin':p['margin'],'margin_value_last_30d':_round(revenue*p['margin']),
               'wow_growth':None,'trending':p.get('trending',False),
               'trend_basis':'synthetic fixture flag; no observed weekly comparator'})
        rows=sorted(rows,key=lambda row:-row['units_sold_last_30d'])[:limit]
    elif name in {'bootstrap_promotions','promotions_active'}:
        for index,p in enumerate(fixture.get('promotions',[])):
            if p.get('startDate') and as_of<_date(p['startDate']):continue
            if p.get('endDate') and as_of>_date(p['endDate']):continue
            if name=='bootstrap_promotions':rows.append(deepcopy(p))
            else: rows.append({'id':p.get('id',f'PROMO-{index+1:02}'),'name':p['name'],
               'discount':p['discount'],'category':p.get('category','Protein nutrition'),
               'validity':p.get('validity','All week'),'uplift_pct':None,'uplift_label':p.get('uplift'),
               'is_synthetic':True})
    elif name=='planogram_spec':
        quarter_start=anchor.replace(month=((anchor.month-1)//3)*3+1,day=1)
        quarter_end=(quarter_start.replace(year=quarter_start.year+1,month=1) if quarter_start.month==10 else quarter_start.replace(month=quarter_start.month+3))-dt.timedelta(days=1)
        for pg in [fixture.get('planogram',{}),fixture.get('benchmark',{})]:
            if pg.get('id')!=params.get('planogram_id') or not(quarter_start<=as_of<=quarter_end):continue
            rules=pg.get('rules',[])
            rows=[{'id':pg['id'],'name':pg['name'],'bay':pg['bay'],'rule_id':r['code'],
                   'rule':r['rule'],'spec':r['spec'],'weight':r.get('weight',round(1/len(rules),9))} for r in rules]
            rows.sort(key=lambda row:row['rule_id'])
    elif name=='visit_brief':
        for visit in fixture.get('visits',[]):
            if visit['id']!=params.get('visit_id'):continue
            account=next((a for a in fixture.get('accounts',[]) if a['id']==visit['accountId']),None)
            if account is None:continue
            history=visit.get('history',{});contact=account.get('contact',{})
            rows=[{'visit_id':visit['id'],'visit_date':visit['date'],'visit_time':visit['time'],
               'duration_minutes':int(re.search(r'\d+',str(visit.get('duration','0'))).group()),
               'status':visit['status'],'store_name':visit['store'],'store_id':visit['storeId'],
               'objective':visit.get('objective',''),'open_tasks':deepcopy(visit.get('openTasks',[])),
               'last_visit_date':visit.get('lastVisit'),'days_since_last_visit':(as_of-_date(visit['lastVisit'])).days if visit.get('lastVisit') else None,
               'visit_frequency':visit.get('visitFrequency'),'last_order_value':history.get('lastOrderValue'),
               'orders_last_6m':history.get('ordersLast6m'),'avg_order_value':history.get('avgOrderValue'),
               'listings_lost':deepcopy(history.get('listingsLost',[])),'account_id':account['id'],
               'account_name':account['name'],'account_type':account['type'],'tier':account['tier'],
               'store_count':account['stores'],'ytd_value':account['ytdValue'],'growth_yoy':account['growthYoY'],
               'contact_name':contact.get('name'),'contact_role':contact.get('role'),'contact_style':contact.get('style'),
               'past_objections':[{'objection_text':text,'theme':'buyer_history'} for text in history.get('pastObjections',[])]}]
    return deepcopy(rows)
