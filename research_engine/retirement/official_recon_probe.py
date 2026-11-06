#!/usr/bin/env python3
"""Source-verified official administration API probe and independent archival mirror audit.

Official data: dmfw.mca.gov.cn (public national place-name database), requested 2025 code release.
Mirror: community-maintained wujingke/division_codes, never promoted to official direct evidence.
The results are ADMINISTRATIVE-IDENTITY ONLY; no climate suitability decisions.
"""
import csv,datetime,hashlib,io,json,pathlib,time,urllib.error,urllib.parse,urllib.request
P=pathlib.Path("research_engine/retirement/output");P.mkdir(parents=True,exist_ok=True)
OFFICIAL="https://dmfw.mca.gov.cn/9095/xzqh/getList"
MIRROR="https://raw.githubusercontent.com/wujingke/division_codes/main/output/"
ARCHIVE=pathlib.Path("retirement-climate-pilot/status/latest-adcode-probe.json")
RESULT=pathlib.Path("research_engine/retirement/output/official_probe.json")
def get(url,timeout=100):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; ResearchEvidenceAudit/1.0)","Accept":"application/json,text/csv,*/*"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        b=response.read()
        return b,dict(response.headers),response.status
def digest(b):return hashlib.sha256(b).hexdigest()
def walk(obj,path=""):
    if isinstance(obj,dict):
        if "name" in obj and "code" in obj:yield (path,str(obj.get("name")),str(obj.get("code")))
        for k,v in obj.items():
            if isinstance(v,(list,dict)):yield from walk(v,path+"/"+k)
    elif isinstance(obj,list):
        for i,item in enumerate(obj):yield from walk(item,path+"/"+str(i))
def as_six(raw):
    s=str(raw).strip()
    if len(s)>=6 and s[:6].isdigit():return s[:6]
    return None
def candidates(rows):
    by={}
    for path,name,raw in rows:
        code=as_six(raw)
        if code and code[:2] in ("11","12","13","14","15","21","22","23","31","32","33","34","35","36","37","41","42","43","44","45","46","50","51","52","53","54","61","62","63","64","65") and code[-2:]!="00":
            by.setdefault(code,[]).append({"name":name,"source_path":path,"raw_code":raw})
    return by
report={"generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "active_action":"RET-OFFICIAL-RECON-001","official_api_url":OFFICIAL,
        "status":"PENDING","valid_county_screenings":0,"official_code_verified":0,
        "county_climate_verified":0,
        "official_source_method":"live government HTTP GET requested 2025 annual edition",
        "warning":"A code identity is not a weather representativeness judgement, and does not mean a valid county screening."}
archive=json.loads(ARCHIVE.read_text(encoding="utf-8"))
expected=[{"site":e["site"],"name":e["archival_county_chinese"],"code":e["candidate_code"]} for e in archive["candidate_links"]]
report["expected_archival_candidates"]=len(expected)
official_rows=[]
attempts=[]
for code in ("","460000000000","530000000000"):
    params={"code":code,"maxLevel":3,"year":2025}
    url=OFFICIAL+"?"+urllib.parse.urlencode(params)
    record={"url":url}
    try:
        b,headers,status=get(url)
        record.update({"http_status":status,"raw_bytes":len(b),"sha256":digest(b),"content_type":headers.get("Content-Type")})
        result=json.loads(b)
        record.update({"json_top_keys":list(result) if isinstance(result,dict) else ["ROOT_LIST"],"node_sample":list(walk(result))[:6],"node_count":sum(1 for _ in walk(result))})
        if not code and record["node_count"]>2800:
            (P/"official_2025_raw.json").write_bytes(b)
            official_rows=list(walk(result))
            record["usable_full_coverage"]=True
        else:
            record["usable_full_coverage"]=False
            if code: (P/("official_"+code[:2]+"_raw.json")).write_bytes(b)
    except Exception as e:
        record["error"]=repr(e)
    attempts.append(record)
    # Do not request more from public service after full nationwide data is obtained
    if official_rows:break
    time.sleep(1)
report["official_attempts"]=attempts
report["official_response_received"]=sum(a.get("http_status")==200 for a in attempts)
if official_rows:
    cs=candidates(official_rows)
    report["official_records_with_name_and_code"]=len(official_rows)
    report["six_digit_county_like_keys"]=len(cs)
    details=[]
    for e in expected:
        cand=cs.get(e["code"],[])
        details.append({**e,"official_exact_matches":[c for c in cand if c["name"]==e["name"]],
                        "official_code_candidates":cand[:5],
                        "identity_status":"EXACT_CODE_AND_NAME" if any(c["name"]==e["name"] for c in cand) else "MISMATCH_OR_MISSING"})
    report["official_12_site_checks"]=details
    report["official_12_exact_matches"]=sum(d["identity_status"]=="EXACT_CODE_AND_NAME" for d in details)
    report["official_code_verified"]=report["official_12_exact_matches"]
    report["status"]="PASS_OFFICIAL_DIRECT" if report["official_12_exact_matches"]==12 else "PARTIAL_OFFICIAL_DIRECT"
else:
    report["status"]="OFFICIAL_DIRECT_UNAVAILABLE"
# Independent comparison, never substitute for official direct data
try:
    b,h,st=get(MIRROR+"meta/summary.json",timeout=40)
    meta=json.loads(b)
    report["mirror_summary"]={"source_url":MIRROR+"meta/summary.json","sha256":digest(b),"raw_bytes":len(b),"data":meta}
except Exception as e:
    report["mirror_error"]=repr(e)
RESULT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in report.items() if k not in ("official_12_site_checks","official_attempts")},ensure_ascii=False))
print("official_attempts",json.dumps(attempts,ensure_ascii=False))
if report["status"]=="OFFICIAL_DIRECT_UNAVAILABLE":raise SystemExit(2)
if report["status"]!="PASS_OFFICIAL_DIRECT":raise SystemExit(3)
