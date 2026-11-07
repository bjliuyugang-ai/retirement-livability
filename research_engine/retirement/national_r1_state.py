#!/usr/bin/env python3
"""V1.6 S0-S6 checkpoint for first real (12) historical county R1 point-data batch."""
import datetime,hashlib,json,os,pathlib,subprocess,sys
TASK="6aead9a989808191ad42f80fd4e32bf1"
BASE=pathlib.Path("tasks")/TASK/"phase1"
STATE=BASE/"RUN_STATE.json";LOG=BASE/"RUN_LOG.jsonl"
CURRENT=pathlib.Path("research_assets/retirement/CURRENT_STATE.md")
ROOT=pathlib.Path("research_engine/retirement")
OUTPUT=ROOT/"output"
SOURCE_JSON=OUTPUT/"national_r1_first_real_batch_evidence.json"
SOURCE_CSV=OUTPUT/"national_r1_first_real_batch.csv"
DEST_JSON=ROOT/"status/national_r1_first_real_batch_evidence.json"
DEST_CSV=ROOT/"status/national_r1_first_real_batch.csv"
ACTION="RET-CASCADE-NATIONAL-R1-001"
RUN=os.getenv("GITHUB_RUN_ID","LOCAL")
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(path):return subprocess.check_output(["git","hash-object",str(path)],text=True).strip()
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def log(x):
 with LOG.open("a",encoding="utf-8") as f:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n")
def statecheck(post=False):
 if not STATE.exists() or not LOG.exists() or not CURRENT.exists():raise RuntimeError("V16_INPUT_MISSING")
 s=json.loads(STATE.read_text(encoding="utf-8"))
 if s.get("schema_version")!="1.6" or s.get("task_id")!=TASK:raise RuntimeError("V16_SCHEMA_MISMATCH")
 if s["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("V16_CURRENT_SHA_DRIFT")
 if not post:
  if s["active_action"]["action_id"]!=ACTION:raise RuntimeError("V16_UNIQUE_ACTION_MISMATCH")
  if s["writeback_verification"]["status"]!="POSTCHECK_PASS":raise RuntimeError("V16_PRIOR_POSTCHECK_MISSING")
 else:
  if s["writeback_verification"]["status"]!="PENDING_REMOTE_CHECK":raise RuntimeError("V16_POSTCHECK_NOT_PENDING")
  if s["last_verified_run"]["run_id"]!=RUN:raise RuntimeError("V16_POSTCHECK_RUN_ID_MISMATCH")
 return s
def precheck():
 s=statecheck()
 for path in [SOURCE_JSON,SOURCE_CSV]:
  if path.exists():path.unlink()
 write(OUTPUT/"national_r1_precheck.json",{
 "run_id":RUN,"action_id":ACTION,"start_at":NOW(),
 "source_revision":s["state_revision"],"source_current_blob":blob(CURRENT),
 "source_state_sha":sha(STATE.read_bytes()),"source_commit":os.environ.get("GITHUB_SHA"),
 "previous_run_id":s["last_verified_run"]["run_id"]})
def finalize():
 s=statecheck()
 if not SOURCE_JSON.exists() or not SOURCE_CSV.exists():raise RuntimeError("R1_REAL_DATA_NOT_GENERATED")
 d=json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
 if not (d["input_counties"]==2847 and d["R1_real_point_evidence_counties"]==12
   and d["R1_not_scanned_counties"]==2835 and d["R1_carry_forward_count"]==2847
   and d["R1_county_wide_validated"]==0 and d["R1_verified_fatal_exclusions"]==0
   and d["formal_valid_county_screenings"]==0 and d["formal_grades_changed"]==0
   and len(d["county_era5_climate_records"])==12):
  raise RuntimeError("R1_DATA_OR_FORMAL_GRADE_INVARIANT_FAILED")
 if sha(SOURCE_CSV.read_bytes())!=d["CSV_sha256"]:raise RuntimeError("R1_CSV_HASH_INVALID")
 DEST_JSON.parent.mkdir(parents=True,exist_ok=True)
 DEST_JSON.write_bytes(SOURCE_JSON.read_bytes());DEST_CSV.write_bytes(SOURCE_CSV.read_bytes())
 result="RES-NATIONAL-R1-12-REAL-ERA5-COUNTY-POINTS-"+RUN
 s["last_completed_action_id"]=ACTION
 s["closed_result_refs"].append(result)
 s["consecutive_no_delta"]=0
 s["phase"]="NATIONAL_R1_TEMPERATURE_EVIDENCE_EXPANSION"
 s["active_action"]={"action_id":"RET-CASCADE-NATIONAL-R1-EXPAND-002",
  "question_id":"Q-NATIONAL_FIRST_PARAMETER_FILTER",
  "decision":"把真实R1温度取证从12个历史编码县域向更多省份和县级居住片区扩展；已有证据缓存复用、无数据保持未扫描，达到可量化覆盖再继续其他参数",
  "method":"基于可核查真实坐标与县级历史边界/临时代码映射分批下载1991-2020 ERA5温度，并在每批里区分格点已测、县域代表性未核、未扫描和正式广筛",
  "expected_evidence":"每批新增县级R1实际温度证据、输入/继续/退出审计、失败和未扫描原因以及历史地貌例外",
  "pass_criteria":"新增R1真实样本且增量可复现；不因缺失数据卡住全国后续轮次、不提前宣布正式县域筛选",
  "fallback":"历史县界/站点接口失败则优先读取已有经溯源城市气候事实，依旧将未取到的数据留在R1_NOT_SCREENED",
  "status":"READY","timebox_end":"2026-11-08T15:26:00Z"}
 with CURRENT.open("a",encoding="utf-8") as f:
  f.write("\n- "+result+": 全国R1首次真实数据批处理通过：沿用GitHub Actions历史归档12点1991—2020 ERA5逐日气温记录，匹配12个独立历史县级候选编码（仅单点、非住宅），形成冬季、6—9月夏季和≥35℃热天证据；总2847临时县级，12个R1有探索性点证据、2835个R1未扫描、确证退出0、继续2847、正式有效县级广筛0。首批R2交接输入可继续但R1未扫描必须保留未知，不冒充R1完成。证据："+str(DEST_JSON)+"，县级全量增量台账："+str(DEST_CSV)+"。\n")
 s["current_state_ref"]["git_blob_sha"]=blob(CURRENT)
 s["state_revision"]+=1;s["updated_at"]=NOW()
 s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK","verified_commit":None}
 s["last_verified_run"]={"run_id":RUN,"action_id":ACTION,"result_id":result,
  "execution_status":"EXECUTED","engineering_status":"PASS",
  "research_delta_status":"DELTA_VERIFIED_12_REAL_COUNTY_POINT_DATA",
  "research_closure_status":"OPEN",
  "evidence_path":str(DEST_JSON),"evidence_sha256":sha(DEST_JSON.read_bytes()),
  "csv_path":str(DEST_CSV),"csv_sha256":sha(DEST_CSV.read_bytes()),"status":"AWAITING_POSTCHECK"}
 s["r1_nationwide_progress"]={"provisional_roster":2847,"R1_point_data_counties":12,
  "R1_unscanned_counties":2835,"R1_confirmed_exits":0,"R1_carry_forward":2847,
  "formal_valid_county_screenings":0,"source_artifact_run":"42245826626","source_artifact_id":"13518156891",
  "output":str(DEST_JSON),"county_register":str(DEST_CSV)}
 write(STATE,s)
 pre=json.loads((OUTPUT/"national_r1_precheck.json").read_text(encoding="utf-8"))
 log({"kind":"S0-S5","run_id":RUN,"action_id":ACTION,"source_revision":pre["source_revision"],
  "source_commit":pre["source_commit"],"source_current_blob":pre["source_current_blob"],
  "command":"gh run download 42245826626 -n retirement-climate-pilot-output; python research_engine/retirement/national_r1_real_batch.py",
  "evidence_path":str(DEST_JSON),"evidence_sha256":sha(DEST_JSON.read_bytes()),
  "csv_path":str(DEST_CSV),"csv_sha256":sha(DEST_CSV.read_bytes()),
  "input_provisional_units":2847,"real_R1_point_data_counties":12,"R1_not_scanned":2835,
  "verified_exits":0,"carry_forward_count":2847,"valid_county_screenings":0,
  "engineering_status":"PASS","research_delta_status":"DELTA_VERIFIED_12_REAL_COUNTY_POINT_DATA",
  "research_closure_status":"OPEN","next_action_id":"RET-CASCADE-NATIONAL-R1-EXPAND-002",
  "result_id":result,"writeback":"PENDING_REMOTE_CHECK","at":NOW()})
 print(json.dumps({"R1_real_point_counties":12,"R1_unscanned":2835,"next_action":s["active_action"]["action_id"]},ensure_ascii=False))
def postcheck():
 s=statecheck(post=True)
 r=json.loads(subprocess.check_output(["git","show","origin/main:"+str(STATE)],text=True))
 if r["state_revision"]!=s["state_revision"] or r["last_verified_run"]["run_id"]!=RUN:raise RuntimeError("REMOTE_STATE_CONFLICT")
 if r["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("REMOTE_CURRENT_BLOB_CONFLICT")
 for p,key in [(DEST_JSON,"evidence_sha256"),(DEST_CSV,"csv_sha256")]:
  data=subprocess.check_output(["git","show","origin/main:"+str(p)])
  if sha(data)!=s["last_verified_run"][key]:raise RuntimeError("REMOTE_EVIDENCE_SHA_CONFLICT "+str(p))
 lines=subprocess.check_output(["git","show","origin/main:"+str(LOG)],text=True).splitlines()
 if not any(json.loads(line).get("run_id")==RUN and json.loads(line).get("kind")=="S0-S5" for line in lines if line.strip()):
  raise RuntimeError("REMOTE_EXECUTION_LOG_MISSING")
 s["writeback_verification"]={"status":"POSTCHECK_PASS","verified_commit":subprocess.check_output(["git","rev-parse","origin/main"],text=True).strip(),"verified_at":NOW()}
 s["last_verified_run"]["status"]="POSTCHECK_PASS";s["state_revision"]+=1;s["updated_at"]=NOW()
 write(STATE,s)
 log({"kind":"S6_POSTCHECK","run_id":RUN,"action_id":ACTION,"postcheck":"PASS",
  "state_revision":s["state_revision"],"R1_point_data_counties":12,
  "R1_unscanned_counties":2835,"formal_county_screenings":0,"at":NOW()})
if __name__=="__main__":
 try:{"precheck":precheck,"finalize":finalize,"postcheck":postcheck}[sys.argv[1]]()
 except Exception as e:print("R1_V16_GATE_FAIL",repr(e),file=sys.stderr);sys.exit(2)
