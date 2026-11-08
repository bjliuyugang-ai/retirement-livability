#!/usr/bin/env python3
"""Discover the public MEE pollution-permit portal's read-only search interface.

No account, credentials, or write actions are used. This script only fetches
public pages and linked JavaScript to identify safe query parameters.
"""
from __future__ import annotations
import json, re, time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BASES = [
    "https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!licenseInformation.action",
    "https://permit.mee.gov.cn/perxxgkinfo/defaults/default-index!getInformation.action",
]
UA = "Mozilla/5.0 (compatible; RetirementR4PublicEvidenceResearch/1.0; +https://github.com/bjliuyugang-ai/retirement-livability)"

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms=[]; self.inputs=[]; self.selects=[]; self.scripts=[]; self.links=[]; self.buttons=[]
        self._form=None; self._select=None; self._script=None
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=="form":
            self._form={"attrs":a,"inputs":[],"selects":[],"buttons":[]}; self.forms.append(self._form)
        elif tag=="input":
            item={k:a.get(k) for k in ("type","name","id","value","placeholder","onclick","onchange")}
            self.inputs.append(item)
            if self._form is not None:self._form["inputs"].append(item)
        elif tag=="select":
            self._select={"name":a.get("name"),"id":a.get("id"),"options":[]}
            self.selects.append(self._select)
            if self._form is not None:self._form["selects"].append(self._select)
        elif tag=="option" and self._select is not None:
            self._select["options"].append({"value":a.get("value"),"text":""})
        elif tag=="script":
            if a.get("src"):self.scripts.append(a["src"])
            self._script=a.get("src") is None
        elif tag=="a":
            self.links.append({"href":a.get("href"),"text":""})
        elif tag in ("button","input") and (a.get("onclick") or a.get("type")=="submit"):
            self.buttons.append({"tag":tag,"attrs":a})
            if self._form is not None:self._form["buttons"].append({"tag":tag,"attrs":a})
    def handle_endtag(self, tag):
        if tag=="form":self._form=None
        if tag=="select":self._select=None
        if tag=="script":self._script=None
    def handle_data(self,data):
        if self._select is not None and self._select["options"]:
            self._select["options"][-1]["text"]+=data.strip()
        if self.links and data.strip():
            self.links[-1]["text"]=(self.links[-1]["text"]+" "+data.strip()).strip()

def fetch(url, timeout=60, max_bytes=8_000_000):
    req=Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/javascript,*/*","Accept-Language":"zh-CN,zh;q=0.9,en;q=0.8"})
    with urlopen(req,timeout=timeout) as r:
        data=r.read(max_bytes+1)
        if len(data)>max_bytes: data=data[:max_bytes]
        return {"url":url,"final_url":r.geturl(),"status":getattr(r,"status",200),
                "content_type":r.headers.get("Content-Type"),"bytes":len(data),
                "body":data.decode("utf-8","replace")}

def snippets(text, terms, radius=220, limit=40):
    found=[]
    for term in terms:
        start=0
        while len(found)<limit:
            i=text.lower().find(term.lower(),start)
            if i<0:break
            found.append({"term":term,"offset":i,"snippet":text[max(0,i-radius):min(len(text),i+radius)]})
            start=i+len(term)
    return found

def main():
    result={"schema":"MEE_PERMIT_PUBLIC_PORTAL_DISCOVERY_V1","created_at_utc":datetime.now(timezone.utc).isoformat(),
            "scope":"READ_ONLY_PUBLIC_INTERFACE_DISCOVERY_ONLY","credentials_used":False,"pages":[],"javascript":[],"findings":[]}
    all_scripts=[]
    for url in BASES:
        try:
            page=fetch(url)
            parser=PageParser();parser.feed(page["body"])
            page_out={k:v for k,v in page.items() if k!="body"}
            page_out.update({"title":re.findall(r"<title[^>]*>(.*?)</title>",page["body"],re.I|re.S)[:1],
                "forms":parser.forms,"inputs":parser.inputs,"selects":parser.selects,
                "script_srcs":parser.scripts,"links":[x for x in parser.links if x["href"] and any(t in x["href"].lower() for t in ("license","information","query","search","detail","getinformation"))],
                "html_query_snippets":snippets(page["body"],["licenseInformation","getInformation","pageNo","currentPage","provinceCode","cityCode","unitName","industry","ajax","search"],limit=35)})
            result["pages"].append(page_out)
            all_scripts.extend(urljoin(page["final_url"],s) for s in parser.scripts)
        except Exception as e:
            result["pages"].append({"url":url,"error":repr(e)})
    seen=set()
    for url in all_scripts[:40]:
        if url in seen:continue
        seen.add(url)
        try:
            js=fetch(url,timeout=40,max_bytes=2_000_000)
            body=js.pop("body")
            js["keyword_snippets"]=snippets(body,["licenseInformation","getInformation","pageNo","currentPage","pageIndex","provinceCode","cityCode","unitName","companyName","industry","ajax","search","method:"],limit=50)
            if js["keyword_snippets"]:
                result["javascript"].append(js)
        except Exception as e:
            result["javascript"].append({"url":url,"error":repr(e)})
    # Summarize whether a search form and usable fields were found.
    for page in result["pages"]:
        if page.get("forms"):
            for form in page["forms"]:
                fields=[x.get("name") or x.get("id") for x in form.get("inputs",[])]
                fields += [x.get("name") or x.get("id") for x in form.get("selects",[])]
                result["findings"].append({"page":page.get("final_url"),"form_attrs":form.get("attrs"),"field_names":[x for x in fields if x]})
    out="research_engine/retirement/national_funnel/R4_ENVIRONMENT_236/POLLUTION_PERMIT_DISCOVERY/output/permit_portal_inspection.json"
    import pathlib
    p=pathlib.Path(out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PORTAL_DISCOVERY",json.dumps({"pages":len(result["pages"]),"scripts":len(result["javascript"]),"forms":len(result["findings"]),"output":out},ensure_ascii=False),flush=True)
    for item in result["findings"]:print("FORM",json.dumps(item,ensure_ascii=False),flush=True)

if __name__=="__main__":main()
