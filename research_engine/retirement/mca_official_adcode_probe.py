#!/usr/bin/env python3
"""Probe Ministry of Civil Affairs National Geographic Name Database 2025/26
official administrative division code endpoint, without claiming access until
actual HTTP response and schema are verified. Fallback provenance is separate.
"""
import datetime,hashlib,json,pathlib,urllib.error,urllib.request
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
url="https://dmfw.mca.gov.cn/9095/xzqh/getList?code=&maxLevel=3"
out={"schema":"RET_MCA_OFFICIAL_XZQH_API_REAL_ACCESS_QA_V1",
 "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "url":url,"source_owner":"中华人民共和国民政部 国家地名信息库",
 "asof_date_verified":False,"official_county_code_records_extracted":0,
 "source_status":"NOT_ATTEMPTED",
 "claims_forbidden":["HTTP 200 alone does not certify 2026 county roster", "Nested admin units may include province/city/county level and direct-admin counties",
 "If a source is blocked, third-party mirrors remain unofficial"]}
try:
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; research-source-qa/1.0)","Accept":"application/json,text/plain,*/*","Referer":"https://dmfw.mca.gov.cn/XzqhVersionPublish.html"})
 with urllib.request.urlopen(req,timeout=55) as r:
  raw=r.read(25_000_000);status=r.status;headers={k:v for k,v in r.headers.items() if k.lower() in ("content-type","last-modified","content-length")}
 out.update({"http_status":status,"response_headers":headers,"response_byte_count":len(raw),
             "response_sha256":hashlib.sha256(raw).hexdigest(),"source_status":"HTTP_RESPONDED"})
 (OUT/"mca_official_api_response_raw.json").write_bytes(raw)
 try:
  j=json.loads(raw)
  out["json_root_type"]=type(j).__name__
  out["json_root_keys"]=list(j.keys())[:30] if isinstance(j,dict) else []
  out["json_top_level_preview"]=json.dumps(j,ensure_ascii=False)[:2400]
  # structural preflight only; leave full parsing to separate run when schema known
  out["source_status"]="OFFICIAL_HTTP_JSON_RETURNED_NEEDS_LEVEL_DATE_QA"
 except Exception as ex:
  out["json_error"]=repr(ex);out["response_preview"]=raw[:600].decode("utf-8","replace")
  out["source_status"]="HTTP_NONJSON_OR_PORTAL_GATE"
except Exception as ex:
 out.update({"source_status":"OFFICIAL_API_BLOCKED_WITH_REAL_ERROR","error":repr(ex)})
 print("MCA_OFFICIAL_API_ACTUAL_ERROR",repr(ex),flush=True)
(OUT/"mca_official_api_real_access_QA.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:out.get(k) for k in ["source_status","http_status","response_byte_count","json_root_type","json_root_keys","error"]},ensure_ascii=False),flush=True)
