#!/usr/bin/env python3
"""Actually download official MEE 2025-12 full air-quality city monthly report PDF
and inspect PDF text/table structure. THIS IS SOURCE QA, NOT county coverage.
No invented city values; not county or residential criteria.
"""
import datetime,hashlib,json,pathlib,re,urllib.request
from pypdf import PdfReader
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
URL="https://www.mee.gov.cn/hjzl/dqhj/cskqzlzkyb/202601/W020260130583204381295.pdf"
out={"schema":"RET_MEE_OFFICIAL_2025_12_CITY_AIR_PDF_REAL_STRUCTURE_V1",
"attempted_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"source_URL":URL,"source_level":"Chinese Ministry of Ecology and Environment city-level air monthly report, not county or dwelling",
"source_document_year":2025,"official_2026_current_county_roster_verified":False,
"formal_valid_county_screenings":0,"status":"SOURCE_NOT_YET_VERIFIED"}
try:
 request=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 (compatible; research-qa/1.0)","Accept":"application/pdf"})
 with urllib.request.urlopen(request,timeout=160) as r:b=r.read(32_000_001)
 if not b.startswith(b"%PDF-"):raise RuntimeError("Official PDF URL did not return PDF bytes")
 if len(b)>32_000_000:raise RuntimeError("Official PDF too large to safely inspect")
 p=OUT/"MEE_2025_12_monthly_city_air_quality_official_original.pdf";p.write_bytes(b)
 reader=PdfReader(str(p))
 out.update({"pdf_file_length_bytes":len(b),"pdf_sha256":hashlib.sha256(b).hexdigest(),"page_count":len(reader.pages)})
 matches=[];samples=[];scanned=[];totalchars=0
 for i,page in enumerate(reader.pages):
  try:t=page.extract_text(extraction_mode="layout") or ""
  except Exception:t=page.extract_text() or ""
  totalchars+=len(t)
  if len(t.strip())<80:scanned.append(i+1)
  flags=[k for k in ["2025年","2025 年","城市","附表","年均","PM2.5","PM₂.₅","O3","O₃","臭氧","1—12月","1-12月"] if k in t]
  if flags:
   matches.append({"page":i+1,"characters":len(t),"keywords":flags,
    "line_count":len(t.splitlines())})
  if any(x in t for x in ["附表","168个","城市空气质量"]) or (len(t)>1600 and ("PM" in t or "O3" in t)):
   s=t.splitlines()
   sample=[line.strip() for line in s if line.strip()][:45]
   samples.append({"page":i+1,"representative_text_lines":sample[:24]})
 out.update({"total_extracted_characters":totalchars,"textually_sparse_pages":scanned,
 "keyword_page_count":len(matches),"keyword_pages":matches,
 "potential_table_page_samples":samples[:14],
 "status":"OFFICIAL_PDF_DOWNLOADED_TEXT_SCHEMA_REVIEW" if totalchars>4000 else "OFFICIAL_PDF_DOWNLOADED_TEXT_UNAVAILABLE"})
except Exception as exc:
 out.update({"status":"OFFICIAL_PDF_ACCESS_OR_TEXT_ERROR","actual_error":repr(exc)})
 print("ACTUAL_MEE_PDF_ERROR",repr(exc),flush=True)
(OUT/"MEE_2025_official_city_air_PDF_structure_QA.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:out.get(k) for k in ["status","pdf_file_length_bytes","page_count","total_extracted_characters","textually_sparse_pages","keyword_page_count","actual_error"]},ensure_ascii=False),flush=True)
