"""Verify original-template preservation and render local review images."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tmp/pdf-template-tools"))
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import ImageChops
source=ROOT/"submission/AI_Builder_Cup_Original_Template.pdf"
final=ROOT/"pitch-slides.pdf"
mapping=[0,2,3,4,5,6,7,8,9,10,11,12,13]
a,b=PdfReader(source),PdfReader(final)
ra,rb=pdfium.PdfDocument(source),pdfium.PdfDocument(final)
assert len(b.pages)==13
checks=[]
out=ROOT/"tmp/prescribed-template-qa";out.mkdir(parents=True,exist_ok=True)
normal=lambda s: re.sub(r"\s+"," ",s).strip()
for i,j in enumerate(mapping):
    original=ra[j].render(scale=1.5).to_pil().convert("RGB")
    result=rb[i].render(scale=1.5).to_pil().convert("RGB")
    crop_h=405 if i==0 else 120
    identical=ImageChops.difference(original.crop((0,0,1080,crop_h)),result.crop((0,0,1080,crop_h))).getbbox() is None
    prompts=normal(a.pages[j].extract_text()) in normal(b.pages[i].extract_text())
    assert identical,(i+1,"Original header artwork changed")
    assert prompts,(i+1,"Original prompt text changed")
    assert tuple(float(x) for x in b.pages[i].mediabox[2:])==(720.0,405.0)
    checks.append({"page":i+1,"original_page":j+1,"original_header_and_title_pixels_identical":identical,"all_original_prompt_text_preserved":prompts})
    if i+1 in (1,3,5,7,8,9,10,11,13):result.save(out/f"page-{i+1:02}.png")
text="\n".join(p.extract_text() for p in b.pages)
for item in ("RetailIQ","Abhishek Agarwal","Vivek Sharma","Firebase Hosting","Cloud Run","Firestore","Gemini 3.5 Flash-Lite","synthetic","Guardrails","human drafts"):
    assert item.lower() in text.lower(),item
assert final.stat().st_size<5_000_000
proof={"passed":True,"method":"Original PDF vector underlays; original headings, prompts, logos and page geometry retained","original_template_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"final_pdf_sha256":hashlib.sha256(final.read_bytes()).hexdigest(),"pages":13,"bytes":final.stat().st_size,"omitted_original_pages":[2,15,16],"checks":checks,"limit_bytes":5000000}
(ROOT/"submission/evidence/prescribed-template-verification.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"passed":True,"pages":13,"bytes":proof["bytes"],"pdf_sha256":proof["final_pdf_sha256"],"header_pixel_checks":13,"prompt_checks":13}))
