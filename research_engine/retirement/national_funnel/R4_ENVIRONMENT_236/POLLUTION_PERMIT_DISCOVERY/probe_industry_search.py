#!/usr/bin/env python3
"""Search official permit industry taxonomy for pollution-relevant categories."""
import json,http.cookiejar,pathlib,time
from datetime import datetime,timezone
from urllib.parse import urlencode
from urllib.request import Request,build_opener,HTTPCookieProcessor
BASE="https://permit.mee.gov.cn"
PAGE=BASE+"/perxxgkinfo/syssb/xkgg/xkgg!licenseInformation.action"
TREE=BASE+"/perxxgkinfo/common/tree/xzxk-common-trade!selectHylist.action?hyids=&hytype=more"
NODES=BASE+"/perxxgkinfo/common/tree/xzxk-common-trade!hynodeslist.action"
UA="Mozilla/5.0 (compatible; RetirementR4PublicEvidenceResearch/1.0)"
TERMS=["铜冶炼","铅锌冶炼","有色金属冶炼","磷肥制造","危险废物治理","污水处理及其再生利用",
"化学试剂和助剂制造","基础化学原料制造","化学农药制造","化学药品原料药制造","电镀","焦化",
"水泥制造","造纸","皮革鞣制加工","印染精加工","有色金属矿采选","黑色金属矿采选","非金属矿采选",
"石油加工","炼焦","钢铁冶炼","铅冶炼","锌冶炼","电池制造","垃圾焚烧","危险废物集中处置"]
def main():
 cj=http.cookiejar.CookieJar();op=build_opener(HTTPCookieProcessor(cj))
 def get(url,ref):
  q=Request(url,headers={"User-Agent":UA,"Accept":"text/html,*/*","Referer":ref})
  with op.open(q,timeout=45) as r:return r.read()
 get(PAGE,PAGE);get(TREE,PAGE)
 results=[]
 for term in TERMS:
  data=urlencode({"nodecode":"","name":term,"hyids":""}).encode()
  req=Request(NODES,data=data,headers={"User-Agent":UA,"Accept":"application/json,text/plain,*/*","Referer":TREE,"Origin":BASE,"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8","X-Requested-With":"XMLHttpRequest"})
  try:
   with op.open(req,timeout=30) as r:status=r.status;body=r.read().decode("utf-8","replace")
   parsed=json.loads(body)
   if isinstance(parsed,dict):items=parsed.get("data") or parsed.get("rows") or parsed.get("list") or [parsed]
   else:items=parsed
   if not isinstance(items,list):items=[items]
   results.append({"term":term,"status":status,"matches":items[:50],"count":len(items),"raw_preview":body[:300]})
  except Exception as e:results.append({"term":term,"error":repr(e)})
  time.sleep(.15)
 out={"schema":"MEE_PUBLIC_PERMIT_INDUSTRY_CATEGORY_SEARCH_V1","created_at_utc":datetime.now(timezone.utc).isoformat(),"terms":TERMS,"results":results}
 p=pathlib.Path("research_engine/retirement/national_funnel/R4_ENVIRONMENT_236/POLLUTION_PERMIT_DISCOVERY/output/industry_category_search.json")
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 compact=[]
 for x in results:
  matches=x.get("matches",[])
  compact.append({"term":x["term"],"count":x.get("count"),"matches":[{k:m.get(k) for k in ("id","name","pId","singlehyname","isParent")} for m in matches[:20] if isinstance(m,dict)],"error":x.get("error")})
 print("INDUSTRY_SEARCH",json.dumps(compact,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
