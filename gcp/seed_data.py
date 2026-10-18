"""Generate synthetic warehouse rows from the same fixture the browser uses.

The aggregate OTHER line represents the remainder of store turnover, not a
sellable product. Last-seven-day totals and tracked-SKU 30-day units reconcile
exactly. Earlier history is synthetic and cannot establish forecast accuracy.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import random
from pathlib import Path
from fixtures import load_fixture


def generate(as_of: dt.date, days: int, out: Path) -> dict[str, int]:
    if days < 30:
        raise ValueError("At least 30 days are required to reproduce SKU velocities")
    data = load_fixture()
    rng = random.Random(20261022)
    origin = dt.date.fromisoformat(data["asOfDate"])
    shift = (as_of-origin).days
    def date(value):
        return (dt.date.fromisoformat(value)+dt.timedelta(days=shift)).isoformat()
    store, rep = data["store"], data["rep"]
    sid = store["storeId"]
    products = [{"product_id":p["id"],"product_name":p["name"],"category":p["cat"],
                 "brand":data["brand"]["name"] if p["ours"] else p["name"].split()[0],
                 "list_price":p["price"],"margin_rate":p["margin"],
                 "default_reorder_point":p["reorderAt"],"pack_size":p["pack"],
                 "is_active":True,"first_listed_date":"2024-04-01",
                 "protein_grams":p["protein"],"added_sugar_grams":p["addedSugar"],
                 "is_ours":p["ours"],"is_tracked":True,"shelf_life_days":p.get("shelfLifeDays"),
                 "case_size":p.get("caseSize",1 if p.get("shelfLifeDays",999)<21 else 12)}
                for p in data["products"]]
    products.append({"product_id":"OTHER","product_name":"Other store assortment (synthetic aggregate)",
                     "category":"Other store assortment","brand":"Synthetic aggregate",
                     "list_price":1000,"margin_rate":0.15,"default_reorder_point":0,
                     "pack_size":"aggregate","is_active":False,"is_tracked":False,"is_ours":False})
    tables = {k:[] for k in ["stores","products","sales_reps","accounts","visits",
              "visit_objections","kb_documents","planogram_rules","promotions",
              "customer_segments","sales_transactions","store_traffic_daily","inventory_snapshots"]}
    tables["products"] = products
    tables["stores"] = [{"store_id":sid,"store_name":store["name"],"city":store["city"],
                         "zone":store["zone"],"format_segment":store["segment"],"sqft":store["sqft"],
                         "open_date":store["openDate"],"daily_revenue_target":data["kpis"]["revenueTarget"],
                         "latest_nps":data["kpis"]["nps"],"nps_as_of":as_of.isoformat()}]
    tables["sales_reps"] = [{"rep_id":rep["employeeId"],"rep_name":rep["name"],"role_title":rep["role"],
                             "territory":rep["territory"],"quota_month":rep["quotaMonth"],
                             "visits_planned_month":rep["visitsPlanned"]}]
    for a in data["accounts"]:
        tables["accounts"].append({"account_id":a["id"],"account_name":a["name"],"account_type":a["type"],
            "store_count":a["stores"],"tier":a["tier"],"relationship_years":int(a["relationship"].split()[0]),
            "ytd_value":a["ytdValue"],"growth_yoy":a["growthYoY"],
            **{"contact_"+k:v for k,v in a["contact"].items()}})
    for v in data["visits"]:
        h = v["history"]
        tables["visits"].append({"visit_id":v["id"],"account_id":v["accountId"],"rep_id":rep["employeeId"],
            "store_id":v["storeId"],"store_name":v["store"],"visit_date":date(v["date"]),"visit_time":v["time"],
            "duration_minutes":int(v["duration"].split()[0]),"status":v["status"],"last_visit_date":date(v["lastVisit"]),
            "visit_frequency":v["visitFrequency"],"objective":v["objective"],"open_tasks":v["openTasks"],
            "last_order_value":h["lastOrderValue"],"orders_last_6m":h["ordersLast6m"],
            "avg_order_value":h["avgOrderValue"],"listings_lost":h["listingsLost"]})
        for n,text in enumerate(h["pastObjections"]):
            tables["visit_objections"].append({"objection_id":f"{v['id']}-{n}","visit_id":v["id"],
                "account_id":v["accountId"],"objection_text":text,"theme":"buyer_history",
                "raised_on":date(v["lastVisit"]),"resolved":False})
    for d in data["kbDocs"]:
        tables["kb_documents"].append({"doc_id":d["id"],"title":d["title"],"fact":d["fact"],
            "source_type":"published" if d.get("url") else "synthetic","category":"Protein nutrition",
            "published_date":None,"embedding":[],"is_synthetic":not bool(d.get("url")),
            "url":d.get("url"),"publisher":d.get("publisher"),"published_label":d.get("published")})
    for pg in [data["planogram"],data["benchmark"]]:
        for r in pg["rules"]:
            tables["planogram_rules"].append({"planogram_id":pg["id"],"planogram_name":pg["name"],
                "bay":pg["bay"],"rule_id":r["code"],"rule_name":r["rule"],"spec":r["spec"],
                "weight":round(1/len(pg["rules"]),9),"effective_from":date("2026-10-01"),"effective_to":date("2026-12-31")})
    for n,p in enumerate(data["promotions"]):
        tables["promotions"].append({"promotion_id":f"PROMO-{n+1:02}","promotion_name":p["name"],"store_id":sid,
            "category":"Protein nutrition","mechanic":"fixture","discount_label":p["discount"],"discount_pct":None,
            "start_date":date(p["startDate"]),"end_date":date(p["endDate"]),"active_weekdays":"",
            "observed_uplift_pct":None,"sku_ids":p["skuIds"],"uplift_label":p["uplift"],"validity_label":p["validity"]})
    tables["customer_segments"] = [{"as_of_date":as_of.isoformat(),"store_id":sid,"segment_name":s["name"],
        "share_pct":s["pct"],"avg_basket_value":s["avgBasket"],"visits_per_week":s["visits"],"description":s["desc"]}
        for s in data["segments"]]
    # Evenly distribute each product's exact 30-day unit total; old days have
    # reproducible seasonality and noise rather than pretending to be real sales.
    for age in range(days-1,-1,-1):
        day = as_of-dt.timedelta(days=age)
        shape = data["revenueWeek"][6-age%7]
        factor = 1 if age < 7 else max(0.5,1-age*0.001)*rng.uniform(0.95,1.05)
        cents = round(shape["revenue"]*factor*100)
        count = max(1,round(shape["transactions"]*factor))
        baskets = [[] for _ in range(count)]
        for p in data["products"]:
            units = p["unitsSoldLast30d"]
            qty = ((age+1)*units//30-age*units//30) if age < 30 else round(units/30*factor)
            for j in range(qty):
                b = (j+sum(ord(c) for c in p["id"]))%count
                baskets[b].append({"product_id":p["id"],"quantity":1,"unit_price":p["price"],
                                   "discount_amount":0,"line_revenue":p["price"],"promotion_id":None})
        allocated = sum(round(l["line_revenue"]*100) for b in baskets for l in b)
        if allocated > cents:
            raise ValueError("Tracked product sales exceed the fixture's store revenue")
        remainder = cents-allocated
        for i,basket in enumerate(baskets):
            value = (remainder//count+(1 if i < remainder%count else 0))/100
            if value > 0:
                basket.append({"product_id":"OTHER","quantity":1,"unit_price":value,
                               "discount_amount":0,"line_revenue":value,"promotion_id":None})
            customer = f"C{i%350:04}"
            segment = data["segments"][i%len(data["segments"])]["name"]
            for j,line in enumerate(basket):
                tables["sales_transactions"].append({**line,"transaction_id":f"T{day:%Y%m%d}-{i:04}",
                    "line_number":j+1,"txn_ts":f"{day}T10:00:00+05:30","txn_date":str(day),"store_id":sid,
                    "customer_id":customer,"segment_name":segment,"channel":"in_store","is_return":False})
        tables["store_traffic_daily"].append({"traffic_date":str(day),"store_id":sid,
            "footfall":round(count/data["kpis"]["conversionRate"]),"unique_visitors":count})
    for p in data["products"]:
        tables["inventory_snapshots"].append({"snapshot_date":str(as_of),"store_id":sid,"product_id":p["id"],
            "units_on_hand":p["stock"],"reorder_point":p["reorderAt"],"units_on_order":0,
            "lead_time_days":1 if p.get("shelfLifeDays") else 7})
    out.mkdir(parents=True,exist_ok=True)
    for name,rows in tables.items():
        with (out/f"{name}.ndjson").open("w",encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row,ensure_ascii=False)+"\n")
    return {name:len(rows) for name,rows in tables.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=Path("seed_out"))
    parser.add_argument("--as-of",default=load_fixture()["asOfDate"])
    parser.add_argument("--days",type=int,default=180)
    args = parser.parse_args()
    print(json.dumps(generate(dt.date.fromisoformat(args.as_of),args.days,args.out),indent=2))
