#!/usr/bin/env python3
"""V1.6 S0-S6 nationwide R2 parameter handoff: 12 archived ERA5 sun/rain points."""
import datetime,hashlib,json,os,pathlib,subprocess,sys
TASK="6aead9a989808191ad42f80fd4e32bf1";ACTION="RET-CASCADE-NATIONAL-R2-001"
B=pathlib.Path("tasks")/TASK/"phase1"
STATE=B/"RUN_STATE.json";LOG=B/"RUN_LOG.jsonl"
CURRENT=pathlib.Path("research_assets/retirement/CURRENT_STATE.md")
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output"
SRC=OUT/"national_r2_first_real_batch_evidence.json"
CSRC=OUT/"national_r2_first_real_batch.csv"
DEST=ROOT/"status/national_r2_first_real_batch_evidence.json"
CDEST=ROOT/"status/national_r2_first_real_batch.csv"
RUN=os.getenv("GITHUB_RUN_ID","LOCAL")
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(p):return subprocess.check_output(["git","hash-object",str(p)],text=True).strip()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def log(d):
 with LOG.open("a",encoding="utf-8") as f:f.write(json.dumps(d,ensure_ascii=False,sort_keys=True)+"\n")
def read(post=False):
 if not all(p.exists() for p in [STATE,LOG,CURRENT]):raise RuntimeError("V1.6_STATE_MISSING")
 s=json.loads(STATE.read_text(encoding="utf-8"))
 if s["task_id"]!=TASK or s["schema_version"]!="1.6":raise RuntimeError("STATE_SCHEMA")
 if s["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("CURRENT_BLOB_DRIFT")
 if not post:
  if s["active_action"]["action_id"]!=ACTION:raise RuntimeError("UNIQUE_ACTION_WRONG")
  if s["writeback_verification"]["status"]!="POSTCHECK_PASS":raise RuntimeError("PREVIOUS_POSTCHECK_MISSING")
  if s["last_completed_action_id"]!="RET-CASCADE-NATIONAL-R1-EXPAND-002":raise RuntimeError("R1_EXPANSION_NOT_COMPLETE")
 else:
  if s["writeback_verification"]["status"]!="PENDING_REMOTE_CHECK":raise RuntimeError("NOT_PENDING_POSTCHECK")
  if s["last_verified_run"]["run_id"]!=RUN:raise RuntimeError("RUN_MISMATCH")
 return s
def precheck():
 s=read()
 for p in [SRC,CSRC]:
  if p.exists():p.unlink()
 write(OUT/"national_r2_precheck.json",{"run_id":RUN,"action_id":ACTION,
 "source_revision":s["state_revision"],"source_current_blob":blob(CURRENT),
 "source_commit":os.getenv("GITHUB_SHA"),"at":NOW()})
def finalize():
 s=read()
 if not SRC.exists() or not CSRC.exists():raise RuntimeError("R2_EVIDENCE_NOT_GENERATED")
 d=json.loads(SRC.read_text(encoding="utf-8"))
 if not (d["input_county_candidates"]==2847 and d["R1_carry_forward"]==2847
  and d["R2_county_point_sun_rain_scanned"]==12
  and d["R2_humidity_model_sites"]>=10
  and d["R2_unscanned"]==2835
  and d["R2_verified_exclusions"]==0
  and d["R2_carry_forward"]==2847
  and d["formal_valid_county_screenings"]==0
  and d["formal_grade_changes"]==0 and len(d["point_records"])==12):
  raise RuntimeError("R2_SCOPE_OR_GRADING_GUARD_FAILURE")
 if d["CSV_sha256"]!=sha(CSRC.read_bytes()):raise RuntimeError("R2_CSV_HASH_FAIL")
 DEST.parent.mkdir(parents=True,exist_ok=True)
 DEST.write_bytes(SRC.read_bytes());CDEST.write_bytes(CSRC.read_bytes())
 result="RES-NATIONAL-R2-12-SUNRAIN-HUMIDITY-ERA5-"+RUN
 s["closed_result_refs"].append(result)
 s["last_completed_action_id"]=ACTION;s["consecutive_no_delta"]=0
 s["phase"]="NATIONAL_PARAMETER_CASCADE_R3_READY"
 s["active_action"]={"action_id":"RET-CASCADE-NATIONAL-R3-001",
   "question_id":"Q-NATIONAL_RESIDENTIAL_ALTITUDE",
   "decision":"由2847个R2保留单元进入R3，以现有12县36个DEM采样及局部地形例外证据做真实住宅海拔的探索性初筛，不按单个高点剔除整个县",
   "method":"实际从已保存DEM资料生成县域内高差、海拔偏好/例外清单；住宅位置不明标待核，其他未扫描县级单元继续流转",
   "expected_evidence":"2847个地区R2→R3队列对账，12县DEM多点证据、局部例外及0未经授权淘汰的审计",
   "pass_criteria":"R3使用真实DEM数据并保留住宅海拔未核边界；无已证实不可补偿重大风险不剔除",
   "fallback":"区域地形信息不可用标待核，继续推进R4",
   "status":"READY","timebox_end":"2026-11-08T15:26:00Z"}
 with CURRENT.open("a",encoding="utf-8") as f:
  f.write("\n- "+result+": R2已按用户漏斗要求实际衔接：全国2847个R1继续地区全部进入R2，重用12个已缓存1991—2020 ERA5逐日原始点位获得年日照、冬季日照、年降水和连续阴雨证据，其中"+str(d["R2_humidity_model_sites"])+"点位已有湿度/露点独立字段；R2真实点位12、R2尚未扫描2835、R2确证淘汰0、进入R3共2847，正式有效县级广筛0。R1未扫描与已有不足证据保留待核。证据："+str(DEST)+"，全国台账："+str(CDEST)+"。\n")
 s["current_state_ref"]["git_blob_sha"]=blob(CURRENT)
 s["state_revision"]+=1;s["updated_at"]=NOW()
 s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK","verified_commit":None}
 s["last_verified_run"]={"run_id":RUN,"action_id":ACTION,"result_id":result,
 "execution_status":"EXECUTED","engineering_status":"PASS",
 "research_delta_status":"DELTA_VERIFIED_12_REAL_R2_COUNTY_POINTS",
 "research_closure_status":"OPEN","evidence_path":str(DEST),"evidence_sha256":sha(DEST.read_bytes()),
 "csv_path":str(CDEST),"csv_sha256":sha(CDEST.read_bytes()),"status":"AWAITING_POSTCHECK"}
 s["national_parameter_rounds"]=s.get("national_parameter_rounds",{})
 s["national_parameter_rounds"]["R2"]={"input_counties":2847,"point_sun_rain_sites":12,
 "model_humidity_sites":d["R2_humidity_model_sites"],"R2_unscanned":2835,
 "confirmed_exits":0,"carry_forward":2847,"formal_valid_county_screenings":0}
 write(STATE,s)
 pre=json.loads((OUT/"national_r2_precheck.json").read_text(encoding="utf-8"))
 log({"kind":"S0-S5","run_id":RUN,"action_id":ACTION,"at":NOW(),
 "source_rev":pre["source_revision"],"source_commit":pre["source_commit"],
 "source_current_blob":pre["source_current_blob"],
 "command":"reuse archived 12 historic Open-Meteo daily files; python research_engine/retirement/national_r2_real_batch.py",
 "evidence_path":str(DEST),"evidence_sha256":sha(DEST.read_bytes()),
 "country_csv_path":str(CDEST),"country_csv_sha256":sha(CDEST.read_bytes()),
 "input":2847,"R2_real_point_count":12,"R2_unscanned":2835,"confirmed_exits":0,"carry_forward":2847,
 "formal_valid_county_screenings":0,"engineering_status":"PASS",
 "research_delta_status":"DELTA_VERIFIED_12_REAL_R2_COUNTY_POINTS",
 "research_closure_status":"OPEN","next_action_id":"RET-CASCADE-NATIONAL-R3-001",
 "result_id":result,"writeback":"PENDING_REMOTE_CHECK"})
 print(json.dumps({"R2_real_counties":12,"R2_unscanned":2835,"R3_carry_forward":2847},ensure_ascii=False))
def postcheck():
 s=read(post=True)
 state=json.loads(subprocess.check_output(["git","show","origin/main:"+str(STATE)],text=True))
 if state["state_revision"]!=s["state_revision"] or state["last_verified_run"]["run_id"]!=RUN:
  raise RuntimeError("REMOTE_STATE_MISMATCH")
 if state["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("REMOTE_CURRENT_DRIFT")
 for p,key in [(DEST,"evidence_sha256"),(CDEST,"csv_sha256")]:
  b=subprocess.check_output(["git","show","origin/main:"+str(p)])
  if sha(b)!=s["last_verified_run"][key]:raise RuntimeError("REMOTE_EVIDENCE_WRONG")
 lines=subprocess.check_output(["git","show","origin/main:"+str(LOG)],text=True).splitlines()
 if not any(json.loads(z).get("run_id")==RUN and json.loads(z).get("kind")=="S0-S5" for z in lines if z.strip()):
  raise RuntimeError("REMOTE_LOG_MISSING")
 s["writeback_verification"]={"status":"POSTCHECK_PASS",
  "verified_commit":subprocess.check_output(["git","rev-parse","origin/main"],text=True).strip(),"verified_at":NOW()}
 s["last_verified_run"]["status"]="POSTCHECK_PASS";s["state_revision"]+=1;s["updated_at"]=NOW()
 write(STATE,s)
 log({"kind":"S6_POSTCHECK","run_id":RUN,"action_id":ACTION,"postcheck":"PASS",
 "state_revision":s["state_revision"],"R2_real_counties":12,"R2_unscanned":2835,
 "R3_carry_forward":2847,"formal_valid_county_screenings":0,"at":NOW()})
if __name__=="__main__":
 try:{"precheck":precheck,"finalize":finalize,"postcheck":postcheck}[sys.argv[1]]()
 except Exception as exc:print("V1.6_R2_GATE_FAIL",repr(exc),file=sys.stderr);sys.exit(2)
