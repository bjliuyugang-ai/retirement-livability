#!/usr/bin/env python3
"""Build structured, geospatially matched evidence from five official MEE permit records."""
import base64,csv,hashlib,html,json,pathlib,re
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.request import Request,urlopen
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from shapely.geometry import shape,Point

ROOT=pathlib.Path("research_engine/retirement")
BASE=ROOT/"national_funnel/R4_ENVIRONMENT_236/POLLUTION_PERMIT_DISCOVERY"
OUT=BASE/"output"
CAND=ROOT/"national_funnel/FINAL_FILTER/runs/42453646573/FINAL_CARRY_FORWARD_AFTER_R1_R2_R3.csv"
GEO_URL="https://raw.githubusercontent.com/zzhonglei/GeoCode-Release/main/contributions/china-admin-boundaries/skill/data/china_county.geojson"
GEO_SHA="22db6c54b9cb0118ecdcc8a117bf2da4fc24a2229cdba7e6e55dbb5dd56e8246"
UA="Mozilla/5.0 (compatible; RetirementR4PublicEvidenceResearch/1.0)"
class TextParser(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,d):
  x=" ".join(d.split())
  if x:self.parts.append(x)
def clean(s):return html.unescape(s or "").replace("\xa0"," ").strip()
def first(pattern,text,flags=re.I|re.S):
 m=re.search(pattern,text,flags);return clean(re.sub(r"<[^>]+>"," ",m.group(1))) if m else None
def extract_list(label,next_label,text):
 m=re.search(re.escape(label)+r"\s*(.*?)\s*"+re.escape(next_label),text,re.S)
 return clean(m.group(1)) if m else None
def main():
 req=Request(GEO_URL,headers={"User-Agent":UA,"Accept":"application/geo+json,*/*"})
 with urlopen(req,timeout=90) as r:raw=r.read()
 sha=hashlib.sha256(raw).hexdigest()
 if sha!=GEO_SHA:raise RuntimeError("ADMIN_GEOJSON_SHA256_MISMATCH "+sha)
 geo_doc=json.loads(raw.decode("utf-8"))
 geoms={}
 for feat in geo_doc.get("features",[]):
  props=feat.get("properties") or {};code=str(props.get("adcode") or "")
  if len(code)==6 and feat.get("geometry"):geoms[code]={"name":props.get("name"),"geometry":shape(feat["geometry"])}
 with CAND.open(encoding="utf-8-sig",newline="") as f:
  candidates={r["code"]:r["name"] for r in csv.DictReader(f)}
 rows=[];outlets=[]
 for p in sorted(OUT.glob("details_*.html")):
  s=p.read_text(encoding="utf-8",errors="replace")
  pwd=first(r"var\s+pwd\s*=\s*'([^']+)'",s)
  word=first(r"var\s+word\s*=\s*'([^']+)'",s)
  lon=first(r'id="longitude"\s+value="([^"]+)"',s)
  lat=first(r'id="latitude"\s+value="([^"]+)"',s)
  tp=TextParser();tp.feed(s);txt=" ".join(tp.parts)
  company=first(r'<p[^>]*font-size:36px[^>]*>(.*?)</p>',s)
  address=first(r"生产经营场所地址：\\s*(.*?)\\s*行业类别：",txt)
  industry=first(r"行业类别：\\s*(.*?)\\s*所在地区：",txt)
  admin=first(r"所在地区：\\s*(.*?)\\s*发证机关：",txt)
  air=extract_list("大气主要污染物种类：","大气污染物排放规律：",txt)
  water=extract_list("废水主要污染物种类：","废水污染物排放规律：",txt)
  permit_no=re.search(r"details_(.+)\.html$",p.name).group(1)
  # Current and prior permit validity periods are preserved in source page text.
  validity=re.findall(r"\d{4}-\d{2}-\d{2}\s*至\s*\d{4}-\d{2}-\d{2}",txt)
  issued=re.findall(r"(?:重新申请|申领|延续|调整)\s+\d+\s+(\d{4}-\d{2}-\d{2})",txt)
  candidate_code=None;candidate_name=None;geom_match=None
  if lon and lat:
   pt=Point(float(lon),float(lat))
   for code,g in geoms.items():
    if g["geometry"].covers(pt):
     geom_match=code;break
   if geom_match in candidates:candidate_code=geom_match;candidate_name=candidates[geom_match]
  payload=[];decrypt="NO_PAYLOAD"
  try:
   key=pwd.encode();cipher=base64.b64decode(word)
   plain=unpad(AES.new(key,AES.MODE_ECB).decrypt(cipher),AES.block_size).decode("utf-8")
   payload=json.loads(plain);decrypt="SUCCESS"
  except Exception as e:decrypt="FAILED:"+repr(e)
  rec={"company":company,"permit_no":permit_no,"address":address,"admin_text":admin,"industry":industry,
       "facility_longitude":float(lon) if lon else None,"facility_latitude":float(lat) if lat else None,
       "matched_county_code":geom_match,"matched_county_name":geoms.get(geom_match,{}).get("name") if geom_match else None,
       "matched_236_candidate_code":candidate_code,"matched_236_candidate_name":candidate_name,
       "current_or_historical_validity_periods":";".join(dict.fromkeys(validity)),
       "permit_issue_dates":";".join(dict.fromkeys(issued)),
       "air_pollutants":air,"wastewater_pollutants":water,"decryption_status":decrypt,
       "outlet_point_count":len(payload) if isinstance(payload,list) else 0,
       "source_file":str(p)}
  rows.append(rec)
  if isinstance(payload,list):
   for i,o in enumerate(payload,1):
    outlets.append({"company":company,"permit_no":permit_no,"matched_236_candidate_code":candidate_code,
      "matched_236_candidate_name":candidate_name,"outlet_index":i,"outlet_icon_code":o.get("icon"),
      "longitude":o.get("longitude"),"latitude":o.get("latitude"),
      "longitude_dms":f'{o.get("drainlngd","")}°{o.get("drainlngm","")}\u2032{o.get("drainlngf","")}\u2033',
      "latitude_dms":f'{o.get("drainlatd","")}°{o.get("drainlatm","")}\u2032{o.get("drainlatf","")}\u2033'})
 summary={"schema":"RETIREMENT_R4_MEE_PERMIT_GEOSPATIAL_EVIDENCE_V1","created_at_utc":datetime.now(timezone.utc).isoformat(),
  "official_portal":"https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!licenseInformation.action",
  "source_scope":"Five publicly accessible Kunming permit records selected from the first page of the official city query; not a complete city inventory.",
  "candidate_count":len(candidates),"sample_permit_count":len(rows),"sample_outlet_point_count":len(outlets),
  "records_within_236_candidate_polygons":sum(1 for x in rows if x["matched_236_candidate_code"]),
  "admin_boundary_sha256":sha,"records":rows,"outlet_points":outlets,
  "guardrails":["Permit holder facility coordinates and individual outlet coordinates are distinct; both are retained.",
   "A point inside a candidate county polygon establishes administrative-area match only, not residential exposure.",
   "Permit pollutant lists are licensed pollutants, not proof of actual current emissions or a violation.",
   "No hard exclusion or grade change is made from these records alone."]}
 (OUT/"permit_geospatial_evidence_batch01.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 def write_csv(name,items):
  if not items:return
  with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
   w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
 write_csv("permit_facility_points_batch01.csv",rows)
 write_csv("permit_outlet_points_batch01.csv",outlets)
 print("PERMIT_GEO",json.dumps({"permits":len(rows),"outlets":len(outlets),"matched_candidates":summary["records_within_236_candidate_polygons"],"records":[{k:x.get(k) for k in ("company","industry","matched_236_candidate_code","facility_longitude","facility_latitude","outlet_point_count")} for x in rows]},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
