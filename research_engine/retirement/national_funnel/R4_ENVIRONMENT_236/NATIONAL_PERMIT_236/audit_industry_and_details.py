#!/usr/bin/env python3
"""Forensic read-only audit of low-yield official permit scan."""
import csv,json,pathlib,re,urllib.request,urllib.parse,http.cookiejar
from datetime import datetime,timezone
ROOT=pathlib.Path("research_engine/retirement/national_funnel/R4_ENVIRONMENT_236/NATIONAL_PERMIT_236")
DATA=ROOT/"output/runs/42466352739/NATIONAL_236_PERMIT_FACILITY_DETAIL_SAMPLE.csv"
BASE="https://permit.mee.gov.cn"
PAGE=BASE+"/perxxgkinfo/syssb/xkgg/xkgg!licenseInformation.action"
UA="Mozilla/5.0 (compatible; R4National236PublicEnvironmentalEvidence/1.0)"
def request(op,url,form=None):
 data=urllib.parse.urlencode(form).encode() if form else None
 headers={"User-Agent":UA,"Referer":PAGE,"Accept":"text/html,application/json,*/*"}
 if data:headers["Content-Type"]="application/x-www-form-urlencoded; charset=UTF-8"
 with op.open(urllib.request.Request(url,data=data,headers=headers),timeout=50) as r:return r.read(3000000).decode("utf-8","replace")
def main():
 jar=http.cookiejar.CookieJar();op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
 result={"schema":"MEE_236_INDUSTRIAL_SCAN_FORENSIC_V1","created_at_utc":datetime.now(timezone.utc).isoformat(),"pages":[],"targeted_queries":[]}
 with DATA.open(encoding="utf-8-sig",newline="") as f:old=list(csv.DictReader(f))
 listing=request(op,PAGE)
 m=re.search(r'name="tempReportKey"[^>]*value="([^"]+)"',listing)
 token=m.group(1) if m else ""
 for row in old[:8]:
  try:
   body=request(op,row["detail_url"])
   title=re.findall(r"<title[^>]*>(.*?)</title>",body,re.I|re.S)[:1]
   substr=lambda w:body.find(w)
   coords=re.findall(r'<input[^>]+(?:id="longitude"|id="latitude")[^>]*>',body,re.I)
   result["pages"].append({"permit_no":row["permit_no"],"company":row["company"],"bytes":len(body),"title":title,
    "longitude_token_offset":substr("longitude"),"latitude_token_offset":substr("latitude"),
    "company_offset":substr(row["company"]),"permit_no_offset":substr(row["permit_no"]),
    "coords_input_tags":coords[:10],
    "contains_production_address":"生产经营场所地址" in body,
    "prefix_html":body[:3500],
    "longitude_snippet":body[max(0,substr("longitude")-300):substr("longitude")+900] if substr("longitude")>=0 else ""})
  except Exception as e:result["pages"].append({"company":row["company"],"error":repr(e)})
 for citycode,cityname,pcode,ccode in [
  ("5301","昆明市","530000000000","530100000000"),
  ("3302","宁波市","330000000000","330200000000"),
  ("3505","泉州市","350000000000","350500000000")]:
  for code,label in [("C3211","铜冶炼"),("N7724","危险废物治理"),("C2614","有机化学原料制造")]:
   form={"page.pageNo":"1","page.orderBy":"","page.order":"","tempReportKey":token,
    "registerentername":"","xkznum":"","treadname":label,"treadcode":code,"publishtime":"",
    "province":pcode,"city":ccode,"management":""}
   try:
    body=request(op,PAGE,form)
    pages=re.findall(r"共\s*([\d,]+)\s*页",body)
    ids=re.findall(r'getxxgkContent&dataid=([0-9a-f]{32})',body)
    result["targeted_queries"].append({"city":cityname,"industry_code":code,"industry_label":label,
     "pages":pages[-1] if pages else None,"record_links":len(ids),"sample_names":re.findall(r"<td[^>]*>\s*([^<]*有限公司[^<]*)\s*</td>",body)[:5]})
   except Exception as e:result["targeted_queries"].append({"city":cityname,"industry_code":code,"error":repr(e)})
 path=ROOT/"output/AUDIT_INDUSTRIAL_SCAN_42466352739.json"
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("AUDIT",json.dumps({"pages":[{k:v for k,v in p.items() if k in ("permit_no","company","bytes","title","longitude_token_offset","latitude_token_offset","contains_production_address","error")} for p in result["pages"]],"targeted_queries":result["targeted_queries"]},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
