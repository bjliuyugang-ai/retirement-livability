#!/usr/bin/env python3
"""V1.6 event/transaction for user-authorized Stage-3 first-batch pre-screen.

User decision: Stage-2 11-point preliminary evidence is sufficient to TEST
screening now; do not wait for full CMA+2026 official confirmation.
This is a procedural fast-track, NOT a declaration of quality PASS and NOT
a waiver of formal A-D criteria or nationwide screening requirements.
"""
import datetime,hashlib,json,os,pathlib,subprocess,sys
T="6aead9a989808191ad42f80fd4e32bf1"
BASE=pathlib.Path("tasks")/T/"phase1"
STATE=BASE/"RUN_STATE.json";LOG=BASE/"RUN_LOG.jsonl"
CURRENT=pathlib.Path("research_assets/retirement/CURRENT_STATE.md")
OUTPUT=pathlib.Path("research_engine/retirement/output")
REPORT=OUTPUT/"first_batch_prescreen.json"
CSV=OUTPUT/"first_batch_prescreen_counties.csv"
DEST=pathlib.Path("research_engine/retirement/status/latest-first-batch-prescreen.json")
DESTCSV=pathlib.Path("research_engine/retirement/status/first-batch-prescreen-counties.csv")
RUN=os.getenv("GITHUB_RUN_ID","LOCAL-MANUAL")
ACTIVE="RET-CMA-ERA5-CROSSCHECK-003"
ACTION="RET-STAGE3-FIRSTBATCH-001"
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def blob(path):return subprocess.check_output(["git","hash-object",str(path)],text=True).strip()
def write(path,d):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def log(d):
 with LOG.open("a",encoding="utf-8") as f:f.write(json.dumps(d,ensure_ascii=False,sort_keys=True)+"\n")
def read(post=False):
 if not all(x.exists() for x in [STATE,CURRENT,LOG]):raise RuntimeError("STATE_MISSING")
 s=json.loads(STATE.read_text(encoding="utf-8"))
 if s.get("task_id")!=T or s.get("schema_version")!="1.6":raise RuntimeError("STATE_SCHEMA_INVALID")
 if blob(CURRENT)!=s["current_state_ref"]["git_blob_sha"]:raise RuntimeError("STATE_DRIFT_CURRENT_BLOB")
 if not post:
  if s["active_action"].get("action_id")!=ACTIVE:raise RuntimeError("ACTIVE_ACTION_CHANGE_OR_ALREADY_PROCESSED")
  if s["writeback_verification"].get("status")!="POSTCHECK_PASS":raise RuntimeError("PREVIOUS_WRITE_UNVERIFIED")
  if s["last_completed_action_id"]!="RET-CLIMATE-SPATIAL-REPRESENTATIVENESS-002":
   raise RuntimeError("PREVIOUS_CLIMATE_SPATIAL_ENGINEERING_NOT_PASSED")
 else:
  if s["writeback_verification"]["status"]!="PENDING_REMOTE_CHECK":raise RuntimeError("POSTCHECK_NOT_PENDING")
  if s["last_verified_run"]["run_id"]!=RUN:raise RuntimeError("POSTCHECK_RUN_MISMATCH")
 return s
def precheck():
 s=read()
 for p in [REPORT,CSV]:
  if p.exists():p.unlink()
 write(OUTPUT/"first_batch_precheck.json",{"run_id":RUN,"start":NOW(),
  "source_revision":s["state_revision"],"current_blob":blob(CURRENT),"state_hash":sha(STATE),
  "claimed_action":ACTION,"deferred_unresolved_action":ACTIVE,"source_commit":os.environ.get("GITHUB_SHA"),
  "user_decision":"Do not wait for 12-point perfection; start Stage-3 first-batch validation with 11 preliminary points"})
def finalize():
 s=read()
 if not REPORT.exists() or not CSV.exists():raise RuntimeError("SCREEN_COMPUTATION_OUTPUT_MISSING")
 report=json.loads(REPORT.read_text(encoding="utf-8"))
 if (report.get("preliminary_point_records")!=11 or
     report.get("stage3_preliminary_county_units")!=4 or
     report.get("valid_county_screenings")!=0 or report.get("formal_a_b_c_d_count")!=0 or
     len(report.get("county_rows",[]))!=4 or
     len(report.get("point_rows",[]))!=11 or
     any(x.get("formal_county_screening_valid") is not False for x in report["county_rows"])):
  raise RuntimeError("PRE_SCREEN_EVIDENCE_OR_FORMAL_GRADE_GUARD_FAIL")
 DEST.parent.mkdir(parents=True,exist_ok=True);DEST.write_bytes(REPORT.read_bytes())
 DESTCSV.write_bytes(CSV.read_bytes())
 result="RES-STAGE3-11POINT-FIRSTBATCH-"+RUN
 s.setdefault("deferred_actions",[]).append({"action_id":ACTIVE,"status":"DEFERRED_BY_EXPLICIT_USER_DECISION",
   "reason":"11 preliminary data points sufficient to test first-batch screening; unresolved CMA/official-code checks retained as formal blockers",
   "deferred_at":NOW(),"may_revisit_for_formal_grade":True})
 s["last_completed_action_id"]=ACTION;s["closed_result_refs"].append(result)
 s["consecutive_no_delta"]=0
 s["phase"]="STAGE3_FIRST_BATCH_SCREENING_VALIDATION"
 s["active_action"]={"action_id":"RET-STAGE3-EVIDENCE-GAPS-002",
   "question_id":"Q-FIRST-VALID-COUNTY-SCREEN",
   "decision":"从4县域11点初筛真实结果出发，逐项核验最有希望的候选住宅片区及其空气、水、污染和地灾底线，判断有无首批正式有效县级广筛",
   "method":"先用本轮11点的候选区位分层缩小范围；核对现行官方代码、独立气候站、住宅海拔、空气/饮水/污染/灾害，缺口逐项待核",
   "expected_evidence":"已冻结的4县域初筛结果、具体居住片区的来源与质量差集、第一批达标或待核判定",
   "pass_criteria":"真实住宅片区与正式质量底线全项合格才允许计入有效县级广筛；不足留待核",
   "fallback":"不拿ERA5代替站点、不将县域海拔最高值作为全县淘汰，不改变原20片区暂定分级",
   "status":"READY","timebox_end":"2026-11-08T15:26:00Z"}
 with CURRENT.open("a",encoding="utf-8") as f:
  f.write("\n- "+result+": 用户明确授权从11个已有ERA5点位直接进入第三关方法验证。首次4个县域11点初筛已生成逐点偏好命中与县域风险分层（研究增量）；现行行政身份、CMA站点、住宅海拔、空气/水/污染/灾害未关闭，正式有效县级广筛仍为0。旧RET-CMA-ERA5-CROSSCHECK-003标记DEFERRED而非PASS。详见 "+str(DEST)+"。\n")
 s["current_state_ref"]["git_blob_sha"]=blob(CURRENT)
 s["state_revision"]+=1;s["updated_at"]=NOW()
 s["last_verified_run"]={"run_id":RUN,"action_id":ACTION,"result_id":result,
 "execution_status":"EXECUTED","engineering_status":"PASS",
 "research_delta_status":"DELTA_VERIFIED","research_closure_status":"OPEN",
 "evidence_path":str(DEST),"evidence_sha256":sha(DEST),
 "csv_evidence_path":str(DESTCSV),"csv_sha256":sha(DESTCSV),"status":"AWAITING_POSTCHECK"}
 s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK","verified_commit":None}
 write(STATE,s)
 pre=json.loads((OUTPUT/"first_batch_precheck.json").read_text(encoding="utf-8"))
 log({"kind":"S0-S5","run_id":RUN,"at":NOW(),"source_commit":pre["source_commit"],
 "source_revision":pre["source_revision"],"input_current_blob":pre["current_blob"],
 "claimed_action":ACTION,"deferred_action":ACTIVE,"reason":"USER_DIRECTED_STAGE3_FAST_TRACK",
 "command":"python research_engine/retirement/first_batch_prescreen.py",
 "evidence_path":str(DEST),"evidence_sha256":sha(DEST),
 "csv_path":str(DESTCSV),"csv_sha256":sha(DESTCSV),
 "valid_county_screenings":0,"point_records":11,"county_units":4,
 "execution_status":"EXECUTED","engineering_status":"PASS","research_delta_status":"DELTA_VERIFIED",
 "research_closure_status":"OPEN","result_id":result,
 "next_action_id":s["active_action"]["action_id"],"writeback":"PENDING_REMOTE_CHECK"})
 print(json.dumps({"engineering":"PASS","research_delta":"DELTA_VERIFIED","stage3_preliminary_counties":4,
                   "point_records":11,"formal_county_screenings":0,
                   "next_action":s["active_action"]["action_id"]},ensure_ascii=False))
def postcheck():
 s=read(post=True)
 remote=json.loads(subprocess.check_output(["git","show","origin/main:"+str(STATE)],text=True))
 if remote["state_revision"]!=s["state_revision"] or remote["last_verified_run"]["run_id"]!=RUN:
  raise RuntimeError("REMOTE_STATE_MISMATCH")
 if remote["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("REMOTE_CURRENT_BLOB_DRIFT")
 for path,key in [(DEST,"evidence_sha256"),(DESTCSV,"csv_sha256")]:
  b=subprocess.check_output(["git","show","origin/main:"+str(path)])
  if hashlib.sha256(b).hexdigest()!=s["last_verified_run"][key]:
   raise RuntimeError("REMOTE_OUTPUT_HASH_MISMATCH: "+str(path))
 ll=subprocess.check_output(["git","show","origin/main:"+str(LOG)],text=True).splitlines()
 if not any(json.loads(z).get("run_id")==RUN and json.loads(z).get("kind")=="S0-S5" for z in ll if z.strip()):
  raise RuntimeError("LOG_NOT_PERSISTED")
 s["writeback_verification"]={"status":"POSTCHECK_PASS",
  "verified_commit":subprocess.check_output(["git","rev-parse","origin/main"],text=True).strip(),
  "verified_at":NOW()}
 s["last_verified_run"]["status"]="POSTCHECK_PASS"
 s["updated_at"]=NOW();s["state_revision"]+=1
 write(STATE,s)
 log({"kind":"S6_POSTCHECK","run_id":RUN,"action_id":ACTION,"at":NOW(),"postcheck":"PASS",
      "state_revision":s["state_revision"],"official_county_screenings":0})
if __name__=="__main__":
 try:{"precheck":precheck,"finalize":finalize,"postcheck":postcheck}[sys.argv[1]]()
 except Exception as e:print("V1.6_STAGE3_GATE_FAIL",repr(e),file=sys.stderr);sys.exit(2)
