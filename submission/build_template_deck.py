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
def footer(c,number,note="Synthetic commercial context. Current free prototype is clearly labelled."):
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
        ("Field representative","Shelf photo/video analysis; own-brand audit and separate competitor benchmark.<br/><br/>Guided counts, stock discrepancy checks and forecast-aware proposed orders.<br/><br/>Source-linked pitch, buyer rehearsal and structured debrief."),
        ("Manager and buyer","Saved audits and proposed orders with originating visit context.<br/><br/>Revenue, forecasts, inventory alerts and segment reference views.<br/><br/>Optional private evidence in backend mode; human commercial approval."),
        ("Shopper","Conversational catalogue discovery by need, preference and basket context.<br/><br/>Compare product stock, price and nutrition.<br/><br/>Synthetic figures are labelled; recorded mode requires no model key.")]
    for x,(title,text) in zip((28,256,484),groups): card(c,x,308,208,239,title,text,11)
    footer(c,4,"Static events save in the browser. Configured backend persistence is a separate profile.")
def slide_process(c):
    xs=[28,198,368,538]; w=154; h=94; top=308
    nodes=[("01 Capture","Shelf photo or selected frames"),
           ("02 Qualify","Visibility verdicts and human-confirmed counts"),
           ("03 Verify","Compare system stock and inbound quantities"),
           ("04 Choose action","Reconcile/fill shelf or justify replenishment")]
    for x,(t,d) in zip(xs,nodes): card(c,x,top,w,h,t,escape(d),10.3)
    for x in xs[:-1]: arrow(c,x+w,top-h/2,x+170,top-h/2)
    arrow(c,615,214,615,184)
    bottom=[("08 Review","Manager inspects evidence and follows up"),
            ("07 Save","Audit, proposed action and visit debrief"),
            ("06 Human control","Rep/buyer validate the draft and commercial terms"),
            ("05 Prepare","Inspect cited facts and rehearse the conversation")]
    for x,(t,d) in zip(xs,bottom): card(c,x,184,w,h,t,escape(d),10.3)
    for x in xs[:-1]: arrow(c,x+170,137,x+w,137)
    para(c,"Decision branch: empty shelf + positive recorded stock → locate and reconcile first. Verified replenishment need → demand minus usable stock and inbound, bounded by case size and shelf life.",28,70,664,10.2,max_height=33)
    footer(c,5,"A proposed order remains a draft; no automatic ERP placement is claimed.")
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
    para(c,"CURRENT PUBLIC PROFILE",28,309,240,10,bold=True,color=GREEN,max_height=20)
    card(c,28,283,228,69,"Firebase Spark","Unbilled hosting; billing disabled.",10.5)
    arrow(c,142,214,142,197)
    card(c,28,195,228,69,"RetailIQ browser","Recorded mode; local event storage.",10.5)
    arrow(c,142,126,142,109)
    card(c,28,107,228,65,"Optional AI Studio","Confirmed unbilled key; quota stop.",10)
    para(c,"IMPLEMENTED BACKEND REFERENCE",289,309,403,10,bold=True,color=GREEN,max_height=20)
    card(c,289,283,403,62,"Cloud Run / FastAPI","Authenticated API; bounded requests and validated contracts.",10)
    for x,title,text in [
        (289,"Gemini on Vertex AI","Backend text + shelf vision"),
        (498,"BigQuery / BQML","Analytics, retrieval, forecasts")]:
        card(c,x,196,194,62,title,escape(text),10.2)
    for x,title,text in [
        (289,"Firestore","Visit events + review metadata"),
        (498,"Cloud Storage","Optional private shelf evidence")]:
        card(c,x,116,194,62,title,escape(text),10.2)
    arrow(c,490,221,490,208); arrow(c,490,208,386,208);arrow(c,490,208,595,208)
    arrow(c,386,208,386,196);arrow(c,595,208,595,196)
    para(c,"Reference backend was historically verified; its retired endpoint is not the current static host.",289,44,403,8.3,max_height=15)
    footer(c,7,"Model credentials stay off the browser in backend mode. Private IAM is the backend default.")
def slide_technologies(c):
    rows=[
      ["Firebase Hosting (Spark)","Public static app and video","Current host; project billing disabled"],
      ["HTML / CSS / JavaScript","Rep, manager and shopper UI","Current browser application"],
      ["Gemini / AI Studio","Optional direct text and vision","Unbilled-key confirmation; quota stop"],
      ["Cloud Run / FastAPI","Authenticated application API","Implemented backend reference"],
      ["Gemini on Vertex AI","Backend model inference","Historical 3.6 Flash reference evaluated"],
      ["BigQuery / BigQuery ML","Analytics, retrieval, ARIMA forecasts","Synthetic history and holdout checked"],
      ["Firestore","Saved visit events and review metadata","Implemented backend persistence"],
      ["Cloud Storage / Secret Manager","Private evidence / credentials","Implemented backend safeguards"],
      ["Playwright / pytest / CI","Software and evaluator regressions","Local checks and workflow supplied"]]
    table(c,rows,[168,258,238],308,["Technology","Purpose","Actual status"],9.3,row_h=26)
    footer(c,8,"No usage of Vertex AI Search, Looker, AlloyDB or Cloud SQL is claimed.")
def slide_cost(c):
    para(c,"Current prototype: Firebase Spark project billing is disabled; recorded mode makes no AI calls. Optional company services are metered and consume credits.",28,309,664,11.6,max_height=44)
    rows=[
      ["10 reps × 6 visits/day × 22 days","1,320 visits / month"],
      ["Assumed 12-minute baseline → 5-minute scoped-task target","7 minutes / visit"],
      ["1,320 × 7 / 60","154 hours released capacity"],
      ["154 hours × assumed INR 300 / hour","INR 46,200 capacity value"],
      ["Target operating budget: INR 5 × 1,320 visits","INR 6,600 / month"],
      ["Illustrative capacity value less operating target","INR 39,600 / month"]]
    table(c,rows,[470,194],248,["Editable planning assumption","Scenario value"],10.2,row_h=27)
    para(c,"Implementation estimate: integration, training and device scope require discovery; no engineering cost is invented. The scenario is not measured ROI or guaranteed cash saving. The operating budget is a target, not an invoice.",28,53,664,9.1,max_height=30)
    footer(c,9,"Scope: audit preparation and debrief administration, not the entire store visit.")
def slide_snapshots(c):
    images=[
      ("prototype-shelf-gap.png","Field rep: confirm the shelf-stock mismatch","Actual prototype; synthetic zero facings versus 64 recorded units. Human stock verification precedes a new purchase."),
      ("prototype-manager.png","Manager: review context and saved events","Actual prototype; synthetic KPIs and team figures. Current free-host events remain in the browser.")]
    for x,(name,title,caption) in zip((28,370),images):
        box(c,x,59,322,249,white)
        c.drawImage(ImageReader(str(ROOT/"assets/submission"/name)),x+7,105,width=308,height=196,preserveAspectRatio=True,anchor="c",mask="auto")
        para(c,escape(title),x+9,99,304,10.3,bold=True,color=GREEN,max_height=26)
        para(c,escape(caption),x+9,74,304,8.3,max_height=27)
    footer(c,10,"Real application screenshots; commercial figures and actors are synthetic demo context.")
def slide_benchmark(c):
    rows=[
      ["Current public host","18 HTTP/browser checks passed","Hashes, private paths, mobile fit; no AI calls"],
      ["Public video player","6 checks; native browser playback","222.44-second playable MP4; no AI/backend calls"],
      ["Browser / policy","157 + 7 checks passed","Exercised UI contracts; mocked backend responses"],
      ["Python regressions","60 checks passed","51 API + 4 deploy doubles + 5 free-host guards"],
      ["Offline evaluator","38 deterministic assertions","Facts and corrupt-response rejection; no model calls"],
      ["Historical live model","10/10 synthetic cases","Vertex Gemini 3.6 Flash; not current free-model proof"],
      ["Historical cloud","22 deployed checks passed","Warehouse, events, private photo; endpoint retired"],
      ["Synthetic forecast","WAPE 1.249% vs baseline 2.824%","7-day generated holdout; not real-store accuracy"]]
    table(c,rows,[136,215,313],308,["Area","Result / baseline","What the result establishes"],9.3,row_h=29)
    para(c,"Credential-free reports: submission/evidence/. No achieved sales uplift, production forecast accuracy, visual-counting precision or measured operating cost is claimed.",28,40,664,8.3,max_height=17)
    footer(c,11,"Local software checks, historical model results and real business impact are separate claims.")
def slide_future(c):
    card(c,28,308,322,237,"Proposed development",
         "1. Replace generated data with permissioned POS, stock and inbound feeds.<br/><br/>2. Independently label shelf evidence and measure precision, coverage and abstention.<br/><br/>3. Add approved enterprise identity and ERP draft-order handoffs.<br/><br/>4. Evaluate the chosen current model and establish cost/latency under representative usage.",11)
    card(c,370,308,322,237,"Falsifiable pilot",
         "Compare a two-week baseline with an assisted period.<br/><br/>Test the five-minute target for scoped audit/debrief work. Measure corrections and productive reuse of time.<br/><br/>Track stock discrepancy closure, source-supported claims, order waste risk, latency and cost per completed workflow.",11)
    footer(c,12,"Roadmap and pilot targets only. No achieved revenue uplift or stockout reduction is claimed.")
def slide_links(c):
    # Original three link labels remain visible; URLs fill the space beside them.
    links=[
      ("https://github.com/abhishek-0706/AI-BUILDER-CUP-2026",292.5),
      ("https://retailiq-free-20261018-7ce297.web.app/demo.html",275.7),
      ("https://retailiq-free-20261018-7ce297.web.app/?demo=recorded",258.9)]
    for url,y in links:
        para(c,f'<link href="{url}" color="#095f52">{escape(url)}</link>',273,y+10,419,8.8,max_height=16)
    card(c,28,219,664,155,"Submission access and scope",
         "Public source, product and Google-hosted video links are verified without authentication.<br/><br/>Video: 3:42.44, meeting the online form's 3–4-minute range; AI-assisted narration from the creator-provided voice sample. The walkthrough is recorded with synthetic commercial context.<br/><br/>Current public product: Firebase Spark, project billing disabled, browser-local saves. A no-key recorded visit requires no model request.",10.8)
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
