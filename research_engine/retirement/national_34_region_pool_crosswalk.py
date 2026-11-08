#!/usr/bin/env python3
"""Crosswalk only the named Phase-1 residential candidate regions to the 214 existing R1 evidence points.
Also repair the altitude-flag join in the 214-row register from the authoritative 73+127 batch files.
"""
from __future__ import annotations
import csv,json,hashlib,datetime,pathlib,collections
S=pathlib.Path("research_engine/retirement/status")
P214=S/"national_214_R1_all_evidence_hard_screen_20261108.csv"
SUM214=S/"national_214_R1_hardline_signal_rollup_20261108.json"
A73=S/"national_73_existing_evidence_hard_screen_20261108.csv"
A127=S/"national_127_short_history_R1_hard_screen_20261108.csv"
OUT214=S/"national_214_R1_all_evidence_hard_screen_20261108.csv"
OUTSUM=S/"national_214_R1_hardline_signal_rollup_20261108.json"
OUTREG=S/"national_40_named_region_candidate_crosswalk_20261108.csv"
OUTJSON=S/"national_40_named_region_candidate_crosswalk_20261108.json"

def readcsv(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def writecsv(p,rows):
 with p.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def yes(v):return str(v).strip().lower() in ("true","1","yes")
def num(v):
 if v is None or str(v).strip()=="":return None
 try:return float(v)
 except:return None

# 29 original residential samples. Status and wording are inherited from the current
# V2 workbook; this script does not silently change their original evidence status.
CORE=[
("云南","昆明主城区","530102;530112","优先保留｜样点四项通过","市中心样点温度/日照/海拔通过；周边高地须分片"),
("云南","大理古城／洱海湖滨盆地","532901","条件保留｜统一基期/分片后确认","住宅海拔跨越2000m，必须按湖滨实际住宅点分片"),
("云南","蒙自坝区／城区","532503","优先保留｜样点四项通过","坝区城区约1300m；周边山地不能外推"),
("四川","西昌城区","513401","优先保留｜样点四项通过","样点四项有通过信号；日照与温度来源需持续交叉核"),
("海南","五指山市通什城区","469001","优先保留｜样点四项通过","已有较强1991-2020逐日证据；保留"),
("广西","北海市区","450502;450503","条件保留｜统一基期/分片后确认","温度/日照统计期拼接，需统一基期"),
("广西","百色城区","451002","条件保留｜统一基期/分片后确认","温度与日照来源需统一核验"),
("云南","楚雄市鹿城镇","532301","条件保留｜统一基期/分片后确认","温度/日照资料统计期偏旧"),
("云南","普洱市思茅区","530802","条件保留｜统一基期/分片后确认","温度/日照资料统计期偏旧"),
("云南","弥勒城区","532504","条件保留｜统一基期/分片后确认","日照来源和统计期需回溯"),
("云南","芒市城区","533103","条件保留｜统一基期/分片后确认","日照来源和统计期需回溯"),
("广西","靖西市新靖镇／城区","451025","待核｜单项补证","温度已有通过信号；只补日照"),
("云南","保山市隆阳区城区","530502","待核｜单项补证","温度最冷/最热月指标待补"),
("云南","玉溪·新平桂山街道／县城","530427","待核｜单项补证","河谷/半山/高山必须分片；温度待补"),
("云南","玉溪·红塔区中心城区","530402","待核｜单项补证","最冷/最热月平均日最高温待补"),
("云南","红河州·建水坝区","532524","待核｜单项补证","最热月平均日最高温待补"),
("四川","攀枝花·米易县城","510421","待核｜单项补证","只做一次最热月平均日最高温核验"),
("海南","三亚市区","460203;460204;460205","硬线触发｜退出该样点候选池","既有1991-2020最热月平均日最高温32.5℃，样点退出"),
("海南","琼海市嘉积镇／城区","469002","硬线触发｜退出该样点候选池","既有最热月平均日最高温33.6℃，样点退出"),
("海南","万宁市城区","469006","硬线触发｜退出该样点候选池","既有最热月平均日最高温32.6℃，样点退出"),
("海南","海口市区","460105;460106;460107;460108","硬线触发｜退出该样点候选池","既有最热月平均日最高温33.6℃，样点退出"),
("四川","攀枝花主城区／低海拔河谷","510402;510403;510411","硬线触发｜退出该样点候选池","既有最热月平均日最高温32.9℃，只退出该低海拔主城区样点"),
("云南","西双版纳·景洪城区","532801","硬线触发｜退出该样点候选池","既有1991-2020多个热月平均日最高温≥32℃，样点退出"),
("福建","霞浦县城近海片区","350921","硬线触发｜退出该样点候选池","既有日照1690.4h且最热月32.3℃；二次来源待原始复核"),
("陕西","勉县县城","610725","硬线触发｜退出该样点候选池","既有2001-2020日照1396h；统计期需复核"),
("湖北","利川城区","422802","硬线触发｜退出该样点候选池","既有最冷月平均日最高温5.8/8.0℃；待官方站值复核"),
("北京","北京市区","110101;110102;110105;110106;110108;110109;110111","硬线触发｜退出该样点候选池","北方冬季样点硬线触发；只作为北京代表样点"),
("黑龙江","哈尔滨市区","230102;230103;230104;230108;230109;230110","硬线触发｜退出该样点候选池","既有冬季平均日最高温远低于10℃"),
("吉林","长春市区","220102;220103;220104;220105;220106","硬线触发｜退出该样点候选池","既有冬季平均日最高温远低于10℃")
]
EXP=[
("贵州","贞丰县城","522326","待核，暂留","缺少统一基期海拔/日照/温度；不耗时单点深挖"),
("广西","南丹县城","451221","冬季优先核验","高地夏凉与冬季偏冷冲突；先看冬季温度"),
("广西","资源县城","450329","冬季优先核验","山地冬湿冷风险；缺统一日最高温"),
("广东","乳源县城","440232","待核，暂留","核实际居住海拔和夏季温度"),
("福建","霞浦县城近海片区","350921","硬线触发｜待原始数据复核","与核心29重复，保留原始双硬线记录"),
("福建","建瓯县级市城区","350783","待核，暂留","近年天气资料不能替代气候常年值"),
("江西","龙南县城","360783","待核，暂留","冬季可能较暖，夏季热风险待批量核验"),
("湖南","桂东县城","431027","冬季优先核验","高地夏凉与冬季偏冷并存"),
("湖北","利川城区","422802","硬线触发｜待原始数据复核","与核心29重复，冬季温度触线"),
("陕西","勉县县城","610725","硬线触发｜待统一基期复核","与核心29重复，日照明显偏低"),
("甘肃","武都城区及台地","621202","待核，暂留","低海拔河谷冬暖潜力，夏季热风险待核"),
("新疆","伊宁市城区","654002","冬季高风险待核","先做一次冬季温度核验"),
("山东","荣成城区","371082","冬季强风险待核","现有月平均气温不能替代平均日最高温"),
("西藏","墨脱县城","540423","待核，暂留","先做低成本海拔/日照快速筛")
]

def main():
 all214=readcsv(P214);a73=readcsv(A73);a127=readcsv(A127)
 if len(all214)!=214 or len({x["candidate_code"] for x in all214})!=214:raise RuntimeError("214 register invalid")
 # Repair the previous rollup's altitude join: source header contains _over_2000m_.
 alt73={x["candidate_code"]:yes(x.get("altitude_point_over_2000m_signal")) for x in a73}
 alt127={x["candidate_code"]:yes(x.get("altitude_point_over2000m_warning")) for x in a127}
 for x in all214:
  if x["history_tier"].startswith("LONGER_SOURCE_1991_2020"):
   x["altitude_point_over2000m_warning"]=str(alt73.get(x["candidate_code"],False))
  elif x["history_tier"].startswith("INTERIM_180_MONTHS"):
   x["altitude_point_over2000m_warning"]=str(alt127.get(x["candidate_code"],False))
 writecsv(OUT214,all214)
 # Recompute counts after correction.
 climate=[x for x in all214 if yes(x["winter_lt10_signal"]) or yes(x["summer_ge32_signal"]) or yes(x["sunshine_lt1800_signal"])]
 alt=[x for x in all214 if yes(x["altitude_point_over2000m_warning"])]
 sunmeas=sum(num(x.get("annual_sunshine_hours")) is not None for x in all214)
 union_codes={x["candidate_code"] for x in climate+alt}
 summary=json.loads(OUTSUM.read_text(encoding="utf-8"))
 summary["all_214_counts"]["altitude_point_over2000m_warning"]=len(alt)
 summary["all_214_counts"]["climate_or_altitude_point_warning_union"]=len(union_codes)
 summary["all_214_counts"]["annual_sunshine_measured"]=sunmeas
 summary["all_214_counts"]["annual_sunshine_missing"]=214-sunmeas
 summary["all_214_counts"]["altitude_point_only_not_climate_signal"]=len({x["candidate_code"] for x in alt}-{x["candidate_code"] for x in climate})
 summary["altitude_join_correction"]={
  "corrected":True,"source_73_field":"altitude_point_over_2000m_signal",
  "source_127_field":"altitude_point_over2000m_warning",
  "altitude_point_warnings_73":sum(alt73.values()),
  "altitude_point_warnings_127":sum(alt127.values()),
  "altitude_point_warnings_14_long_R1_only":sum(yes(x["altitude_point_over2000m_warning"]) for x in all214 if x["history_tier"].startswith("LONGER_R1_ONLY")),
  "note":"Residential altitude is still not verified; this is a point warning only."
 }
 summary["source_sha256"]["corrected_214_csv"]=sha(OUT214)
 OUTSUM.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 bycode={x["candidate_code"]:x for x in all214}
 records={}
 for prov,name,codes,status,reason in CORE+EXP:
  key=name
  if key not in records:
   records[key]={"province":prov,"region_unit":name,"candidate_codes":codes.split(";"),
    "source_lists":[],"original_statuses":[],"original_reasons":[]}
  z=records[key]
  z["source_lists"].append("CORE_29" if (prov,name,codes,status,reason) in CORE else "EXPANSION_14")
  z["original_statuses"].append(status);z["original_reasons"].append(reason)
 out=[]
 for name,z in records.items():
  matched=[c for c in z["candidate_codes"] if c in bycode]
  rows=[bycode[c] for c in matched]
  climate_codes=[x["candidate_code"] for x in rows if yes(x["winter_lt10_signal"]) or yes(x["summer_ge32_signal"]) or yes(x["sunshine_lt1800_signal"])]
  altitude_codes=[x["candidate_code"] for x in rows if yes(x["altitude_point_over2000m_warning"])]
  sun_missing=[x["candidate_code"] for x in rows if num(x.get("annual_sunshine_hours")) is None]
  existing_exit=any("退出该样点" in s or "硬线触发" in s for s in z["original_statuses"])
  multi=len(z["candidate_codes"])>1
  if existing_exit:
   decision="已有样点硬线退出保留；原始来源复核，不因粗粒度站点无触线而恢复"
  elif climate_codes:
   decision="新增气候硬线信号；住宅点位核实后退出具体片区"
  elif altitude_codes:
   decision="海拔点位超2000m；按实际住宅点分片，超线部分退出"
  elif not matched:
   decision="无精确R1点位匹配；保持待核，不进入D档"
  elif sun_missing:
   decision="温度点位未见已测触线；日照缺失，保持待核"
  else:
   decision="已匹配点位未见当前硬线信号；保留进入下一轮"
  out.append({
   "province":z["province"],"region_unit":name,
   "source_lists":";".join(sorted(set(z["source_lists"]))),
   "original_status":";".join(dict.fromkeys(z["original_statuses"])),
   "candidate_codes":";".join(z["candidate_codes"]),
   "exact_R1_code_matches":";".join(matched),
   "unmatched_codes":";".join(c for c in z["candidate_codes"] if c not in bycode),
   "matched_R1_codes_with_climate_hardline_signal":";".join(climate_codes),
   "matched_codes_with_altitude_point_over2000m":";".join(altitude_codes),
   "matched_codes_missing_sunshine":";".join(sun_missing),
   "matched_code_count":len(matched),"mapping_scope":"MULTI_DISTRICT_OR_BASIN" if multi else "SINGLE_ADMIN_UNIT",
   "region_screening_decision":decision,
   "formal_residential_exclusion":False,
   "original_evidence_reason":" | ".join(dict.fromkeys(z["original_reasons"])),
   "matched_evidence_values":" | ".join(f'{x["candidate_code"]}:冬季={x["winter_mean_daily_tmax_c"]},夏季={x["summer_mean_daily_tmax_c"]},日照={x["annual_sunshine_hours"]},海拔点位警示={x["altitude_point_over2000m_warning"]}' for x in rows),
   "next_action":"仅对精确匹配且触线的具体住宅片区核实站点代表性；多区/盆地按住宅点拆分；无匹配转下一片区，不耗时追数"
  })
 if len(out)!=40:raise RuntimeError(f"Expected 40 de-duplicated region units, got {len(out)}")
 writecsv(OUTREG,out)
 counts=collections.Counter(x["region_screening_decision"] for x in out)
 summary2={
  "schema":"RET_PHASE1_NAMED_REGION_POOL_29_PLUS_14_CROSSWALK_V1",
  "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "input_counts":{"core_sample_records":len(CORE),"expansion_records":len(EXP),
   "input_records":len(CORE)+len(EXP),"deduplicated_named_region_units":len(out),
   "duplicate_region_records":len(CORE)+len(EXP)-len(out)},
  "R1_evidence_register":{"screened_candidate_points":214,"climate_hardline_signal_candidates":len(climate),
   "altitude_point_warnings":len(alt),"climate_or_altitude_point_warning_union":len(union_codes),
   "sunshine_measured":sunmeas,"sunshine_missing":214-sunmeas},
  "region_crosswalk_counts":{
   "units_with_any_exact_R1_code_match":sum(x["matched_code_count"]>0 for x in out),
   "units_with_no_exact_R1_code_match":sum(x["matched_code_count"]==0 for x in out),
   "units_with_matched_climate_hardline_signal":sum(bool(x["matched_R1_codes_with_climate_hardline_signal"]) for x in out),
   "units_with_altitude_point_warning":sum(bool(x["matched_codes_with_altitude_point_over2000m"]) for x in out),
   "units_already_marked_exit_in_V2":sum("退出该样点" in x["original_status"] or "硬线触发" in x["original_status"] for x in out)},
  "region_decision_counts":dict(counts),
  "region_results":[{"province":x["province"],"region_unit":x["region_unit"],
   "original_status":x["original_status"],"matched_codes":x["exact_R1_code_matches"],
   "climate_signal_codes":x["matched_R1_codes_with_climate_hardline_signal"],
   "altitude_warning_codes":x["matched_codes_with_altitude_point_over2000m"],
   "decision":x["region_screening_decision"]} for x in out],
  "governance":{"formal_residential_exclusions":0,"formal_county_screenings":0,
   "D_grade_not_used_as_hardline_bucket":True,"missing_parameters_remain_pending":True,
   "stage2_stage3_lists_not_reduced":True,"all_2847_carry_forward":True},
  "limitations":["214 are evidence-bearing county/point candidates, not all 2847 counties.",
   "Only exact code matches are joined; a district/station point does not certify an entire city, basin or residential micro-area.",
   "Existing V2 sample hardline exits are preserved even when a coarse 3-4 month mean does not independently reproduce the hottest/coldest-month signal.",
   "A point over 2000m is not a residential altitude exclusion until the actual dwelling area is verified.",
   "No-match areas remain pending; no single area is allowed to block the batch."]
 }
 OUTJSON.write_text(json.dumps(summary2,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"status":"PASS","R1_candidates":214,"climate_signal_candidates":len(climate),
  "altitude_point_warnings_corrected":len(alt),"climate_or_altitude_union":len(union_codes),
  "named_region_input_records":43,"named_region_units_deduplicated":len(out),
  "matched_region_units":summary2["region_crosswalk_counts"]["units_with_any_exact_R1_code_match"],
  "unmatched_region_units":summary2["region_crosswalk_counts"]["units_with_no_exact_R1_code_match"],
  "region_climate_signal_units":summary2["region_crosswalk_counts"]["units_with_matched_climate_hardline_signal"],
  "formal_exclusions":0},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
