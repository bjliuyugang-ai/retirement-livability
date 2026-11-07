#!/usr/bin/env python3
"""Reproducibly archive Ministry of Ecology and Environment 2025 annual PM2.5
values for 168 named priority cities from its six annex image pages, crosswalk
2025 municipal codes and link CITY CONTEXT ONLY to provisional 2847-county ledger.

Critical: city annual mean PM2.5 is NOT county, residential-street, seasonal
PM2.5, ozone, local industrial pollution or a formal R4 county evaluation.
Transcription requires secondary digit review; preserve every JPEG raw SHA.
"""
import collections,csv,datetime,hashlib,json,pathlib,re,urllib.request
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
ANN=ROOT/"evidence/mee_2025_168_cities_pm25_annex_transcription.csv"
MIRROR=ROOT/"evidence/mirror_2025_adcodes.txt"
PREV=ROOT/"status/national_R3_205_station_dem_altitude_partial_2847.csv"
R3=ROOT/"status/national_R3_205_station_dem_altitude_source_evidence.json"
def digest(b):return hashlib.sha256(b).hexdigest()
r3=json.loads(R3.read_text(encoding="utf-8"))
if r3["total_R3_partial_point_evidence_counties"]!=205 or r3["formal_valid_county_screenings"]!=0:
 raise RuntimeError("Previous R3 source stage not verified")
if digest(PREV.read_bytes())!=r3["output_national_csv_sha256"]:
 raise RuntimeError("Previous R3 2847 county registry SHA drift")
with ANN.open(encoding="utf-8",newline="") as f:
 rd=csv.DictReader(f);cities=list(rd)
with PREV.open(encoding="utf-8-sig",newline="") as f:
 rdr=csv.DictReader(f);fields=list(rdr.fieldnames);counties=list(rdr)
if len(cities)!=168 or len(counties)!=2847 or len({r["candidate_code"] for r in counties})!=2847:
 raise RuntimeError("MEE 168 or 2847 source row mismatch")
known={};
for line in MIRROR.read_text(encoding="utf-8").splitlines():
 if line.strip():
  parts=line.split(maxsplit=1)
  if len(parts)!=2 or not re.fullmatch(r"[0-9]{6}",parts[0]):raise RuntimeError("Invalid historical county code line")
  known[parts[0]]=parts[1]
if len(known)!=3212:raise RuntimeError("Historical 2025 codes source unexpected")
city_code_lookup=collections.defaultdict(list)
for code,name in known.items():
 if code.endswith("00"):city_code_lookup[name].append(code)
city_code_lookup["北京市"]=["110000"]
city_code_lookup["天津市"]=["120000"]
city_code_lookup["上海市"]=["310000"]
city_code_lookup["重庆市"]=["500000"]
annex_ids=[
 "W020260128508395887866.jpg",
 "W020260128510156334836.jpg",
 "W020260128510522537058.jpg",
 "W020260128510716141744.jpg",
 "W020260128511325397127.jpg",
 "W020260128511513082894.jpg"]
urlprefix="https://www.mee.gov.cn/ywdt/xwfb/202601/"
image_raw=[]
for k,name in enumerate(annex_ids):
 url=urlprefix+name
 req=urllib.request.Request(url,headers={"User-Agent":"Retirement2025MEEOfficialAnnexSourceQA/1.0","Accept":"image/jpeg,*/*"})
 try:
  with urllib.request.urlopen(req,timeout=85) as resp:
   data=resp.read(2500000)
   status=resp.status
  if status!=200 or len(data)<10000 or data[:2]!=bytes([0xff,0xd8]):
   raise ValueError("MEE JPEG source missing original magic or size "+str((status,len(data),data[:8])))
  image_raw.append({"page_index":k+1,"url":url,"bytes":len(data),"sha256":digest(data),"http_status":status,"source_verified":True})
  print("MEE_ANNEX_PAGE_ACTUALLY_DOWNLOADED",k+1,len(data),flush=True)
 except Exception as ex:
  image_raw.append({"page_index":k+1,"url":url,"source_verified":False,"error":repr(ex)})
  print("MEE_ANNEX_HTTP_ERROR",k+1,repr(ex),flush=True)
# City names and values transcribed from original image; validate with
# known Beijing and Lhasa/Haikou/Shanghai spot checks.
spot={"北京市":27.0,"拉萨市":10.5,"海口市":15.4,
      "昆明市":20.2,"贵阳市":20.0,"上海市":26.3,
      "广州市":21.5,"深圳市":16.8,"乌鲁木齐市":35.3}
matched=[];unmatched=[]
for idx,source in enumerate(cities,1):
 if int(source["annex_row"])!=idx:raise RuntimeError("Official annex row order malformed")
 city=source["city_name_2025"];pm=float(source["annual_2025_PM25_ug_m3"])
 if not(5<=pm<=80):raise RuntimeError("Annual source city PM25 unreasonable "+city+str(pm))
 if city in spot and pm!=spot[city]:raise RuntimeError("Official annex sample cell mismatch "+city)
 locs=city_code_lookup.get(city,[])
 if len(locs)!=1:
  unmatched.append({"row":idx,"city":city,"candidate_codes":locs})
  continue
 code=locs[0]
 page=(1 if idx<=25 else 2 if idx<=54 else 3 if idx<=83 else 4 if idx<=112 else 5 if idx<=141 else 6)
 if source["source_official_image"]!=urlprefix+annex_ids[page-1]:raise RuntimeError("City source page attribution wrong "+city)
 matched.append({"annex_row":idx,"city":city,"city_2025_adcode":code,"2025_pm25_annual_ug_m3":pm,
     "measured_scope":"168_PRIORITIZED_CITY_PM25_2025_12_MONTH_MEAN",
     "source_year":2025,"source_publication":"2026-01-28",
     "official_page_url":"https://www.mee.gov.cn/ywdt/xwfb/202601/t20260128_1142783.shtml",
     "source_image_url":source["source_official_image"],
     "image_sha256":image_raw[page-1].get("sha256"),
     "image_direct_http_verified":image_raw[page-1]["source_verified"],
     "original_annex_value_transcription_review":"SINGLE_PASS_VISUAL_TO_BE_SECOND_VERIFIED",
     "city_scope_not_2026_county_or_residence":True,
     "O3_city_annual_value_acquired":False})
if len(matched)!=168 or unmatched:raise RuntimeError("168 priority cities not uniquely mapped to official-year historical prefecture codes "+str(unmatched))
if len({z["city_2025_adcode"] for z in matched})!=168:raise RuntimeError("Duplicate matched prefecture codes")
code_to_city={r["city_2025_adcode"]:r for r in matched}
# County code hierarchy is unambiguous for regular 4-digit prefix cities.
# Direct-admin Beijing, Tianjin, Shanghai, Chongqing use two-digit province.
# Some 2026 unit status still must be separately checked.
def parent_code(row):
 code=row["candidate_code"]
 if code[:2] in ["11","12","31","50"]:return code[:2]+"0000"
 return code[:4]+"00"
plus=["R4_official_2025_CITY_PM25_context_ugm3","R4_official_2025_parent_city_code",
 "R4_official_2025_parent_city_name","R4_official_2025_city_context_provenance",
 "R4_official_2025_ozone_county_unknown","R4_official_2025_residential_air_unknown"]
for z in plus:
 if z in fields:raise RuntimeError("City PM context field already in prior national CSV")
fields+=plus
coded_count=0
for row in counties:
 code=parent_code(row)
 src=code_to_city.get(code)
 if not src:continue
 coded_count+=1
 row["R4_official_2025_CITY_PM25_context_ugm3"]=src["2025_pm25_annual_ug_m3"]
 row["R4_official_2025_parent_city_code"]=code
 row["R4_official_2025_parent_city_name"]=src["city"]
 row["R4_official_2025_city_context_provenance"]=src["source_image_url"]
 row["R4_official_2025_ozone_county_unknown"]="TRUE"
 row["R4_official_2025_residential_air_unknown"]="TRUE"
 # Explicitly DO NOT change R4_status from NOT_SCREENED:
 # city-wide context != evidence of this particular county/residential air.
if any(row["confirmed_exit_round"] or row["formal_grade"] or str(row["valid_county_screening"]).lower()=="true" for row in counties):
 raise RuntimeError("Unauthorized county exclusion/grading")
countyCSV=OUT/"national_R4_2025_168_city_PM25_CONTEXT_ONLY_2847.csv"
with countyCSV.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(counties)
cityCSV=OUT/"mee_2025_168_official_city_PM25_verified_source.csv"
with cityCSV.open("w",encoding="utf-8-sig",newline="") as f:
 col=list(matched[0]);wr=csv.DictWriter(f,fieldnames=col);wr.writeheader();wr.writerows(matched)
values=sorted(matched,key=lambda x:x["2025_pm25_annual_ug_m3"])
summary={
 "schema":"RET_2025_MEE_168_OFFICIAL_CITY_PM25_YEARLY_CONTEXT_NOT_COUNTY_V1",
 "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_annex_url":"https://www.mee.gov.cn/ywdt/xwfb/202601/t20260128_1142783.shtml",
 "official_release_date":"2026-01-28",
 "2025_year_annual_priority_city_sample_count":168,
 "2025_prefecture_city_code_history_mapped":len(matched),
 "official_source_annex_page_count":len(image_raw),
 "annex_page_http_verified_count":sum(z["source_verified"] for z in image_raw),
 "annex_page_http_evidence":image_raw,
 "source_manual_transcription_sha256":digest(ANN.read_bytes()),
 "source_historical_2025_city_code_list_sha256":digest(MIRROR.read_bytes()),
 "previous_R3_2847_national_csv_sha256":digest(PREV.read_bytes()),
 "provisional_counties_with_parent_2025_city_pm25_CONTEXT_ONLY":coded_count,
 "provisional_counties_without_parent_2025_city_pm25_context":2847-coded_count,
 "city_monitoring_scope":"168 city PM2.5 annual means, not any county, suburb or dwelling exposure",
 "city_2025_PM25_lowest_five":[{"city":r["city"],"pm25":r["2025_pm25_annual_ug_m3"]} for r in values[:5]],
 "city_2025_PM25_highest_five":[{"city":r["city"],"pm25":r["2025_pm25_annual_ug_m3"]} for r in values[-5:]],
 "all_city_rows":matched,
 "city_csv_sha256":digest(cityCSV.read_bytes()),
 "county_context_csv_sha256":digest(countyCSV.read_bytes()),
 "actual_verified_county_air_quality_screenings":0,
 "formal_valid_county_screenings":0,
 "confirmed_county_exclusions":0,
 "full_county_candidates_preserved":2847,
 "missing_city_ozone_and_good_day_from_this_annex":True,
 "image_transcription_double_review_outstanding":True,
 "limitations":[
  "Original six official annex JPEG files and HTTP SHA are recorded individually; visually transcribed city numerical cells still require independent digit-by-digit review",
  "2025 city PM2.5 mean cannot prove any individual county, residential block, microclimate or industrial exposure",
  "The annex supplies annual PM2.5 but NOT city ozone/good-day; 2025 annual MEE national summary cannot substitute for 168 city ozone",
  "Some provisional 2026 county codes rely on 2025 prefecture hierarchy, unverified current administrative boundary",
  "Never auto-assign A/B/C/D, do not exclude any county, full R4 locality remains PENDING until site-level evidence"]
}
(OUT/"mee_2025_168_official_city_PM25_context_evidence.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:summary[k] for k in ["2025_year_annual_priority_city_sample_count","2025_prefecture_city_code_history_mapped","annex_page_http_verified_count","provisional_counties_with_parent_2025_city_pm25_CONTEXT_ONLY","provisional_counties_without_parent_2025_city_pm25_context","city_2025_PM25_lowest_five","city_2025_PM25_highest_five","actual_verified_county_air_quality_screenings"]},ensure_ascii=False),flush=True)
