#!/usr/bin/env python3
"""One-shot A/B geocode repair audit. No official climate or grade overwrite."""
import csv, datetime, json, math, pathlib, re, time, urllib.parse
import requests
from shapely.geometry import shape, Point
ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"status"; OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/"output/phase1_236_master_V1p5_library_parsed_backup_20261110.csv"
SUP=ROOT/"output/phase1_236_residential_climate_parameter_supplement_20261109.csv"
ALIASES={
"469001":"通什镇","532929":"诺邓镇","532922":"苍山西镇","532901":"大理古城",
"530581":"腾越街道","532531":"大兴镇","532301":"鹿城镇","469030":"营根镇",
"533301":"六库街道","532927":"南诏镇","530802":"思茅街道","532503":"文澜街道",
"533103":"勐焕街道","530502":"永昌街道","513401":"北城街道","530402":"玉兴街道",
"532327":"永定镇","510421":"攀莲镇","532524":"建水古城","532601":"开化街道",
"530902":"凤翔街道",
"530826":"勐烈镇","530128":"屏山街道","513426":"金江街道","530921":"凤山镇",
"513427":"披砂镇","530723":"中心镇","532923":"祥城镇","532822":"勐海镇",
"530524":"田园镇","530521":"甸阳镇","513402":"城北街道",
"530112":"马街街道","530113":"铜都街道","530824":"威远镇",
"530927":"勐董镇","530115":"昆阳街道","532328":"元马镇","530114":"龙城街道"
}
PROV={"53":"云南省","51":"四川省","46":"海南省","44":"广东省"}
def load(path):
 with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
base={x["区域"]:x for x in load(BASE)}
sup=load(SUP)
targets=[x for x in sup if base[x["区域"]]["第一阶段评估等级"] in ("A","B")
         and ("指定居住片区未被精确解析" in x.get("复核原因","")
          or x.get("地理编码类型")=="administrative")]
print("A/B target count",len(targets),flush=True)
u="https://raw.githubusercontent.com/zzhonglei/GeoCode-Release/main/contributions/china-admin-boundaries/skill/data/china_county.geojson"
g=requests.get(u,timeout=120,headers={"User-Agent":"RetirementClimateAudit/1.0"});g.raise_for_status()
geoms={}
for f in g.json()["features"]:
 c=str(f.get("properties",{}).get("adcode","")).zfill(6)
 if c in {x["行政代码"] for x in targets} and f.get("geometry"):geoms[c]=shape(f["geometry"])
user_agent={"User-Agent":"RetirementLivabilityAcademicAudit/1.0 (climate-research@users.noreply.github.com)","Accept-Language":"zh-CN"}
audit=[];selected=[];last_request=0
for index,x in enumerate(targets,1):
 code=x["行政代码"];name=x["区域"].split("·",1)[-1];prov=PROV.get(code[:2],"中国")
 alias=ALIASES.get(code)
 qs=[]
 if alias: qs.append(("named_alias", alias+" "+name+" "+prov))
 if alias and not alias.endswith("街道"): qs.append(("alias_short",alias+" "+prov))
 qs.append(("government",name+"人民政府 "+prov))
 if x["地理编码类型"]=="administrative":qs.append(("county_seat",name+"城区 "+prov))
 seen=set();evidence=[];accepted=[]
 for role,q in qs:
  if q in seen:continue
  seen.add(q)
  # Nominatim usage policy: at most one request per second, identifiable UA, no concurrent calls.
  lag=time.monotonic()-last_request
  if lag<1.2:time.sleep(1.2-lag)
  try:
   resp=requests.get("https://nominatim.openstreetmap.org/search",
      params={"q":q,"format":"jsonv2","addressdetails":1,"limit":5,"countrycodes":"cn","accept-language":"zh-CN"},
      headers=user_agent,timeout=45)
   last_request=time.monotonic();resp.raise_for_status();result=resp.json()
  except Exception as e:
   evidence.append({"query":q,"role":role,"error":repr(e)[:220]});continue
  found=0
  for z in result:
   cls=z.get("class","");typ=z.get("type","");ot=z.get("osm_type","")
   if typ=="administrative" or (cls=="boundary" and ot=="relation"):continue
   try:lat=float(z["lat"]);lon=float(z["lon"])
   except Exception:continue
   geom=geoms.get(code)
   if geom is None or not geom.covers(Point(lon,lat)):continue
   display=z.get("display_name","")
   if not (name in display or alias and alias in display):continue
   aliasmatch=bool(alias and alias in display)
   base_score=50 if role=="named_alias" and aliasmatch else 35 if role=="alias_short" and aliasmatch else 15
   if typ in ("suburb","neighbourhood","town","city","village","hamlet"):base_score+=12
   if typ in ("townhall","government"):base_score+=7
   if cls=="place":base_score+=5
   oldlat=x.get("定位纬度");oldlon=x.get("定位经度")
   distance=None
   try:
    a=math.radians(float(oldlat));b=math.radians(lat)
    dy=(b-a);dx=math.radians(lon-float(oldlon))
    h=math.sin(dy/2)**2+math.cos(a)*math.cos(b)*math.sin(dx/2)**2
    distance=round(6371*2*math.asin(min(1,math.sqrt(h))),1)
   except Exception:pass
   if distance is not None and distance>80:continue
   found+=1
   accepted.append({"code":code,"region":x["区域"],"grade":base[x["区域"]]["第一阶段评估等级"],
    "alias":alias or "","query":q,"query_role":role,"lat":lat,"lon":lon,"display_name":display,
    "geocode_type":typ,"geocode_class":cls,"osm_type":ot,"osm_id":str(z.get("osm_id","")),
    "old_lat":oldlat or "","old_lon":oldlon or "","distance_from_old_km":distance,
    "alias_in_display":aliasmatch,"score":base_score+float(z.get("importance") or 0)})
  evidence.append({"query":q,"role":role,"nominatim_returns":len(result),"accepted_in_polygon":found})
 audit.append({"code":code,"region":x["区域"],"grade":base[x["区域"]]["第一阶段评估等级"],
  "original_reference":x["居住片区参考"],"alias":alias or "",
  "original_geocode_type":x["地理编码类型"],"original_display":x["定位显示名称"],
  "queries":evidence,"accepted_count":len(accepted)})
 choices=[y for y in accepted if y["code"]==code]
 if choices:
  choices.sort(key=lambda z:z["score"],reverse=True)
  sel=choices[0]
  sel["decision"]="CANDIDATE_NAMED_SETTLEMENT" if sel["alias_in_display"] else "CANDIDATE_GOVERNMENT_SEAT"
  selected.append(sel)
 print("PROGRESS",index,"of",len(targets),code,name,selected[-1]["decision"] if selected and selected[-1]["code"]==code else "NO_NEW_VALID_POINT",flush=True)
headers=["code","region","grade","alias","query","query_role","lat","lon","display_name","geocode_type",
 "geocode_class","osm_type","osm_id","old_lat","old_lon","distance_from_old_km","alias_in_display","score","decision"]
csv_path=OUT/"phase1_236_ab_geocode_repair_candidates_20261110.csv"
with csv_path.open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=headers);w.writeheader();w.writerows(selected)
sumry={"schema":"PHASE1_236_AB_GEO_AUDIT_V1","time_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "targets":len(targets),"candidate_points":len(selected),
 "named_alias_confirmed":sum(x["decision"]=="CANDIDATE_NAMED_SETTLEMENT" for x in selected),
 "government_proxy":sum(x["decision"]=="CANDIDATE_GOVERNMENT_SEAT" for x in selected),
 "unresolved":len(targets)-len(selected),
 "correctness_notes":["A nominated location is a repair candidate, not verified residence coordinates.",
 "Only candidate points inside original exact candidate polygon and not OSM administrative boundary relation are accepted.",
 "No climate values, original grades, or first-stage exclusions overwritten."],
 "raw_query_audit":audit}
(OUT/"phase1_236_ab_geocode_repair_audit_20261110.json").write_text(json.dumps(sumry,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("SUMMARY",json.dumps({k:v for k,v in sumry.items() if k!="raw_query_audit"},ensure_ascii=False),flush=True)
