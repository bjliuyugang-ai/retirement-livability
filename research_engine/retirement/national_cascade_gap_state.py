#!/usr/bin/env python3
"""V1.6 verified final gap audit for early nationwide R0-R5 parameter cascade.

This closes *pilot method handoff* not the official stage1 national research.
"""
import datetime,hashlib,json,os,pathlib,subprocess,sys
T="6aead9a989808191ad42f80fd4e32bf1";A="RET-CASCADE-NATIONAL-GAP-AUDIT-001"
BASE=pathlib.Path("tasks")/T/"phase1"
STATE=BASE/"RUN_STATE.json";LOG=BASE/"RUN_LOG.jsonl"
CURRENT=pathlib.Path("research_assets/retirement/CURRENT_STATE.md")
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output"
IN=OUT/"national_cascade_gap_coverage_audit.json"
CSV=OUT/"national_cascade_all_2847_audit.csv"
PROV=OUT/"national_cascade_province_coverage.csv"
DEST=ROOT/"status/national_cascade_gap_coverage_audit.json"
DCSV=ROOT/"status/national_cascade_all_2847_audit.csv"
DPROV=ROOT/"status/national_cascade_province_coverage.csv"
RUN=os.getenv("GITHUB_RUN_ID","LOCAL")
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(p):return subprocess.check_output(["git","hash-object",str(p)],text=True).strip()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def log(d):
 with LOG.open("a",encoding="utf-8") as f:f.write(json.dumps(d,ensure_ascii=False,sort_keys=True)+"\n")
def gate(post=False):
 if not all(p.exists() for p in [STATE,LOG,CURRENT]):raise RuntimeError("V16_MISSING_INPUT")
 s=json.loads(STATE.read_text(encoding="utf-8"))
 if s.get("schema_version")!="1.6" or s.get("task_id")!=T:raise RuntimeError("STATE_SCHEMA_INVALID")
 if s["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("SOURCE_CURRENT_DRIFT")
 if not post:
  if s["active_action"]["action_id"]!=A:raise RuntimeError("UNIQUE_ACTION_WRONG")
  if s["last_completed_action_id"]!="RET-CASCADE-NATIONAL-R5-001":raise RuntimeError("R5_NOT_COMPLETED")
  if s["writeback_verification"]["status"]!="POSTCHECK_PASS":raise RuntimeError("R5_NOT_VERIFIED")
 else:
  if s["writeback_verification"]["status"]!="PENDING_REMOTE_CHECK" or s["last_verified_run"]["run_id"]!=RUN:
   raise RuntimeError("GAP_POSTCHECK_NOT_PENDING_OR_WRONG_RUN")
 return s
def precheck():
 s=gate()
 for p in [IN,CSV,PROV]:
  if p.exists():p.unlink()
 write(OUT/"national_gap_precheck.json",{"run_id":RUN,
 "source_rev":s["state_revision"],"source_current_blob":blob(CURRENT),
 "source_commit":os.getenv("GITHUB_SHA"),"at":NOW()})
def finalize():
 s=gate()
 if any(not p.exists() for p in [IN,CSV,PROV]):raise RuntimeError("AUDIT_OUTPUT_MISSING")
 d=json.loads(IN.read_text(encoding="utf-8"))
 if not(d["provisional_input_counties"]==2847
  and d["provisional_counties_with_some_real_parameter_evidence"]==22
  and d["provisional_counties_with_zero_parameter_evidence"]==2825
  and [d["R1_with_real_point_temperature"],d["R2_with_point_sun_rain"],d["R3_with_three_point_DEM"],d["R4_with_city_or_regional_air_context"],d["R5_with_named_tap_observations_counties"]]==[22,12,12,2,1]
  and d["confirmed_exclusions"]==0
  and d["cumulative_R1_to_R5_carry_forward"]==2847
  and d["formal_valid_county_screenings"]==0 and d["formal_grades_modified"]==0
  and d["R1_api_failed_candidate_count"]==20
  and d["official_current_2026_county_roster_certified"] is False
  and sha(CSV.read_bytes())==d["output_all_counties_csv_sha256"]
  and sha(PROV.read_bytes())==d["output_by_province_csv_sha256"]):
  raise RuntimeError("AUDIT_COUNTS_OR_SOURCE_FILE_SHA_BAD")
 DEST.parent.mkdir(parents=True,exist_ok=True)
 for source,dest in [(IN,DEST),(CSV,DCSV),(PROV,DPROV)]:dest.write_bytes(source.read_bytes())
 result="RES-NATIONAL-2847-FIVE-ROUND-COVERAGE-GAP-AUDIT-"+RUN
 s["last_completed_action_id"]=A;s["closed_result_refs"].append(result);s["consecutive_no_delta"]=0
 s["phase"]="NATIONWIDE_DATA_COVERAGE_SCALE_ASSAULT"
 s["active_action"]={"action_id":"RET-CASCADE-NATIONAL-SOURCE-SCALE-002",
 "question_id":"Q_R1_R5_TRUE_NATIONWIDE_DATA_COVERAGE",
 "decision":"扩大跨省真实R1自然条件数据覆盖，重点解决2825县级候选完全无气候/环境参数证据和Open-Meteo HTTP429批量限流；不得继续围绕少数城市重复细节查询",
 "method":"优先寻找可复核的全国县级或格网历史气候大批量数据源、缓存策略与节流/合法授权接口；按独立区域批次可重复计算，并保留官方县级代码更新差集。每次实际新增点位后再接续R2—R5；缺失不阻塞其他地区",
 "expected_evidence":"每次取得跨省多地真实温度或其他自然参数证据，更新全国2847台账的真实测得数、未扫描数、失败分类，并给出来源、基期、位置及正式与探索性区别",
 "pass_criteria":"新增可量化真实取数覆盖且逐轮过账一致；不以新工具、源列表或计划当成果；单一方法限流连续两次必须切换",
 "fallback":"若现有ERA5接口HTTP429持续，则换可合法下载的公开气候数据源或已缓存数据，不重复耗尽配额",
 "status":"READY","timebox_end":"2026-11-08T15:26:00Z"}
 with CURRENT.open("a",encoding="utf-8") as f:
  f.write("\n- "+result+": 全国逐参数R1—R5执行与缺失总审计已完成（不是全国正式有效广筛验收）：R0临时在册2847县级候选，R1真实ERA5点位22、R2真实日照雨量点位12、R3真实DEM多点县域12、R4仅区域空气/污染来源2、R5仅官方命名末梢水观测县域1；总计仅22候选具有至少一种参数真实探索证据，2825完全没有任何参数，20个新取数点因HTTP429失败。确证淘汰0、继续2847、正式有效县级广筛0。已保留全部缺口、失败、按省份覆盖、复活条件和历史档案。任务转为跨省真实数据覆盖攻坚，不在少数区域反复补细节。完整："+str(DCSV)+"；摘要："+str(DEST)+"；按省份："+str(DPROV)+"。\n")
 s["current_state_ref"]["git_blob_sha"]=blob(CURRENT);s["state_revision"]+=1;s["updated_at"]=NOW()
 s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK","verified_commit":None}
 s["last_verified_run"]={"run_id":RUN,"action_id":A,"result_id":result,
 "execution_status":"EXECUTED","engineering_status":"PASS",
 "research_delta_status":"DELTA_VERIFIED_2847_COUNTY_PARAMETER_COVERAGE_AND_GAP_AUDIT",
 "research_closure_status":"OPEN",
 "evidence_path":str(DEST),"evidence_sha256":sha(DEST.read_bytes()),
 "csv_path":str(DCSV),"csv_sha256":sha(DCSV.read_bytes()),
 "province_coverage_path":str(DPROV),"province_coverage_sha256":sha(DPROV.read_bytes()),
 "status":"AWAITING_POSTCHECK"}
 s["national_cascade_gap_audit"]={"provisional_counties":2847,
 "any_parameter_evidence_counties":22,"none_evidence_counties":2825,
 "R1_R5_true_partial_evidence_counts":[22,12,12,2,1],
 "R1_api_failed_429_count":20,"confirmed_exclusions":0,"carry_forward":2847,
 "formal_valid_county_screenings":0,"official_2026_denominator_verified":False,
 "evidence_path":str(DEST),"county_audit_csv":str(DCSV),"province_coverage_csv":str(DPROV)}
 write(STATE,s)
 pre=json.loads((OUT/"national_gap_precheck.json").read_text(encoding="utf-8"))
 log({"kind":"S0-S5","run_id":RUN,"action_id":A,"source_revision":pre["source_rev"],
 "source_commit":pre["source_commit"],"source_current_blob":pre["source_current_blob"],
 "command":"python research_engine/retirement/national_cascade_gap_audit.py",
 "evidence_path":str(DEST),"evidence_sha256":sha(DEST.read_bytes()),
 "county_csv_path":str(DCSV),"county_csv_sha256":sha(DCSV.read_bytes()),
 "province_csv_path":str(DPROV),"province_csv_sha256":sha(DPROV.read_bytes()),"at":NOW(),
 "total":2847,"R1_R5_evidence":[22,12,12,2,1],"all_zero":2825,
 "R1_429":20,"confirmed_exits":0,"carry_forward":2847,"formal_valid_county_screenings":0,
 "engineering_status":"PASS","research_delta_status":"DELTA_VERIFIED",
 "research_closure_status":"OPEN","next_action_id":"RET-CASCADE-NATIONAL-SOURCE-SCALE-002",
 "result_id":result,"writeback":"PENDING_REMOTE_CHECK"})
 print(json.dumps({"counties":2847,"any_real_evidence":22,"none":2825,"round_coverage":[22,12,12,2,1],"next":"SCALE_TRUE_DATA_COVERAGE"},ensure_ascii=False))
def postcheck():
 s=gate(post=True)
 remote=json.loads(subprocess.check_output(["git","show","origin/main:"+str(STATE)],text=True))
 if remote["state_revision"]!=s["state_revision"] or remote["last_verified_run"]["run_id"]!=RUN:
  raise RuntimeError("REMOTE_STATE_MISMATCH")
 if remote["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("REMOTE_CURRENT_DRIFT")
 for p,key in [(DEST,"evidence_sha256"),(DCSV,"csv_sha256"),(DPROV,"province_coverage_sha256")]:
  if sha(subprocess.check_output(["git","show","origin/main:"+str(p)]))!=s["last_verified_run"][key]:
   raise RuntimeError("REMOTE_FILE_SHA_MISMATCH")
 lines=subprocess.check_output(["git","show","origin/main:"+str(LOG)],text=True).splitlines()
 if not any(json.loads(z).get("run_id")==RUN and json.loads(z).get("kind")=="S0-S5" for z in lines if z.strip()):
  raise RuntimeError("REMOTE_LOG_MISSING")
 s["writeback_verification"]={"status":"POSTCHECK_PASS",
 "verified_commit":subprocess.check_output(["git","rev-parse","origin/main"],text=True).strip(),
 "verified_at":NOW()}
 s["last_verified_run"]["status"]="POSTCHECK_PASS";s["state_revision"]+=1;s["updated_at"]=NOW()
 write(STATE,s)
 log({"kind":"S6_POSTCHECK","run_id":RUN,"action_id":A,"postcheck":"PASS",
 "state_revision":s["state_revision"],"R1_R5_evidence_counts":[22,12,12,2,1],
 "any_evidence":22,"none":2825,"formal":0,"at":NOW()})
if __name__=="__main__":
 try:{"precheck":precheck,"finalize":finalize,"postcheck":postcheck}[sys.argv[1]]()
 except Exception as e:print("V16_NATIONAL_AUDIT_GATE_FAIL",repr(e),file=sys.stderr);sys.exit(2)
