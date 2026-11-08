#!/usr/bin/env python3
"""Turn the named 40-region crosswalk into a first-round keep / pending / hard-line exit queue."""
from __future__ import annotations
import csv,json,datetime,pathlib,collections
S=pathlib.Path("research_engine/retirement/status")
IN=S/"national_40_named_region_candidate_crosswalk_20261108.csv"
INJSON=S/"national_40_named_region_candidate_crosswalk_20261108.json"
OUT=S/"national_40_region_disposition_20261108.csv"
OUTJSON=S/"national_40_region_disposition_20261108.json"

def rd(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def wr(p,rows):
 with p.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

# Residential elevations already present in the current 29-sample evidence sheet.
# These override non-residential DEM high points when the actual named sample is known.
RES_ALT={
"昆明主城区":("约1891m","PASS_AT_NAMED_CENTRAL_RESIDENTIAL_SAMPLE","中心城区参考点低于2000m；DEM高点不能外推为住宅海拔"),
"大理古城／洱海湖滨盆地":("约1966—2100m","CROSS_2000M_SPLIT_REQUIRED","只保留实际住宅点≤2000m部分；>2000m住宅片区退出"),
"蒙自坝区／城区":("约1300m","PASS_AT_NAMED_RESIDENTIAL_SAMPLE","城区坝区住宅样点约1300m；周边山地DEM高点不外推"),
"西昌城区":("1591m","PASS_AT_NAMED_RESIDENTIAL_SAMPLE","住宅城区参考点低于2000m"),
"五指山市通什城区":("328.5m","PASS_AT_NAMED_RESIDENTIAL_SAMPLE","住宅城区参考点低于2000m"),
"北海市区":("低于2000m","PASS_REFERENCE_ONLY","仍需住宅点确认"),
"百色城区":("低于2000m","PASS_REFERENCE_ONLY","温度硬线存在冲突，海拔不是当前限制"),
"楚雄市鹿城镇":("1773m","PASS_AT_NAMED_RESIDENTIAL_SAMPLE","住宅镇区参考点低于2000m"),
"普洱市思茅区":("1302m","PASS_AT_NAMED_RESIDENTIAL_SAMPLE","住宅城区参考点低于2000m"),
"弥勒城区":("约1450m","PASS_REFERENCE_ONLY","住宅城区参考点低于2000m"),
"芒市城区":("约900m","PASS_REFERENCE_ONLY","住宅城区参考点低于2000m"),
"靖西市新靖镇／城区":("约700—850m","PASS_REFERENCE_ONLY","住宅城区参考点低于2000m"),
"保山市隆阳区城区":("1653.5m","PASS_REFERENCE_ONLY","住宅城区参考点低于2000m"),
"玉溪·新平桂山街道／县城":("约1480m","PASS_REFERENCE_ONLY","必须区分河谷/半山/高山住宅片区"),
"玉溪·红塔区中心城区":("约1630m","PASS_REFERENCE_ONLY","住宅城区参考点低于2000m"),
"红河州·建水坝区":("约1300m","PASS_REFERENCE_ONLY","住宅坝区参考点低于2000m"),
"攀枝花·米易县城":("约1200m","PASS_REFERENCE_ONLY","住宅县城参考点低于2000m"),
"攀枝花主城区／低海拔河谷":("约1225m","PASS_AT_NAMED_RESIDENTIAL_SAMPLE","海拔通过；夏季温度硬线仍触发"),
"利川城区":("约1074m","PASS_AT_NAMED_RESIDENTIAL_SAMPLE","冬季温度硬线触发"),
"北京市区":("约43m","PASS_AT_NAMED_RESIDENTIAL_SAMPLE","冬季温度硬线触发"),
"哈尔滨市区":("约150m","PASS_AT_NAMED_RESIDENTIAL_SAMPLE","冬季温度硬线触发"),
"长春市区":("约236m","PASS_AT_NAMED_RESIDENTIAL_SAMPLE","冬季温度硬线触发")
}
# Strong new hard-line signals from the 214-point evidence register.
# Baise is flagged as a source conflict because the current 29-sample sheet carries a different July value.
NEW_SIGNAL={
"百色城区":("SUMMER_GE_32C","33.017℃（Jun-Sep平均日最高温）；与现有31.0℃单月值冲突，须一次核对原始月表"),
"武都城区及台地":("WINTER_LT_10C","9.864℃（Dec-Feb平均日最高温）；对城区/台地住宅点做一次代表性确认"),
"伊宁市城区":("WINTER_LT_10C","0.776℃（Dec-Feb平均日最高温）；冬季硬线强信号"),
"荣成城区":("WINTER_LT_10C","3.694℃（Dec-Feb平均日最高温）；冬季硬线强信号")
}
def main():
 rows=rd(IN);source=json.loads(INJSON.read_text(encoding="utf-8"))
 if len(rows)!=40:raise RuntimeError(f"Expected 40 named region rows, got {len(rows)}")
 out=[]
 for x in rows:
  name=x["region_unit"];orig=x["original_status"]
  existing_exit=("退出该样点" in orig or "硬线触发" in orig)
  new=NEW_SIGNAL.get(name)
  altref,altstatus,altnote=RES_ALT.get(name,("待核","NOT_VERIFIED","住宅海拔未核；不得用县内DEM最高点替代住宅点"))
  # Existing V2 hard-line sample exits are preserved. New 214-point signals are kept
  # separate from formal exit until their point is tied to the actual residential site.
  if existing_exit:
   disposition="退出第一阶段该样点候选池"
   confidence="已有样点硬线触发；其中霞浦/勉县/利川仍须原始数据复核"
   next_step="不再为该样点做广泛补数；仅完成一次原始站值/统计期复核"
  elif name=="百色城区" and new:
   disposition="硬线冲突待一次复核（不进入D档）"
   confidence="现有样点单月31.0℃与214点位Jun-Sep平均日最高温33.017℃不一致"
   next_step="一次核对451002站1991-2020逐月平均日最高温；确认≥32℃即退出该城区样点，否则按原样点条件保留"
  elif new:
   disposition="新增硬线预排除（住宅点确认后退出）"
   confidence="214候选点位出现单向硬线信号；尚未证明站点即具体住宅点"
   next_step="一次核对站点与住宅片区位置；若同一居住片区则退出，不放D；若不同则只核住宅点一次"
  elif altstatus=="CROSS_2000M_SPLIT_REQUIRED":
   disposition="条件保留｜按2000m住宅海拔分片"
   confidence="实际住宅海拔范围跨越2000m"
   next_step="保留≤2000m湖滨住宅片区；>2000m住宅片区退出"
  elif altstatus.startswith("PASS"):
   if "优先保留" in orig:
    disposition="优先保留"
   elif "条件保留" in orig:
    disposition="条件保留"
   elif "待核" in orig:
    disposition="待核"
   else:
    disposition="待核"
   confidence="已知住宅海拔≤2000m；非住宅DEM高点不作为淘汰理由"
   next_step="继续按温度/日照/污染水质灾害缺项推进"
  elif x["matched_code_count"] and x["matched_codes_missing_sunshine"]:
   disposition="待核｜日照缺项"
   confidence="匹配温度点位未见已测硬线；日照缺失"
   next_step="仅补一次年日照；缺失则继续待核并转下一地区"
  elif x["matched_code_count"]:
   disposition="条件保留"
   confidence="匹配点位未触发已测气候硬线；仍需住宅点与缺项核验"
   next_step="进入后续环境/居住片区核验"
  else:
   disposition="待核｜无精确点位数据"
   confidence="当前214点位证据未覆盖该评价单元；不能按不合格处理"
   next_step="按省级优先级只做一轮批量补证；无数据则暂搁置"
  out.append({
   "province":x["province"],"region_unit":name,"source_lists":x["source_lists"],
   "candidate_codes":x["candidate_codes"],"matched_R1_codes":x["exact_R1_code_matches"],
   "original_V2_status":orig,"final_phase1_disposition":disposition,
   "new_hardline_signal":new[0] if new else "",
   "new_hardline_signal_value":new[1] if new else "",
   "matched_climate_signal_codes":x["matched_R1_codes_with_climate_hardline_signal"],
   "residential_altitude_reference":altref,"residential_altitude_status":altstatus,
   "nonresidential_DEM_warning_codes":x["matched_codes_with_altitude_point_over2000m"],
   "altitude_interpretation":altnote,
   "confidence_and_limit":confidence,"next_step":next_step,
   "formal_region_exclusion":False,
   "D_grade_used_as_hardline_bucket":False
  })
 wr(OUT,out)
 counts=collections.Counter(x["final_phase1_disposition"] for x in out)
 summary={
  "schema":"RET_PHASE1_40_NAMED_REGION_FINAL_DISPOSITION_DRAFT_V1",
  "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "source_crosswalk_result":source.get("schema"),
  "input_region_units":40,"disposition_counts":dict(counts),
  "existing_sample_hardline_exit_units":sum(x["final_phase1_disposition"]=="退出第一阶段该样点候选池" for x in out),
  "new_hardline_preexit_units":sum(x["final_phase1_disposition"]=="新增硬线预排除（住宅点确认后退出）" for x in out),
  "temperature_conflict_units":sum(x["final_phase1_disposition"]=="硬线冲突待一次复核（不进入D档）" for x in out),
  "altitude_split_units":sum(x["final_phase1_disposition"]=="条件保留｜按2000m住宅海拔分片" for x in out),
  "priority_keep_units":sum(x["final_phase1_disposition"]=="优先保留" for x in out),
  "formal_residential_exclusions":0,
  "next_batch_focus":["百色城区：核验33.017℃四月均值与现有31.0℃单月值冲突",
   "武都城区及台地：冬季9.864℃，确认站点与住宅点代表性",
   "伊宁市城区：冬季0.776℃，强硬线预排除",
   "荣成城区：冬季3.694℃，强硬线预排除",
   "霞浦、勉县、利川：完成一次原始来源/统计期复核；未复核前保留预排除，不恢复候选"],
  "governance":{"hardline_failures_not_D":True,"missing_parameters_pending":True,
   "phase2_phase3_lists_unchanged":True,"all_2847_carry_forward":True},
  "limitations":["This is a named residential-area disposition draft, not yet a final formal residential exclusion.",
   "The 214 evidence points are county/station/ERA5 points; they must be tied to the named dwelling micro-area.",
   "The 4 new hard-line signals are kept separate from the 12 existing V2 exits until one site-representativeness check.",
   "Kunming and Mengzi residential samples are below 2000m; their high DEM points are not residential altitude failures.",
   "Dali's named residential altitude range crosses 2000m and must be split.",
   "Missing values remain PENDING, never D or failed."]
 }
 OUTJSON.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"status":"PASS","regions":40,"existing_exits":summary["existing_sample_hardline_exit_units"],
  "new_preexit":summary["new_hardline_preexit_units"],"temperature_conflicts":summary["temperature_conflict_units"],
  "altitude_split":summary["altitude_split_units"],"priority_keep":summary["priority_keep_units"],
  "disposition_counts":dict(counts)},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
