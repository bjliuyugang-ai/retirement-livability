#!/usr/bin/env python3
"""Fetch a small sample of public MEE permit detail pages, read-only."""
import json,re,http.cookiejar,pathlib
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.request import Request,build_opener,HTTPCookieProcessor
BASE="https://permit.mee.gov.cn"
INPUT="research_engine/retirement/national_funnel/R4_ENVIRONMENT_236/POLLUTION_PERMIT_DISCOVERY/output/kunming_query_page1_42463774649.html"
UA="Mozilla/5.0 (compatible; RetirementR4PublicEvidenceResearch/1.0)"
class RowParser(HTMLParser):
 def __init__(self):
  super().__init__();self.rows=[];self.row=None;self.td=False;self.cell="";self.a=None
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if t=="tr":self.row={"cells":[],"links":[]}
  elif t=="td" and self.row is not None:self.td=True;self.cell=""
  elif t=="a" and self.row is not None:self.a={"href":a.get("href"),"text":""}
 def handle_data(self,d):
  if self.td:self.cell+=d.strip()
  if self.a:self.a["text"]+=d.strip()
 def handle_endtag(self,t):
  if t=="td" and self.row is not None:self.row["cells"].append(self.cell);self.td=False
  elif t=="a" and self.a is not None:self.row["links"].append(self.a);self.a=None
  elif t=="tr" and self.row is not None:
   if self.row["cells"]:self.rows.append(self.row)
   self.row=None
class TextParser(HTMLParser):
 def __init__(self):super().__init__();self.text=[];self.links=[]
 def handle_data(self,d):
  t=" ".join(d.split())
  if t:self.text.append(t)
 def handle_starttag(self,t,attrs):
  if t=="a":
   a=dict(attrs)
   if a.get("href"):self.links.append(a["href"])
def snippets(text,terms,radius=350,limit=8):
 out=[]
 for term in terms:
  start=0
  while len(out)<limit:
   i=text.lower().find(term.lower(),start)
   if i<0:break
   out.append({"term":term,"offset":i,"snippet":text[max(0,i-radius):i+radius]})
   start=i+len(term)
 return out
def main():
 html=pathlib.Path(INPUT).read_text(encoding="utf-8")
 rp=RowParser();rp.feed(html)
 rows=[]
 for row in rp.rows:
  if len(row["cells"])<8 or row["cells"][0]!="云南省":continue
  if not row["links"]:continue
  cells=row["cells"]
  rows.append({"province":cells[0],"city":cells[1],"license_no":cells[2],"company":cells[3],"industry":cells[4],"validity":cells[5],"issue_date":cells[6],"management":cells[7],"detail_url":BASE+row["links"][0]["href"]})
 # Choose a risk-relevant sample and include one general municipal WWTP as a control.
 terms=("危险废物","污水处理","化学","铜冶炼","磷肥","电镀","水泥","造纸","焦化","制药")
 selected=[]
 for term in terms:
  for row in rows:
   if term in row["industry"] or term in row["company"]:
    if row not in selected:selected.append(row)
    break
 selected=selected[:10]
 cj=http.cookiejar.CookieJar();op=build_opener(HTTPCookieProcessor(cj))
 results=[]
 for row in selected:
  try:
   req=Request(row["detail_url"],headers={"User-Agent":UA,"Accept":"text/html,*/*","Referer":BASE+"/perxxgkinfo/syssb/xkgg/xkgg!licenseInformation.action"})
   with op.open(req,timeout=45) as r:
    body=r.read(6_000_000).decode("utf-8","replace");status=r.status;final=r.geturl();ct=r.headers.get("Content-Type")
   tp=TextParser();tp.feed(body);txt=" ".join(tp.text)
   rowout={**row,"http_status":status,"final_url":final,"content_type":ct,"html_bytes":len(body),"text_chars":len(txt),
    "title":re.findall(r"<title[^>]*>(.*?)</title>",body,re.I|re.S)[:1],
    "field_snippets":snippets(txt,["排放口","经度","纬度","坐标","地址","排放去向","排放方式","污染物","许可排放量","生产地址","生产设施","废水","废气","自行监测","厂界","总量"],limit=24),
    "links":tp.links[:40]}
   outname=re.sub(r"[^0-9A-Za-z_-]+","_",row["license_no"])
   p=pathlib.Path("research_engine/retirement/national_funnel/R4_ENVIRONMENT_236/POLLUTION_PERMIT_DISCOVERY/output/details_"+outname+".html")
   p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding="utf-8")
   rowout["saved_html"]=str(p)
   results.append(rowout)
  except Exception as e:results.append({**row,"error":repr(e)})
 result={"schema":"MEE_PERMIT_DETAIL_SAMPLE_V1","created_at_utc":datetime.now(timezone.utc).isoformat(),"credentials_used":False,"write_actions":False,"query_city":"云南省/昆明市","queried_city_pages":199,"selected_count":len(selected),"details":results}
 p=pathlib.Path("research_engine/retirement/national_funnel/R4_ENVIRONMENT_236/POLLUTION_PERMIT_DISCOVERY/output/permit_detail_probe.json")
 p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("DETAIL_PROBE",json.dumps({"selected":len(selected),"success":sum("http_status" in x for x in results),"results":[{k:x.get(k) for k in ("company","industry","http_status","html_bytes","text_chars","saved_html","error")} for x in results]},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
