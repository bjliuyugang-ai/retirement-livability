#!/usr/bin/env python3
"""Fetch third-party 2025 IPE/Blue Map aggregated Chinese city pollutant PDF.
Inspect REAL selectable text and table rows before any R4 county proxy join.
Source caveat: derived monitoring-city data, explicitly not formally audited.
"""
import datetime,hashlib,json,pathlib,urllib.request
from pypdf import PdfReader
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
URL="https://pdf.dfcfw.com/pdf/H3_AP202601071816825617_1.pdf?1767856554000.pdf="
out={"schema":"RET_R4_SECONDARY_2025_CHINA_CITY_PM25_O3_RAW_PDF_ACCESS_QA_V1",
 "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_url":URL,"source_descriptor":"IPE Blue Map published '2025 年1-12月城市空气质量状况' hosted at dfcfw",
 "published_data_caveat":"城市空气质量统计基于环境监测日均值分析，参考沙尘剔除规则，未经有效性审核，仅供参考；准确结果以生态环境部门发布为准",
 "report_year":2025,"not_official_reviewed":True,
 "formal_valid_county_screenings":0}
try:
 request=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0","Accept":"application/pdf"})
 with urllib.request.urlopen(request,timeout=100) as response:b=response.read(19_000_001)
 if not b.startswith(b"%PDF"):raise RuntimeError("Response not PDF")
 if len(b)>19_000_000:raise RuntimeError("Response exceeds safe source QA cap")
 p=OUT/"IPE_BlueMap_2025_city_air_pollution_original.pdf";p.write_bytes(b)
 doc=PdfReader(str(p))
 summaries=[];total=0;rowlike=0
 for i,page in enumerate(doc.pages):
  t=page.extract_text(extraction_mode="layout") or ""
  total+=len(t)
  ls=[z.strip() for z in t.splitlines() if z.strip()]
  tablels=[z for z in ls if (("城市" in z or "省区市" in z or "PM" in z or "μg" in z) or (sum(ch.isdigit() for ch in z)>10 and len(z)<170))]
  rowlike+=len(tablels)
  summaries.append({"page":i+1,"page_chars":len(t),"line_count":len(ls),
   "likely_table_row_lines":len(tablels),"sample_lines":ls[:10],
   "table_sample_lines":tablels[:9]})
 out.update({"raw_pdf_bytes":len(b),"raw_pdf_sha256":hashlib.sha256(b).hexdigest(),
  "pages":len(doc.pages),"extracted_text_characters":total,
  "rowlike_lines":rowlike,"page_summaries":summaries,
  "status":"REAL_SECONDARY_PDF_TEXT_EXTRACTED" if total>15000 and rowlike>80 else "REAL_SECONDARY_PDF_TEXT_INSUFFICIENT"})
except Exception as exc:
 out.update({"status":"SECONDARY_PDF_DOWNLOAD_FAILED","actual_error":repr(exc)})
 print("SECONDARY_CITY_AIR_REAL_ERROR",repr(exc),flush=True)
(OUT/"IPE_2025_city_air_source_structure_QA.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:out.get(k) for k in ["status","raw_pdf_bytes","pages","extracted_text_characters","rowlike_lines","actual_error"]},ensure_ascii=False),flush=True)
