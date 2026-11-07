#!/usr/bin/env python3
"""V1.6 R3 national elevation / terrain three-point source checkpoint."""
import datetime,hashlib,json,os,pathlib,subprocess,sys
T="6aead9a989808191ad42f80fd4e32bf1";A="RET-CASCADE-NATIONAL-R3-001"
BASE=pathlib.Path("tasks")/T/"phase1"
S=BASE/"RUN_STATE.json";L=BASE/"RUN_LOG.jsonl"
C=pathlib.Path("research_assets/retirement/CURRENT_STATE.md")
ROOT=pathlib.Path("research_engine/retirement")
O=ROOT/"output"
P=O/"national_r3_first_real_batch_evidence.json"
Q=O/"national_r3_first_real_batch.csv"
DP=ROOT/"status/national_r3_first_real_batch_evidence.json"
DQ=ROOT/"status/national_r3_first_real_batch.csv"
RUN=os.getenv("GITHUB_RUN_ID","LOCAL")
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
sha=lambda b:hashlib.sha256(b).hexdigest()
def blob(p):return subprocess.check_output(["git","hash-object",str(p)],text=True).strip()
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def line(d):
 with L.open("a",encoding="utf-8") as f:f.write(json.dumps(d,ensure_ascii=False,sort_keys=True)+"\n")
def check(post=False):
 if not all(p.exists() for p in [S,L,C]):raise RuntimeError("V1.6_FILE_MISSING")
 s=json.loads(S.read_text(encoding="utf-8"))
 if s.get("schema_version")!="1.6" or s.get("task_id")!=T:raise RuntimeError("SCHEMA_MISMATCH")
 if s["current_state_ref"]["git_blob_sha"]!=blob(C):raise RuntimeError("CURRENT_BLOB_DRIFT")
 if not post:
  if s["active_action"]["action_id"]!=A:raise RuntimeError("UNIQUE_ACTION_MISMATCH")
  if s["last_completed_action_id"]!="RET-CASCADE-NATIONAL-R2-001":raise RuntimeError("R2_NOT_POSTCHECKED")
  if s["writeback_verification"]["status"]!="POSTCHECK_PASS":raise RuntimeError("PREVIOUS_S6_MISSING")
 else:
  if s["writeback_verification"]["status"]!="PENDING_REMOTE_CHECK" or s["last_verified_run"]["run_id"]!=RUN:
   raise RuntimeError("R3_POSTCHECK_BAD")
 return s
def precheck():
 s=check()
 for p in [P,Q]:
  if p.exists():p.unlink()
 dump(O/"national_r3_precheck.json",{"run_id":RUN,"source_rev":s["state_revision"],
 "source_current_blob":blob(C),"source_commit":os.getenv("GITHUB_SHA"),"at":NOW()})
def finalize():
 s=check()
 if not P.exists() or not Q.exists():raise RuntimeError("REAL_R3_DATA_NOT_GENERATED")
 d=json.loads(P.read_text(encoding="utf-8"))
 if not(d["input"]==2847 and d["R3_DEM_three_point_counties"]==12 and
 d["DEM_total_samples"]==36 and d["R3_unscanned"]==2835 and
 d["R3_confirmed_exclusions"]==0 and d["R3_carry_forward"]==2847 and
 d["formal_valid_county_screenings"]==0 and d["formal_grade_changes"]==0 and len(d["R3_records"])==12):
  raise RuntimeError("R3_EVIDENCE_AND_EXCLUSION_GUARD")
 if d["csv_sha256"]!=sha(Q.read_bytes()):raise RuntimeError("R3_CSV_SHA")
 DP.parent.mkdir(parents=True,exist_ok=True);DP.write_bytes(P.read_bytes());DQ.write_bytes(Q.read_bytes())
 res="RES-NATIONAL-R3-12COUNTY-36DEM-SAMPLES-"+RUN
 s["last_completed_action_id"]=A;s["closed_result_refs"].append(res);s["consecutive_no_delta"]=0
 s["phase"]="NATIONAL_PARAMETER_CASCADE_R4_READY"
 s["active_action"]={"action_id":"RET-CASCADE-NATIONAL-R4-001",
  "question_id":"Q_NATIONWIDE_AIR_INDUSTRIAL",
  "decision":"继续R4空气质量及工业历史污染，从2847个R3继续县区中优先复用已核实的蒙自、攀枝花市级环境资料，缺失视为待核；不能把城市级均值冒充住宅长期安全",
  "method":"将官方可溯源PM2.5/优良率、整改通报和具体住宅点位缺口映射到县级名录，独立标来源等级；只按确认的不可规避重大健康风险淘汰",
  "expected_evidence":"2847单元R3→R4台账、至少两县环境资料核查、缺口和初筛去留，退场须满足全部八项前置门禁",
  "pass_criteria":"实际空气/污染证据可复核，保留所有缺失区域继续R5；不改变正式等级",
  "fallback":"城市资料无法对应住宅则记CITY_CONTEXT_NOT_RESIDENTIAL，继续R5不暂停",
  "status":"READY","timebox_end":"2026-11-08T15:26:00Z"}
 with C.open("a",encoding="utf-8") as f:
  f.write("\n- "+res+": 按逐参数漏斗R3真实运行：全国2847个保留县级候选输入；12个历史编码县域关联36个Copernicus DEM GLO90真实采样点，记录原点/县内最低最高/跨度与低海拔潜在例外，2835个R3未扫描、确证淘汰0、继续2847。没有任何住宅精确定位和2026官方现行县界确认，因此正式有效县级广筛0。依据："+str(DP)+"；全量："+str(DQ)+"。\n")
 s["current_state_ref"]["git_blob_sha"]=blob(C);s["state_revision"]+=1;s["updated_at"]=NOW()
 s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK","verified_commit":None}
 s["last_verified_run"]={"run_id":RUN,"action_id":A,"result_id":res,"execution_status":"EXECUTED",
 "engineering_status":"PASS","research_delta_status":"DELTA_VERIFIED_12_COUNTY_36_DEM_SAMPLES",
 "research_closure_status":"OPEN","evidence_path":str(DP),"evidence_sha256":sha(DP.read_bytes()),
 "csv_path":str(DQ),"csv_sha256":sha(DQ.read_bytes()),"status":"AWAITING_POSTCHECK"}
 s["national_parameter_rounds"]=s.get("national_parameter_rounds",{})
 s["national_parameter_rounds"]["R3"]={"input_counties":2847,"DEM_3_point_counties":12,
 "DEM_total_samples":36,"R3_unscanned":2835,"confirmed_exits":0,"carry_forward":2847,
 "formal_valid_county_screenings":0}
 dump(S,s)
 pre=json.loads((O/"national_r3_precheck.json").read_text(encoding="utf-8"))
 line({"kind":"S0-S5","run_id":RUN,"action_id":A,"source_revision":pre["source_rev"],
 "source_commit":pre["source_commit"],"source_current_blob":pre["source_current_blob"],
 "command":"python research_engine/retirement/national_r3_dem_batch.py",
 "evidence_path":str(DP),"evidence_sha256":sha(DP.read_bytes()),
 "csv_path":str(DQ),"csv_sha256":sha(DQ.read_bytes()),"at":NOW(),
 "R3_actual_counties":12,"R3_DEM_samples":36,"R3_unscanned":2835,
 "confirmed_exits":0,"carry_forward":2847,"formal_valid_county_screenings":0,
 "engineering_status":"PASS","research_delta_status":"DELTA_VERIFIED","research_closure_status":"OPEN",
 "result_id":res,"next_action_id":"RET-CASCADE-NATIONAL-R4-001","writeback":"PENDING_REMOTE_CHECK"})
 print(json.dumps({"R3_real_counties":12,"DEM_samples":36,"R3_not_scanned":2835,"next":"R4"},ensure_ascii=False))
def postcheck():
 s=check(post=True)
 remote=json.loads(subprocess.check_output(["git","show","origin/main:"+str(S)],text=True))
 if remote["state_revision"]!=s["state_revision"] or remote["last_verified_run"]["run_id"]!=RUN:
  raise RuntimeError("REMOTE_STATE_CONFLICT")
 if remote["current_state_ref"]["git_blob_sha"]!=blob(C):raise RuntimeError("REMOTE_CURRENT_BLOB_CONFLICT")
 for path,key in [(DP,"evidence_sha256"),(DQ,"csv_sha256")]:
  if sha(subprocess.check_output(["git","show","origin/main:"+str(path)]))!=s["last_verified_run"][key]:
   raise RuntimeError("REMOTE_EVIDENCE_SHA")
 entries=subprocess.check_output(["git","show","origin/main:"+str(L)],text=True).splitlines()
 if not any(json.loads(z).get("run_id")==RUN and json.loads(z).get("kind")=="S0-S5" for z in entries if z.strip()):
  raise RuntimeError("REMOTE_LOG_MISSING")
 s["writeback_verification"]={"status":"POSTCHECK_PASS",
  "verified_commit":subprocess.check_output(["git","rev-parse","origin/main"],text=True).strip(),
  "verified_at":NOW()}
 s["last_verified_run"]["status"]="POSTCHECK_PASS";s["state_revision"]+=1;s["updated_at"]=NOW()
 dump(S,s)
 line({"kind":"S6_POSTCHECK","run_id":RUN,"action_id":A,"postcheck":"PASS",
 "state_revision":s["state_revision"],"R3_DEM_sites":12,"carry_forward":2847,"formal_county":0,"at":NOW()})
if __name__=="__main__":
 try:{"precheck":precheck,"finalize":finalize,"postcheck":postcheck}[sys.argv[1]]()
 except Exception as e:print("V16_R3_FAIL",repr(e),file=sys.stderr);sys.exit(2)
