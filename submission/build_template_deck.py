"""Fill the official AI Builder Cup PDF without replacing its template artwork."""
from pathlib import Path
import argparse, copy, hashlib, io, json, re, sys
ROOT=Path(__file__).resolve().parents[1]
DEPS=ROOT/"tmp/pdf-template-tools"
if DEPS.is_dir(): sys.path.insert(0,str(DEPS))
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader
from xml.sax.saxutils import escape
GREEN=HexColor("#095f52"); INK=HexColor("#18382f"); MUTED=HexColor("#526b60")
LINE=HexColor("#d7e4db"); SAGE=HexColor("#edf4ee"); GOLD=HexColor("#946c3e")
TEMPLATE=ROOT/"submission/AI_Builder_Cup_Original_Template.pdf"
SOURCE_INDICES=[0,2,3,4,5,6,7,8,9,10,11,12,13]
OUT=ROOT/"pitch-slides.pdf"
FONT_PATHS=[(Path(r"C:\Windows\Fonts\arial.ttf"),Path(r"C:\Windows\Fonts\arialbd.ttf")),
            (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))]
for regular,bold in FONT_PATHS:
    if regular.is_file() and bold.is_file(): break
else: raise FileNotFoundError("Arial or DejaVu Sans font files are required.")
pdfmetrics.registerFont(TTFont("Body",str(regular)))
pdfmetrics.registerFont(TTFont("BodyBold",str(bold)))
pdfmetrics.registerFontFamily("Body",normal="Body",bold="BodyBold",italic="Body",boldItalic="BodyBold")
STYLES={}
def para(c,text,x,top,width,size=11.4,leading=None,color=INK,bold=False,max_height=None):
    leading=leading or size*1.35
    key=(size,leading,color.hexval(),bold)
    if key not in STYLES:
        STYLES[key]=ParagraphStyle("p",fontName="BodyBold" if bold else "Body",fontSize=size,leading=leading,textColor=color,spaceAfter=0)
    p=Paragraph(text,STYLES[key])
    w,h=p.wrap(width,1000)
    if max_height is not None and h>max_height+0.1:
        raise ValueError(f"Text overflow ({h:.1f}>{max_height}) near: {text[:85]}")
    p.drawOn(c,x,top-h)
    return top-h
def line(c,x1,y1,x2,y2,color=LINE,width=1):
    c.setStrokeColor(color); c.setLineWidth(width); c.line(x1,y1,x2,y2)
def box(c,x,y,w,h,fill=SAGE,stroke=LINE,radius=7):
    c.setFillColor(fill);c.setStrokeColor(stroke);c.roundRect(x,y,w,h,radius,stroke=1,fill=1)
def card(c,x,top,w,h,title,text,size=10.8,fill=SAGE):
    box(c,x,top-h,w,h,fill)
    y=para(c,escape(title),x+12,top-12,w-24,12,color=GREEN,bold=True,max_height=38)
    para(c,text,x+12,y-10,w-24,size,max_height=h-(top-y)-20)
def footer(c,number,note="Live AI and persistence use explicitly synthetic commercial context."):
    line(c,28,21,692,21)
    para(c,escape(note),28,16,610,7.3,color=MUTED,max_height=12)
    para(c,f"{number:02d} / 13",650,16,42,7.5,color=MUTED,max_height=12)
def arrow(c,x1,y1,x2,y2,color=GREEN):
    line(c,x1,y1,x2,y2,color,1.25)
    import math
    angle=math.atan2(y2-y1,x2-x1)
    for delta in (-.52,.52):
        x=x2-6*math.cos(angle+delta);y=y2-6*math.sin(angle+delta)
        line(c,x2,y2,x,y,color,1.25)
def table(c,rows,widths,top,header=None,size=10,row_h=29):
    x0=28
    if header:
        x=x0
        for text,w in zip(header,widths):
            c.setFillColor(SAGE);c.rect(x,top-row_h,w,row_h,stroke=0,fill=1)
            para(c,escape(text),x+8,top-7,w-16,size,bold=True,color=GREEN,max_height=row_h-10)
            x+=w
        top-=row_h
    for row in rows:
        x=x0
        for text,w in zip(row,widths):
            para(c,text,x+8,top-6,w-16,size,max_height=row_h-8)
            x+=w
        line(c,x0,top-row_h,x0+sum(widths),top-row_h)
        top-=row_h
    return top
def slide_team(c):
    # Fill beside, never over, the original a/b/c labels.
    para(c,"RetailIQ",285,120,400,16,bold=True,color=GREEN,max_height=25)
    para(c,"Abhishek Agarwal",285,98,400,15,bold=True,max_height=25)
    para(c,"Retail &amp; Commerce: Intelligent Customer and Business Experiences",285,76,405,10.2,leading=12.5,max_height=30)
    para(c,"Team member: Vivek Sharma",90,38,590,10.2,color=MUTED,max_height=15)
def slide_idea(c):
    para(c,"RetailIQ: shelf evidence to an accountable retail action",28,308,664,20,bold=True,color=GREEN,max_height=52)
    para(c,"A CPG field representative captures the shelf, verifies a stock discrepancy, prepares a source-linked buyer conversation and saves an action a manager can review. The buyer retains commercial authority.",28,244,664,12.4,max_height=68)
    for x,title,text in [(28,"SENSING","Qualified shelf observations; PASS, FAIL or NOT VISIBLE."),
                         (256,"EXECUTION","Locate/reconcile existing stock or justify replenishment."),
                         (484,"EMPOWERMENT","Cited facts, rehearsal, structured debrief and a reviewable record.")]:
        card(c,x,155,208,102,title,escape(text),11)
    footer(c,2,"Primary user: CPG field rep. Managers review; buyers approve; shoppers discover.")
def slide_opportunities(c):
    # Original three questions remain intact above this answer region.
    card(c,28,242,208,173,"1. How it differs",
         "Connects shelf evidence, stock logic, a prepared conversation and manager review in one visit. It goes beyond an isolated audit score or chat answer.<br/><br/>Design comparison; no exhaustive competitor benchmark is claimed.",10.7)
    card(c,256,242,208,173,"2. How it solves the problem",
         "Zero facings plus 64 recorded units triggers a locate-and-reconcile task. A justified order nets usable and inbound stock against demand, case rules and shelf life.<br/><br/>The example is synthetic; physical verification remains necessary.",10.7)
    card(c,484,242,208,173,"3. USP",
         "Evidence + retail arithmetic + human control. Own-brand compliance and competitor benchmarking stay separate. Unseen evidence remains unknown; a saved record exposes the proposed action.",10.7)
    para(c,'Research rationale: a 55-retailer study links availability to sensing, execution and empowerment. <link href="https://doi.org/10.1108/IJRDM-09-2025-0758" color="#095f52">Corsten et al., IJRDM, May 2026</link>. Industry findings are not RetailIQ outcomes.',28,55,664,8.2,max_height=29)
    footer(c,3,"No achieved sales uplift or stockout reduction is claimed.")
def slide_features(c):
    groups=[
      ("Field representative","Typed Gemini shelf audit; abstain when evidence, product or expiry is unclear.<br/><br/>Confirm counts, reconcile shelf/system stock, size a proposed order and generate a source-linked pitch.<br/><br/>Save structured audits and visit debriefs."),
      ("Manager and buyer","Review Firestore visit records within the same signed workspace.<br/><br/>Inspect verdicts, confirmed observations and next actions. Dashboard figures and forecasts are synthetic.<br/><br/>Buyer approval is necessary; photo retention is disabled live."),
      ("Shopper","Ask Gemini for catalogue options by need, preference or budget.<br/><br/>Compare fixture products, prices and nutrition; build a proposed basket.<br/><br/>Synthetic data is labelled. No personal model key is needed on the live workspace.")]
    for x,(title,text) in zip((28,256,484),groups): card(c,x,308,208,239,title,text,10.7)
    footer(c,4,"Three roles share one synthetic catalogue. Proposed orders do not place ERP purchases.")


def slide_process(c):
    xs=[28,198,368,538]; w=154; h=84; top=308
    nodes=[("01 Capture","Photo or selected shelf frames"),("02 Qualify","Visibility and confirmed counts"),
           ("03 Verify","System stock and inbound units"),("04 Choose action","Reconcile shelf or review order")]
    for x,(t,d) in zip(xs,nodes): card(c,x,top,w,h,t,escape(d),10)
    for x in xs[:-1]: arrow(c,x+w,top-h/2,x+170,top-h/2)
    arrow(c,615,224,615,194)
    bottom=[("08 Manager review","Read saved Firestore actions"),("07 Persist","Save in signed workspace"),
            ("06 Buyer control","Validate draft and terms"),("05 Live pitch","Source-linked talking points")]
    for x,(t,d) in zip(xs,bottom): card(c,x,194,w,h,t,escape(d),10)
    for x in xs[:-1]: arrow(c,x+170,152,x+w,152)
    para(c,"Rep decision: zero facings plus positive stock triggers a locate-and-reconcile task. Proposed quantities net demand, stock and inbound, then apply case and shelf-life limits.",28,93,664,10,max_height=32)
    para(c,"Shopper journey: describe a need → Gemini compares synthetic catalogue stock, price and nutrition → review a proposed basket.",28,51,664,9.7,max_height=27)
    footer(c,5,"Rep → confirmed action → Firestore → manager. Shopper discovery is a second entry point.")


def slide_wireframes(c):
    for x,title,labels in [
        (28,"Field Execution",["Store / buyer / visit context","Shelf evidence + verdicts","Counts + stock constraints","Review next action; save visit"]),
        (256,"Team and Analytics",["Revenue + inventory risk","Forecast + segment context","Saved audit / order events","Inspect evidence; follow up"]),
        (484,"Shopper Insights",["Need + preferences + basket","Conversation + options","Stock + price + nutrition","Compare suitable products"])]:
        box(c,x,72,208,236,white)
        para(c,title,x+12,294,184,13,bold=True,color=GREEN,max_height=20)
        y=260
        for index,label in enumerate(labels):
            box(c,x+12,y-35,184,35,GREEN if index==3 else SAGE)
            para(c,escape(label),x+20,y-9,168,10.2,color=white if index==3 else MUTED,max_height=25)
            y-=46
    footer(c,6,"Explanatory screen structures; actual prototype captures appear in the snapshot section.")
def slide_architecture(c):
    para(c,"VERIFIED LIVE PATH — SAME-ORIGIN APPLICATION AND API",28,309,664,10,bold=True,color=GREEN,max_height=20)
    card(c,28,283,206,63,"Firebase Hosting","HTTPS frontend + API rewrites",10)
    card(c,258,283,206,63,"Cloud Run / FastAPI","us-central1; signed workspaces",10)
    card(c,488,283,204,63,"Gemini 3.5 Flash-Lite","Separate unbilled AI project",10)
    arrow(c,234,251,258,251);arrow(c,464,251,488,251)
    card(c,28,192,206,64,"Data provenance","Synthetic catalogue and forecasts",9.5)
    card(c,258,192,206,64,"Firestore","Workspace-scoped visit records",9.5)
    card(c,488,192,204,64,"AI access","Server-held key; no paid fallback",9.5)
    arrow(c,361,220,361,192)
    line(c,234,160,246,160); line(c,246,160,246,234); arrow(c,246,234,258,234)
    card(c,28,112,664,77,"Guardrails / live deployment boundary",
         "Typed outputs; abstain on unseen evidence. Facings are not stock. Code checks shelf-life/inbound; human approval gates orders. Signed workspace isolation; server-only key. Rechecked unbilled AI; no Vertex fallback. Anonymous synthetic judge mode.",9.4)
    footer(c,7,"No live BigQuery/Vertex route; no photo retention. Limits are not a hard billing cap.")


def slide_technologies(c):
    rows=[
      ["Firebase Hosting","HTTPS frontend and same-origin API rewrites","Live public entry point"],
      ["Cloud Run / FastAPI","Retail API and model proxy in us-central1","Live; capped runtime and requests"],
      ["Gemini 3.5 Flash-Lite","Text, shelf vision and buyer/shopper dialogue","Live; separate unbilled AI project"],
      ["Firestore","Signed-workspace visit records and limits","Actual write/read/isolation verified"],
      ["HTML / CSS / JavaScript","Field rep, manager and shopper surfaces","Three roles; synthetic context labelled"],
      ["BigQuery / BigQuery ML","Warehouse analytics and trained forecasting","Reference; not live catalogue"],
      ["Gemini on Vertex AI","Service-account model route","Reference; not live inference"],
      ["Cloud Storage evidence","Private retained shelf photos","Reference; disabled live"],
      ["Playwright / pytest / CI","UI, API, provider and deployment checks","Offline/live evidence distinguished"]]
    table(c,rows,[168,258,238],308,["Technology","Purpose","Actual status"],9.3,row_h=26)
    footer(c,8,"No live-path usage of BigQuery, Vertex AI, Looker, AlloyDB or Cloud SQL is implied.")


def slide_cost(c):
    para(c,"Gemini uses a separate unbilled project with no paid fallback. Firebase Hosting, Cloud Run and Firestore can incur metered charges; actual cost is unverified and no zero-bill guarantee is claimed.",28,309,664,11.6,max_height=44)
    rows=[
      ["10 reps × 6 visits/day × 22 days","1,320 visits / month"],
      ["Assumed 12-minute baseline → 5-minute scoped-task target","7 minutes / visit"],
      ["1,320 × 7 / 60","154 hours released capacity"],
      ["154 hours × assumed INR 300 / hour","INR 46,200 capacity value"],
      ["Target operating budget: INR 5 × 1,320 visits","INR 6,600 / month"],
      ["Illustrative capacity value less operating target","INR 39,600 / month"]]
    table(c,rows,[470,194],248,["Editable planning assumption","Scenario value"],10.2,row_h=27)
    para(c,"Runtime: min 0 / max 1 instance; 1 CPU, 512 MiB, concurrency 2; 50 AI, 500 API and 200 saves/day, 6 AI requests/min. These are usage limits, not a hard billing cap. Implementation scope and actual cost remain unmeasured.",28,53,664,9.1,max_height=30)
    footer(c,9,"Scope: audit preparation and debrief administration, not the entire store visit.")
def slide_snapshots(c):
    live=[ROOT/"assets/submission"/n for n in ("prototype-rep-live.png","prototype-manager-live.png","prototype-shopper-live.png")]
    if not all(p.is_file() for p in live): raise FileNotFoundError("All three authorized live-role screenshots are required.")
    images=[(live[0],"Field representative","Live workspace: shelf/planning actions over synthetic inventory."),
            (live[1],"Manager","Actual persisted, labelled QA record; not a customer outcome."),
            (live[2],"Shopper","Gemini discovery over the explicit synthetic catalogue.")]
    for x,(path,title,caption) in zip((28,256,484),images):
        box(c,x,59,208,249,white)
        c.drawImage(ImageReader(str(path)),x+7,115,width=194,height=184,preserveAspectRatio=True,anchor="c",mask="auto")
        para(c,title,x+9,101,190,11,bold=True,color=GREEN,max_height=20)
        para(c,caption,x+9,78,190,8.6,max_height=28)
    footer(c,10,"Actual public application captures. Catalogue, customer figures and forecasts are synthetic.")


def slide_benchmark(c):
    report=json.loads((ROOT/"submission/evidence/eval-live-backend.json").read_text(encoding="utf-8"))
    assert report["run_mode"]=="live_backend" and report["model"]=="gemini-3.5-flash-lite"
    assert report["model_calls"]==10 and report["summary"]["total"]==10
    passed=report["summary"]["passed"]
    para(c,f"Current Gemini 3.5 Flash-Lite: {passed}/10 selected synthetic cases passed; 10 calls, no retries.",28,309,664,10.5,bold=True,color=GREEN,max_height=28)
    groups=[
      ("Catalogue facts",["shake-facts","competitor-facts"],"Shake and competitor price, protein, stock and sugar contracts."),
      ("Budget discovery",["budget-discovery"],"FAIL: included S02/S03 beyond the stated price limit."),
      ("Commerce arithmetic",["basket-arithmetic","trade-arithmetic","stock-cover"],"Basket total, unit trade price and stock-cover calculations."),
      ("Short-life order",["short-life-replenishment"],"FAIL: model returned 21 vs expected 5. Execute only code-validated human drafts."),
      ("Source grounding",["source-grounding"],"Exact supplied KB-103 fact, citation and synthetic provenance."),
      ("Uncertainty / injection",["unknown-product","injection-and-uncertainty"],"Unknown product and unseen expiry abstention; no instruction disclosure.")]
    by_id={r["case_id"]:r for r in report["results"]}
    rows=[]
    for label,ids,scope in groups:
        n=sum(bool(by_id[i]["pass"]) for i in ids)
        result=f"{n}/{len(ids)} " + ("PASS" if n==len(ids) else "FAIL")
        rows.append([label,result,scope])
    table(c,rows,[150,130,384],278,["Selected contract group","Actual result","Observed outcome / limitation"],8.5,row_h=31)
    para(c,"Separate proof: 14/14 live API checks and three-role UI QA. Offline: 164 browser/policy, 105 Python checks across two runs, 38 evaluator assertions. Reports: submission/evidence/.",28,51,664,8.1,max_height=25)
    footer(c,11,"Selected factual contracts only: not RAGAS, general accuracy, vision accuracy, savings or a complete injection defence.")

def slide_future(c):
    card(c,28,308,322,237,"Proposed development",
         "1. Replace generated data with permissioned POS, stock and inbound feeds.<br/><br/>2. Independently label shelf evidence and measure precision, coverage and abstention.<br/><br/>3. Add approved enterprise identity and ERP draft-order handoffs.<br/><br/>4. Expand current-model evaluation and establish cost/latency under representative usage.",11)
    card(c,370,308,322,237,"Falsifiable pilot",
         "Compare a two-week baseline with an assisted period.<br/><br/>Test the five-minute target for scoped audit/debrief work. Measure corrections and productive reuse of time.<br/><br/>Track stock discrepancy closure, source-supported claims, order waste risk, latency and cost per completed workflow.",11)
    footer(c,12,"Roadmap and pilot targets only. No achieved revenue uplift or stockout reduction is claimed.")
def slide_links(c):
    # Original three link labels remain visible; URLs fill the space beside them.
    links=[
      ("https://github.com/abhishek-0706/AI-BUILDER-CUP-2026",292.5),
      ("https://retailiq-free-20261018-7ce297.web.app/demo.html",275.7),
      ("https://retailiq-free-20261018-7ce297.web.app/",258.9)]
    for url,y in links:
        para(c,f'<link href="{url}" color="#095f52">{escape(url)}</link>',273,y+10,419,8.8,max_height=16)
    card(c,28,219,664,155,"Submission access and scope",
         "The product base URL opens the live three-role workspace. Firebase Hosting routes requests to Cloud Run, Gemini and workspace-scoped Firestore.<br/><br/>Catalogue, customer figures and forecasts are synthetic. Proposed orders remain drafts for human approval.<br/><br/>The project video is managed separately; this release does not regenerate or revalidate demo media. Live model availability depends on free quota.",10.8)
    para(c,"Team RetailIQ — Abhishek Agarwal (team leader); Vivek Sharma (team member).",28,48,664,10.4,bold=True,color=GREEN,max_height=20)
    footer(c,13,"The template's original link prompts and '3 Minutes' label are preserved unchanged.")

DRAW=[slide_team,slide_idea,slide_opportunities,slide_features,slide_process,slide_wireframes,
      slide_architecture,slide_technologies,slide_cost,slide_snapshots,slide_benchmark,slide_future,slide_links]
def main():
    if not TEMPLATE.is_file(): raise FileNotFoundError(TEMPLATE)
    src=PdfReader(TEMPLATE); writer=PdfWriter(); records=[]
    for output,(source_index,draw) in enumerate(zip(SOURCE_INDICES,DRAW),1):
        stream=io.BytesIO(); overlay=canvas.Canvas(stream,pagesize=(720,405),pageCompression=1)
        draw(overlay);overlay.save();stream.seek(0)
        base=src.pages[source_index];base.merge_page(PdfReader(stream).pages[0])
        writer.add_page(base)
        records.append({"output_page":output,"original_page":source_index+1,"original_text_preserved":True})
    writer.add_metadata({"/Title":"RetailIQ — AI Builder Cup prescribed submission template","/Author":"Team RetailIQ: Abhishek Agarwal; Vivek Sharma","/Subject":"Original template pages filled with the solution; original artwork and prompts preserved"})
    with OUT.open("wb") as f: writer.write(f)
    assert OUT.stat().st_size<5_000_000
    result={"method":"Original PDF vector pages retained as underlay; blank-region overlays only",
            "template_sha256":hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(),
            "pages":len(records),"bytes":OUT.stat().st_size,"pdf_sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
            "omitted_original_pages":[2,15,16],"mapping":records}
    (ROOT/"tmp/prescribed-template-release.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result))
if __name__=="__main__": main()
