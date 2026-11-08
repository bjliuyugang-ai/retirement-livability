#!/usr/bin/env python3
"""One small, read-only POST probe against the official MEE permit search."""
import json,re,http.cookiejar
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urlencode,urljoin
from urllib.request import Request,build_opener,HTTPCookieProcessor

BASE="https://permit.mee.gov.cn"
PAGE=BASE+"/perxxgkinfo/syssb/xkgg/xkgg!licenseInformation.action"
REGION=BASE+"/perxxgkinfo/syssb/xkgg/xkgg!getRegions.action"
UA="Mozilla/5.0 (compatible; RetirementR4PublicEvidenceResearch/1.0)"
class Parser(HTMLParser):
 def __init__(self):
  super().__init__(); self.inputs={};self.rows=[];self.row=None;self.in_td=False;self.current_td="";self.links=[];self.current_link=None
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if t=="input" and a.get("name"):self.inputs[a["name"]]=a.get("value","")
  if t=="tr":self.row={"cells":[],"links":[]}
  if t=="td" and self.row is not None:self.in_td=True;self.current_td=""
  if t=="a" and self.row is not None:self.current_link={"href":a.get("href"),"onclick":a.get("onclick"),"text":""}
 def handle_data(self,d):
  if self.in_td:self.current_td+=d.strip()
  if self.current_link:self.current_link["text"]+=d.strip()
 def handle_endtag(self,t):
  if t=="td" and self.row is not None:
   self.row["cells"].append(self.current_td);self.in_td=False;self.current_td=""
  if t=="a" and self.current_link is not None:
   self.row["links"].append(self.current_link);self.current_link=None
  if t=="tr" and self.row is not None:
   if self.row["cells"]:self.rows.append(self.row)
   self.row=None
def main():
 cj=http.cookiejar.CookieJar();op=build_opener(HTTPCookieProcessor(cj))
 def req(url,data=None,referer=PAGE):
  b=None if data is None else urlencode(data).encode()
  h={"User-Agent":UA,"Accept":"text/html,application/json,*/*","Accept-Language":"zh-CN,zh;q=0.9","Referer":referer,"Origin":BASE}
  if b is not None:h["Content-Type"]="application/x-www-form-urlencoded; charset=UTF-8"
  with op.open(Request(url,data=b,headers=h),timeout=45) as r:return r.status,r.geturl(),r.headers.get("Content-Type"),r.read().decode("utf-8","replace")
 result={"schema":"MEE_PERMIT_READ_ONLY_QUERY_PROBE_V1","created_at_utc":datetime.now(timezone.utc).isoformat(),"credentials_used":False,"write_actions":False}
 status,final,ct,html=req(PAGE)
 parser=Parser();parser.feed(html)
 result["initial_page"]={"status":status,"url":final,"content_type":ct,"bytes":len(html),"hidden_fields":{k:v for k,v in parser.inputs.items() if k in ("page.pageNo","page.orderBy","page.order","tempReportKey")}}
 # Fetch official province and city region lists using the public endpoint used by the page.
 rs,ru,rct,rb=req(REGION,{"parentCode":"000000000000"})
 try: provinces=json.loads(rb).get("regions",[])
 except Exception: provinces=[]
 result["province_endpoint"]={"status":rs,"url":ru,"content_type":rct,"count":len(provinces),"sample":provinces[:8]}
 yunnan=next((x for x in provinces if "云南" in x.get("regionname","")),None)
 result["target_province"]=yunnan
 if not yunnan:
  result["error"]="Could not resolve Yunnan province code from public region endpoint."
 else:
  cs,cu,cct,cb=req(REGION,{"parentCode":yunnan["regioncode"]})
  try:cities=json.loads(cb).get("regions",[])
  except Exception:cities=[]
  result["cities"]={"status":cs,"count":len(cities),"items":cities}
  kunming=next((x for x in cities if "昆明" in x.get("regionname","")),None)
  result["target_city"]=kunming
  if kunming:
   fields={
    "page.pageNo":"1","page.orderBy":"","page.order":"",
    "tempReportKey":parser.inputs.get("tempReportKey",""),
    "registerentername":"","xkznum":"","treadname":"","treadcode":"",
    "publishtime":"","province":yunnan["regioncode"],
    "city":kunming["regioncode"],"management":""
   }
   qs,qu,qct,qhtml=req(PAGE,fields)
   qparser=Parser();qparser.feed(qhtml)
   pages=re.findall(r"共\s*([\d,]+)\s*页",qhtml)
   result["kunming_query"]={"status":qs,"url":qu,"content_type":qct,"bytes":len(qhtml),
    "page_count_text":pages[:3],"parsed_table_rows":len(qparser.rows),
    "sample_rows":qparser.rows[:12],
    "result_markers":re.findall(r"(?:共|当前第|条记录|没有符合|暂无)[^<]{0,50}",qhtml)[:20],
    "contains_license_rows":bool(re.search(r"xkznum|许可证编号|排污许可证",qhtml))}
   # Save raw first page for independent parsing/replay.
   out="research_engine/retirement/national_funnel/R4_ENVIRONMENT_236/POLLUTION_PERMIT_DISCOVERY/output/kunming_query_page1.html"
   import pathlib
   p=pathlib.Path(out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(qhtml,encoding="utf-8")
  else:result["error"]="Yunnan resolved, but Kunming city code not found."
 outj="research_engine/retirement/national_funnel/R4_ENVIRONMENT_236/POLLUTION_PERMIT_DISCOVERY/output/permit_search_probe.json"
 import pathlib
 p=pathlib.Path(outj);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("QUERY_PROBE",json.dumps({k:result.get(k) for k in ("province_endpoint","target_province","cities","target_city","kunming_query","error")},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
