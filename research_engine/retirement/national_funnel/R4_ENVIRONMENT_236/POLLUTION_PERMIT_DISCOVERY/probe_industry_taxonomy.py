#!/usr/bin/env python3
"""Read-only discovery of the MEE public permit portal industry-category selector."""
import json,re,http.cookiejar,pathlib
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.request import Request,build_opener,HTTPCookieProcessor
BASE="https://permit.mee.gov.cn"
PAGE=BASE+"/perxxgkinfo/syssb/xkgg/xkgg!licenseInformation.action"
TREE=BASE+"/perxxgkinfo/common/tree/xzxk-common-trade!selectHylist.action?hyids=&hytype=more"
UA="Mozilla/5.0 (compatible; RetirementR4PublicEvidenceResearch/1.0)"
class P(HTMLParser):
 def __init__(self):super().__init__();self.text=[];self.scripts=[];self.links=[];self.inputs=[]
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if t=="script" and a.get("src"):self.scripts.append(a["src"])
  if t=="a" and a.get("href"):self.links.append({"href":a["href"],"text":""})
  if t=="input":self.inputs.append({k:a.get(k) for k in ("name","id","value","type")})
 def handle_data(self,d):
  x=" ".join(d.split())
  if x:self.text.append(x)
  if self.links and x:self.links[-1]["text"]+=x
def main():
 cj=http.cookiejar.CookieJar();op=build_opener(HTTPCookieProcessor(cj))
 def get(url,ref):
  req=Request(url,headers={"User-Agent":UA,"Accept":"text/html,*/*","Referer":ref})
  with op.open(req,timeout=45) as r:return r.status,r.geturl(),r.read().decode("utf-8","replace")
 ps,pu,ph=get(PAGE,PAGE)
 ts,tu,th=get(TREE,PAGE)
 p=P();p.feed(th);txt=" ".join(p.text)
 terms=["tree","ztree","hyid","hyname","treadcode","industry","行业","trade","async","url","data","load","getHy","selectHylist","json"]
 snippets=[]
 for term in terms:
  start=0
  while len(snippets)<70:
   i=th.lower().find(term.lower(),start)
   if i<0:break
   snippets.append({"term":term,"offset":i,"snippet":th[max(0,i-250):min(len(th),i+650)]})
   start=i+len(term)
 out={"schema":"MEE_PUBLIC_INDUSTRY_TAXONOMY_DISCOVERY_V1","created_at_utc":datetime.now(timezone.utc).isoformat(),
  "main_page_status":ps,"tree_page_status":ts,"tree_url":tu,"html_bytes":len(th),"text_preview":txt[:12000],
  "inputs":p.inputs,"scripts":p.scripts,"links":p.links[:80],"keyword_snippets":snippets}
 root=pathlib.Path("research_engine/retirement/national_funnel/R4_ENVIRONMENT_236/POLLUTION_PERMIT_DISCOVERY/output")
 root.mkdir(parents=True,exist_ok=True)
 (root/"industry_taxonomy_probe.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 (root/"industry_taxonomy_page.html").write_text(th,encoding="utf-8")
 print("INDUSTRY_TREE",json.dumps({"status":ts,"bytes":len(th),"text":txt[:4000],"scripts":p.scripts,"inputs":p.inputs},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
