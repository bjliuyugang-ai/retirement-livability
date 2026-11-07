#!/usr/bin/env python3
"""V1.6 audit-only consolidated R0-R5 evidence table (2847 provisional counties).

This is NOT an A/B/C/D grade and is not a redesign of the user's formal
Library master. Attach actual 2025 city background separately from county
PM2.5, and raw water separately from water plant or household tap samples.
Missing evidence is PENDING, NEVER automatically a failed grade/exclusion.
"""
import collections,csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
P={
 "R0":ROOT/"status/national_cascade_r0_provisional.csv",
 "R1R2":ROOT/"status/national_2847_R1_R2_joint_cascade_evidence_and_next_gap.csv",
 "R1R2_summary":ROOT/"status/national_2847_R1_R2_joint_cascade_summary.json",
 "R1_short":ROOT/"status/meteostat_CN_226_R1_tiered_expansion_evidence.json",
 "R2_short":ROOT/"status/meteostat_CN132_interim_R2_evidence.json",
 "R3":ROOT/"status/national_R3_205_station_dem_altitude_source_evidence.json",
 "R3_national":ROOT/"status/national_R3_205_station_dem_altitude_partial_2847.csv",
 "R4_city":ROOT/"status/mee_2025_168_official_city_PM25_context_evidence.json",
 "R4_city_csv":ROOT/"status/national_R4_2025_168_city_PM25_CONTEXT_ONLY_2847.csv",
 "R4_FJ":ROOT/"status/Fujian2025_official_R4_county_air_evidence.json",
 "R4_FJ_national":ROOT/"status/national_R4_official_Fujian2025_county_PM25_2847.csv",
 "R5":ROOT/"status/R5_2025_crossprovince_7counties_finished_tap_plant_source_evidence.json",
 "R5_national":ROOT/"status/national_R5_2025_7district_finished_water_source_partial_2847.csv",
 "R5_FJ":ROOT/"status/Fujian2025_12_R5_official_raw_water_source_evidence.json"}
def hashfile(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()
def j(k):return json.loads(P[k].read_text(encoding="utf-8"))
def csvmap(k):
 with P[k].open(encoding="utf-8-sig",newline="") as f:
  d=list(csv.DictReader(f))
 if len(d)!=2847 or len(set(x["candidate_code"] for x in d))!=2847:
  raise RuntimeError("Nonunique/incomplete full 2847 national source "+k)
 return {x["candidate_code"]:x for x in d}
a=j("R1R2_summary");b=j("R1_short");c=j("R2_short");d=j("R3");e=j("R4_city");f=j("R4_FJ");g=j("R5");h=j("R5_FJ")
required=[
 ("R1R2","R1R2_summary","national_cascade_csv_sha256"),
 ("R3_national","R3","output_national_csv_sha256"),
 ("R4_city_csv","R4_city","county_context_csv_sha256"),
 ("R4_FJ_national","R4_FJ","national_R4_register_sha256"),
 ("R5_national","R5","national_output_csv_sha256")]
for source,report,key in required:
 if hashfile(P[source])!=j(report)[key]:raise RuntimeError("Source CSV SHA changed "+source)
if not(a["total_provisional_counties"]==2847 and a["R1_has_any_long_or_short_source_evidence"]==214
 and a["R2_has_any_long_or_short_source_evidence"]==199
 and d["total_R3_partial_point_evidence_counties"]==205
 and e["provisional_counties_with_parent_2025_city_pm25_CONTEXT_ONLY"]==1510
 and f["actual_county_code_name_matched_to_provisional_2847"]==58
 and g["all_source_or_finished_partial_county_evidence_after"]==61
 and h["distinct_actual_county_code_source_evidence"]==56
 and a["R1_R2_formal_valid_screenings"]==0
 and d["formal_valid_county_screenings"]==0 and g["formal_valid_county_screenings"]==0):
 raise RuntimeError("Nonmatching frozen cross-round source counts")
R0=csvmap("R0");CL=csvmap("R1R2");GEOM=csvmap("R3_national")
CITY=csvmap("R4_city_csv");FJ=csvmap("R4_FJ_national");WATER=csvmap("R5_national")
allcodes=set(R0)
for key,src in [("R1R2",CL),("R3",GEOM),("R4city",CITY),("R4FJ",FJ),("R5",WATER)]:
 if set(src)!=allcodes:raise RuntimeError("Code key set mismatch from source "+key)
short_r1=set(b["new_interim_county_codes"]);short_r2=set(c["new_interim_R2_codes"])
r3={z["candidate_code"]:z for z in d["source_point_evidence_county_records"]}
fujian={z["candidate_code"]:z for z in f["county_source_records"]}
fjsource=set(h["new_R5_county_code_ids"])
tap={z["county_code"]:z for z in g["source_records"] if z["source_quality"]=="HTTP_REAL_AND_TEXT_VERIFIED"}
if not (len(short_r1)==127 and len(short_r2)==126 and len(r3)==205 and len(fujian)==58 and len(fjsource)==56 and len(tap)==4):
 raise RuntimeError("Actual source detailed codes do not match count proof")
citydata={}
for z in e["all_city_rows"]:
 code=z["city_2025_adcode"]
 if code in citydata:raise RuntimeError("Duplicate official 2025 city code "+code)
 citydata[code]=z
if len(citydata)!=168:raise RuntimeError("Official city 168 codes lost")
def parent(code):
 return code[:2]+"0000" if code[:2] in ["11","12","31","50"] else code[:4]+"00"
rows=[];cov=collections.Counter();regions=collections.defaultdict(lambda:collections.Counter())
for code in sorted(allcodes):
 r0=R0[code];r=CL[code];z=r3.get(code);fj=fujian.get(code);tw=tap.get(code);city=citydata.get(parent(code))
 if not (r0["candidate_name"]==r["candidate_name"]==GEOM[code]["candidate_name"]==CITY[code]["candidate_name"]==WATER[code]["candidate_name"]):
  raise RuntimeError("National candidate name not invariant for "+code)
 R1=r["R1_status"]!="NOT_SCREENED"
 R2=r["R2_status"]!="NOT_SCREENED"
 R3=z is not None
 R4=fj is not None
 R4city=city is not None
 R5=code in fjsource or code=="532503" or tw is not None
 if (WATER[code]["R5_status"]!="NOT_SCREENED")!=R5:
  raise RuntimeError("R5 history source county evidence not reconcilable "+code)
 if bool(R1)!=bool(CL[code]["R1_status"]!="NOT_SCREENED") or bool(R2)!=bool(CL[code]["R2_status"]!="NOT_SCREENED"):
  raise RuntimeError("R1R2 status mismatch")
 R1T="SHORT_15YR_STATION_PARTIAL" if code in short_r1 else ("LONGER_30YR_OR_ERA5_POINT_PARTIAL" if R1 else "MISSING_PENDING")
 R2T="SHORT_15YR_STATION_PARTIAL" if code in short_r2 else ("LONGER_30YR_OR_ERA5_POINT_PARTIAL" if R2 else "MISSING_PENDING")
 if code in short_r1 and not R1:raise RuntimeError("R1 short code without R1 data")
 if code in short_r2 and not R2:raise RuntimeError("R2 short code without R2 data")
 WTYPE=("NAMED_HOUSEHOLD_OR_NETWORK_TAP_SAMPLE" if tw and tw["sample_scope"]!="TREATED_WATER_TWO_PLANT_OUTLETS" else
        "NAMED_TREATMENT_PLANT_OUTLET" if tw else
        "NAMED_TAP_SAMPLE_2026_MENGZI" if code=="532503" else
        "NAMED_UNTREATED_INTAKE_ONLY" if code in fjsource else "MISSING_PENDING")
 # Four sources are all external to Fujian R5 raw source; no double counts.
 statuses=[R1,R2,R3,R4,R5]
 missing=[label for label,has in zip(["R1_气温含极端","R2_日照降水及湿度","R3_住宅海拔灾害","R4_县域空气污染","R5_饮水处理末梢及工业土壤"],statuses) if not has]
 # Even if a source is present, it is PARTIAL. All 5 require residential/county temporal validation.
 special=[]
 if R1:special.append("R1_30年极端连续期、地形微气候待核")
 if R2:special.append("R2_连续阴雨、湿度/露点及季节性待核")
 if R3:special.append("R3_住宅海拔地灾风险待核")
 if R4:special.append("R4_县域臭氧浓度及住宅污染源待核")
 elif R4city:special.append("R4_仅上级城市PM2.5背景，不是县级空气实测")
 if R5:special.append("R5_取水口与供水厂/住户输配关系、产业土壤污染待核")
 row={
 "县级候选代码_临时":code,"县级候选名称":r["candidate_name"],"省级代码":code[:2],
 "行政口径与正式状态":"2025历史县级代码＋2026两新设县补录；2026完整官方县界未核",
 "R1_气温点位数据":("有_部分" if R1 else "缺失待核"),"R1_证据窗口":R1T,
 "R2_降雨日照点位":("有_部分" if R2 else "缺失待核"),"R2_证据窗口":R2T,
 "R3_海拔DEM点位":("有_部分" if R3 else "缺失待核"),
 "R3_站点海拔最低m":(z["station_altitude_min_m"] if z else ""),
 "R3_站点海拔最高m":(z["station_altitude_max_m"] if z else ""),
 "R3_三点DEM高差m":(z["dem_three_point_span_m"] if z else ""),
 "R3_高海拔点需局地复核":("是_不可淘汰整县" if z and z["high_station_or_DEM_point_over_2000_m"] else ""),
 "R3_县内地形异质性提醒":("是" if z and z["significant_internal_altitude_heterogeneity_flag"] else ""),
 "R4_本县官方PM25_2025":("有_县级局地数据" if R4 else "缺失待核"),
 "R4_县级PM25_2025_ugm3":(fj["PM25_annual_ugm3"] if fj else ""),
 "R4_县级空气优良率2025_百分比":(fj["good_air_days_pct"] if fj else ""),
 "R4_官方上级城市PM25背景":("有_市级不代表本县" if R4city else "缺失待核"),
 "R4_上级城市PM25_2025_ugm3":(city["2025_pm25_annual_ug_m3"] if city else ""),
 "R4_城市背景来源需复核":("人工转录待二次校验" if city else ""),
 "R5_具名水源或末梢证据":("有_部分" if R5 else "缺失待核"),
 "R5_水质证据层级":WTYPE,
 "R5_监测样本数_可得":(tw["reported_sample_count"] if tw and tw["reported_sample_count"] is not None else ""),
 "R5_采样期_可得":(tw["quarter"] if tw else "2025-12" if code in fjsource else "2026" if code=="532503" else ""),
 "R5_数据URL_可得":(tw["source_url"] if tw else h["source_URL"] if code in fjsource else ""),
 "已获地方直接或点位证据轮数":sum(statuses),
 "R4上级城市背景单独计":int(R4city),
 "R0_R5尚缺轮次":"；".join(missing),
 "已有参数仍需进一步核验":"；".join(special),
 "临时处置":"仅证据跟踪_所有2847保留_禁止据缺失排除",
 "是否具备正式A级B级C级D级":"否_缺正式全国行政口径和住宅局地关键证据",
 "正式剔除":"否","复活条件":"如后续有合法数据或片区住宅级证据更新重评"}
 rows.append(row)
 for label,flag in [("R1",R1),("R2",R2),("R3",R3),("R4_COUNTY",R4),("R4_CITY_BG",R4city),("R5",R5)]:cov[label]+=int(flag);regions[code[:2]][label]+=int(flag)
 regions[code[:2]]["total"]+=1
 if not statuses or all(not x for x in statuses):regions[code[:2]]["all_5_missing"]+=1
 if all(statuses):cov["all_5_partial"]+=1;regions[code[:2]]["all_5_partial"]+=1
 if R1 and R2 and R3:cov["R1_R2_R3_overlap"]+=1
if len(rows)!=2847 or len({r["县级候选代码_临时"] for r in rows})!=2847:raise RuntimeError("Integrated county identity invariant failed")
if not(cov["R1"]==214 and cov["R2"]==199 and cov["R3"]==205 and cov["R4_COUNTY"]==58 and cov["R4_CITY_BG"]==1510 and cov["R5"]==61):
 raise RuntimeError("Integrated independently source-confirmed counts failed "+str(cov))
if any(row["正式剔除"]!="否" for row in rows):raise RuntimeError("No provisional county may be excluded")
def write_csv(path,items):
 with path.open("w",encoding="utf-8-sig",newline="") as f:
  wr=csv.DictWriter(f,fieldnames=list(items[0]),extrasaction="ignore")
  wr.writeheader();wr.writerows(items)
out=OUT/"national_R0_R5_unified_2847_county_evidence_and_missing.csv";write_csv(out,rows)
prov=OUT/"national_R0_R5_by_province_evidence_coverage.csv"
prows=[{"省级代码":p,"候选数":c["total"],"R1部分":c["R1"],"R2部分":c["R2"],"R3部分":c["R3"],"R4县级空气PM25":c["R4_COUNTY"],"R4市级空气背景":c["R4_CITY_BG"],"R5水源或末梢":c["R5"],"R1R2R3R4R5均有部分证据":c["all_5_partial"],"五轮均缺":c["all_5_missing"]} for p,c in sorted(regions.items())]
write_csv(prov,prows)
# Need extra evidence-rich subset to focus next local validation without claiming suitability.
ranked=sorted(rows,key=lambda x:(-x["已获地方直接或点位证据轮数"], -x["R4上级城市背景单独计"], x["县级候选代码_临时"]))
subset=OUT/"national_R0_R5_high_evidence_local_followups.csv"
write_csv(subset,ranked[:150])
report={"schema":"RET_NATIONWIDE_2847_COUNTIES_R0_R5_SOURCE_QUALITY_CONSOLIDATED_V1",
 "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_files_sha256":{key:hashfile(path) for key,path in P.items()},
 "provisional_counties_total":2847,
 "joined_source_counts":dict(cov),
 "R1_longer_87_short_127":True,"R2_longer_73_short_126":True,
 "R3_stations_198_counties_DEM_12_overlap5":True,
 "R4_58_official_county_PM25_2025_and_city_1510_context_separate":True,
 "R5_56_Fujian_source_1_Mengzi_tap_4_crossprovince_tap":True,
 "province_rows":len(prows),
 "county_integrated_csv_sha256":hashfile(out),
 "province_csv_sha256":hashfile(prov),
 "high_evidence_150_followups_csv_sha256":hashfile(subset),
 "all_5_partial_counties":cov["all_5_partial"],
 "R1_R2_R3_overlap_counties":cov["R1_R2_R3_overlap"],
 "formal_valid_county_screenings":0,"confirmed_exclusions":0,"all_carry_forward":2847,
 "official_2026_legal_country_wide_roster_verified":False,
 "note":"PROVISIONAL EVIDENCE COVERAGE TABLE ONLY. Ranking is completeness, NOT climate suitability. 2025 MEE city PM values are visually transcribed and second review pending.",
 "limits":["No threshold exclusions; pending ≠ failed","Short 15-year station series is NOT 1991-2020 standard climate normal",
 "Station/DEM altitude is NOT dwelling altitude","City PM is NOT county PM","Raw water intake classIII is NOT household tap safety",
 "2025 partial observations do NOT prove decades-long pollution suitability","Formal Library Master remains unchanged"]}
(OUT/"national_R0_R5_unified_evidence_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["provisional_counties_total","joined_source_counts","all_5_partial_counties","R1_R2_R3_overlap_counties","province_rows","formal_valid_county_screenings"]},ensure_ascii=False),flush=True)
