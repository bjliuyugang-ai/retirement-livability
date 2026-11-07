#!/usr/bin/env python3
"""Actual 2024 and 2025 provincial official numeric air pollutants:
10 city PM2.5, ozone MDA8 P90 and good-days; and 58 county PM2.5 and
good-days two-year trend, strictly year matched and no residence inference.
No conflation between county O3 (not published numerically) and city O3.
"""
import collections,csv,datetime,hashlib,json,pathlib,re,urllib.request
from bs4 import BeautifulSoup
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
SOURCES={2024:"https://sthjt.fujian.gov.cn/zwgk/ywxx/kjjc/202502/t20250208_6712419.htm",2025:"https://sthjt.fujian.gov.cn/zwgk/ywxx/kjjc/202601/t20260126_7085242.htm"}
ROSTER=ROOT/"status/Fujian_2025_58_county_air_PM25_source_matched.csv"
CITYNAMES={"福州市","厦门市","漳州市","泉州市","三明市","莆田市","南平市","龙岩市","宁德市","平潭区"}
def sha(b):return hashlib.sha256(b).hexdigest()
def clean(s):return re.sub(r"\s+","",s).replace("\u3000","")
def num(s):
 if not re.fullmatch(r"\d+(?:\.\d+)?",s):raise ValueError("not number "+s)
 return float(s)
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":"RET-2024-2025-Fujian-Gov-Official-Pollution-TwoYearAudit/1.0"})
 with urllib.request.urlopen(req,timeout=100) as r:b=r.read(8_000_000)
 return b,BeautifulSoup(b.decode("utf-8","replace"),"html.parser")
def read(year):
 b,soup=fetch(SOURCES[year])
 tables=[]
 for table in soup.find_all("table"):
  rr=[]
  for tr in table.find_all("tr"):
   x=[clean(td.get_text(" ",strip=True)) for td in tr.find_all(["td","th"],recursive=False)]
   if x:rr.append(x)
  tables.append(rr)
 raw={"year":year,"source_url":SOURCES[year],"source_raw_sha256":sha(b),"source_bytes":len(b)}
 county_cands=[];city_cands=[]
 for ix,table in enumerate(tables):
  counties=[];cities=[]
  for cells in table:
   # CSV may represent rowspan with empty or missing city column; scan for county suffix.
   for i,nm in enumerate(cells):
    if nm in CITYNAMES:
     after=cells[i+1:]
     if len(after)>=8:
      try:
       good=num(after[1]);pm=num(after[5]);oz=num(after[7])
       if 0<pm<150 and 0<oz<350 and 50<=good<=100:
        cities.append({"city":nm,"good_days_pct":good,"PM25_annual_ugm3":pm,
         "O3_MDA8_p90_ugm3":oz,"annual_year":year})
      except (IndexError,ValueError):pass
     break
    if re.fullmatch(r"[^0-9]{2,16}(县|市|区)",nm) and nm not in CITYNAMES:
     rest=cells[i+1:]
     if len(rest)>=4:
      try:
       gd,idx,pm=map(num,rest[:3])
       if 70<=gd<=100 and .5<=idx<=10 and 0<pm<150:
        counties.append({"county_name":nm,"good_days_pct":gd,"air_index":idx,"PM25_annual_ugm3":pm,
        "primary_pollutant":rest[3],"annual_year":year})
      except (IndexError,ValueError):pass
     break
  if len(counties)>40:county_cands.append((ix,counties))
  if len(cities)>=9:city_cands.append((ix,cities))
 if not county_cands or not city_cands:raise ValueError("Fujian official two-year tables missing "+str(year)+":"+str((len(county_cands),len(city_cands))))
 county=max(county_cands,key=lambda z:z[0])[1]
 city=max(city_cands,key=lambda z:z[0])[1]
 if len(county)!=58 or len(city)!=10:raise RuntimeError("Expected 58 county/10 city annual records "+str((year,len(county),len(city))))
 if len({x["county_name"] for x in county})!=58 or len({x["city"] for x in city})!=10:raise RuntimeError("Duplicate city/county in annual data")
 raw.update({"county_records":county,"city_records":city,"city_table_count":len(city),"county_table_count":len(county)})
 return raw
d24=read(2024);d25=read(2025)
rdr=list(csv.DictReader(ROSTER.open(encoding="utf-8-sig")))
codename={z["county_name"]:z["candidate_code"] for z in rdr}
if len(codename)!=58 or len(set(codename.values()))!=58:raise RuntimeError("Official province 2025 county roster mapping invalid")
c24={x["county_name"]:x for x in d24["county_records"]}
c25={x["county_name"]:x for x in d25["county_records"]}
assert set(c24)==set(c25)==set(codename),"No silent 2024 2025 county identity mismatches"
city24={x["city"]:x for x in d24["city_records"]}
city25={x["city"]:x for x in d25["city_records"]}
assert set(city24)==set(city25)==CITYNAMES
county=[]
for name in sorted(codename):
 a,b=c24[name],c25[name]
 county.append({"code":codename[name],"name":name,"PM25_2024":a["PM25_annual_ugm3"],
 "PM25_2025":b["PM25_annual_ugm3"],"PM25_change_2025_minus_2024":round(b["PM25_annual_ugm3"]-a["PM25_annual_ugm3"],2),
 "good_days_2024_pct":a["good_days_pct"],"good_days_2025_pct":b["good_days_pct"],
 "good_days_change_pctpoints":round(b["good_days_pct"]-a["good_days_pct"],2),
 "county_numerical_O3":"NOT_PUBLISHED",
 "source24":SOURCES[2024],"source25":SOURCES[2025],"county_residential_air_verified":False})
city=[]
for name in sorted(CITYNAMES):
 a,b=city24[name],city25[name]
 city.append({"name":name,"PM25_2024_ugm3":a["PM25_annual_ugm3"],"PM25_2025_ugm3":b["PM25_annual_ugm3"],
  "PM25_change":round(b["PM25_annual_ugm3"]-a["PM25_annual_ugm3"],2),
  "O3_MDA8_P90_2024_ugm3":a["O3_MDA8_p90_ugm3"],"O3_MDA8_P90_2025_ugm3":b["O3_MDA8_p90_ugm3"],
  "O3_change":round(b["O3_MDA8_p90_ugm3"]-a["O3_MDA8_p90_ugm3"],2),
  "good_days_2024_pct":a["good_days_pct"],"good_days_2025_pct":b["good_days_pct"],
  "good_days_change_pctpoints":round(b["good_days_pct"]-a["good_days_pct"],2),
  "county_value_inference_allowed":False})
for name,rows in [("Fujian2024_2025_county_PM25_two_year_source.csv",county),("Fujian2024_2025_10city_PM25_O3_two_year_source.csv",city)]:
 out=OUT/name
 with out.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
report={"schema":"RET_R4_FUJIAN_2024_2025_GOV_OFFICIAL_COUNTY_PM25_CITY_O3_TREND_V1",
 "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_publication_years":[2025,2026],"source_publication_urls":SOURCES,
 "source_sha256":{"2024":d24["source_raw_sha256"],"2025":d25["source_raw_sha256"]},
 "county_twoyear_matched":58,"city_twoyear_matched":10,
 "county_numerical_ozone_values_available":0,
 "county_PM25_decreased":sum(x["PM25_change_2025_minus_2024"]<0 for x in county),
 "county_PM25_increased":sum(x["PM25_change_2025_minus_2024"]>0 for x in county),
 "county_PM25_unchanged":sum(x["PM25_change_2025_minus_2024"]==0 for x in county),
 "city_O3_decreased":sum(x["O3_change"]<0 for x in city),
 "city_O3_increased":sum(x["O3_change"]>0 for x in city),
 "city_O3_unchanged":sum(x["O3_change"]==0 for x in city),
 "county_twoyear_records":county,"city_twoyear_records":city,
 "county_csv_sha256":sha((OUT/"Fujian2024_2025_county_PM25_two_year_source.csv").read_bytes()),
 "city_csv_sha256":sha((OUT/"Fujian2024_2025_10city_PM25_O3_two_year_source.csv").read_bytes()),
 "formal_valid_county_screenings":0,"county_exclusions":0,
 "quality_note":"Actual annual county PM2.5 and city O3 from published provincial environmental monitoring reports. No county-level numerical O3, no residential site, 2y does not prove 1991-2020 long baseline."}
(OUT/"Fujian2024_2025_air_pollution_two_year_evidence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["county_twoyear_matched","city_twoyear_matched","county_PM25_decreased","county_PM25_increased","county_PM25_unchanged","city_O3_decreased","city_O3_increased","city_O3_unchanged"]},ensure_ascii=False),flush=True)
