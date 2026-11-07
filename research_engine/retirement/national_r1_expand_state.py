#!/usr/bin/env python3
"""Unique V1.6 action checkpoint for distributed national R1 real climate expansion."""
import datetime,hashlib,json,os,pathlib,subprocess,sys
TASK="6aead9a989808191ad42f80fd4e32bf1";ACTION="RET-CASCADE-NATIONAL-R1-EXPAND-002"
ROOT=pathlib.Path("research_engine/retirement");OUTPUT=ROOT/"output"
BASE=pathlib.Path("tasks")/TASK/"phase1"
STATE=BASE/"RUN_STATE.json";LOG=BASE/"RUN_LOG.jsonl"
CURRENT=pathlib.Path("research_assets/retirement/CURRENT_STATE.md")
SRC=OUTPUT/"national_r1_expanded_summary.json";CSV=OUTPUT/"national_r1_expanded.csv"
DEST=ROOT/"status/national_r1_expanded_summary.json"
DESTCSV=ROOT/"status/national_r1_expanded.csv"
RUN=os.getenv("R1_RECOVERY_ORIGINAL_RUN_ID",os.getenv("GITHUB_RUN_ID","LOCAL"))
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(p):return subprocess.check_output(["git","hash-object",str(p)],text=True).strip()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def log(d):
 with LOG.open("a",encoding="utf-8") as f:f.write(json.dumps(d,ensure_ascii=False,sort_keys=True)+"\n")
def read(post=False):
 if not all(x.exists() for x in [STATE,LOG,CURRENT]):raise RuntimeError("V1.6_STATE_MISSING")
 s=json.loads(STATE.read_text(encoding="utf-8"))
 if s.get("task_id")!=TASK or s.get("schema_version")!="1.6":raise RuntimeError("V16_SCHEMA_MISMATCH")
 if s["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("V16_STATE_DRIFT")
 if not post:
  if s["active_action"]["action_id"]!=ACTION:raise RuntimeError("UNIQUE_ACTION_MISMATCH")
  if s["writeback_verification"]["status"]!="POSTCHECK_PASS":raise RuntimeError("UNVERIFIED_PRIOR_ACTION")
  if s["last_completed_action_id"]!="RET-CASCADE-NATIONAL-R1-001":raise RuntimeError("NO_REAL_R1_PREREQUISITE")
 else:
  if s["writeback_verification"]["status"]!="PENDING_REMOTE_CHECK":raise RuntimeError("NO_PENDING_POSTCHECK")
  if s["last_verified_run"]["run_id"]!=RUN:raise RuntimeError("RUN_MISMATCH")
 return s
def precheck():
 s=read()
 for p in [SRC,CSV]:
  if p.exists():p.unlink()
 write(OUTPUT/"r1_expand_precheck.json",{"run_id":RUN,"action_id":ACTION,"source_rev":s["state_revision"],
  "source_state_sha":sha(STATE.read_bytes()),"current_blob":blob(CURRENT),
  "source_commit":os.getenv("GITHUB_SHA"),"at":NOW()})
def finalize():
 s=read()
 if not SRC.exists() or not CSV.exists():raise RuntimeError("R1_EXPANDED_SOURCE_NOT_WRITTEN")
 d=json.loads(SRC.read_text(encoding="utf-8"));new=d["new_point_evidence_counties"]
 if not (d["requested_new_county_candidates"]==30 and new>0
  and d["cumulative_R1_point_data_counties"]==12+new
  and d["R1_not_scanned"]==2835-new
  and d["R1_carry_forward_to_R2"]==2847
  and d["cumulative_R1_verified_fatal_exclusions"]==0
  and d["formal_valid_county_screenings"]==0
  and d["formal_grades_changed"]==0
  and len(d["new_point_records"])==new
  and len(d["failure_details"])+new==30):
  raise RuntimeError("R1_EXPANSION_FROZEN_GUARD_FAILED")
 if d["output_csv_sha256"]!=sha(CSV.read_bytes()):raise RuntimeError("R1_CSV_DIGEST_MISMATCH")
 DEST.parent.mkdir(parents=True,exist_ok=True);DEST.write_bytes(SRC.read_bytes());DESTCSV.write_bytes(CSV.read_bytes())
 result="RES-NATIONAL-R1-DISTRIBUTED-EXPAND-"+RUN
 s["closed_result_refs"].append(result)
 s["last_completed_action_id"]=ACTION;s["consecutive_no_delta"]=0
 s["phase"]="NATIONAL_PARAMETER_CASCADE_R2_READY"
 s["active_action"]={"action_id":"RET-CASCADE-NATIONAL-R2-001",
  "question_id":"Q-NATIONAL_SECOND_PARAMETER_FILTER",
  "decision":"直接由全国2847个R1继续队列进入R2，使用已有1991—2020气候数据计算日照/降雨/湿度初筛；R1未扫描保留为未知，不因数据缺口停滞",
  "method":"读取全国R1新增全量台账；从12点历史原始ERA5提取真实降雨和日照，4县已存湿度数据做局部探索，其他地区继续待核；对已确定不可接受且空间例外核实者才有权提前淘汰",
  "expected_evidence":"R1→R2全量输入输出数量一致；至少12个历史气候点得到真实日照与降雨多年证据；R1未知状态保持不变；退出与缺失分别入库",
  "pass_criteria":"真实R2参数级证据可复算、输入=上一轮R1继续2847，状态及证据完整S0—S6",
  "fallback":"不重复获取Open-Meteo数据；优先复用历史归档；缺值待核、继续下一轮",
  "status":"READY","timebox_end":"2026-11-08T15:26:00Z"}
 with CURRENT.open("a",encoding="utf-8") as f:
  f.write("\n- "+result+": 本轮全国R1从12个已取数历史县级点位扩展到"+str(12+new)+"，新增"+str(new)+"个真实1991—2020 ERA5温度取数点，历史县界/2025临时代码精确拼音关联、跨"+str(d["new_points_with_provinces"])+"省级代码前缀。另"+str(d["R1_not_scanned"])+"个县级R1未扫描（含"+str(d["failed_or_missing_new_targets"])+"个接口失败/验证失败），确证淘汰0、下轮继续2847、正式有效县级广筛0。各结果严格记为点位/2017历史县界探索性，不作2026官方或居住片区证实。已批准递进法，唯一下一动作转R2，不阻塞于R1缺失。证据："+str(DEST)+"，全量CSV："+str(DESTCSV)+"。\n")
 s["current_state_ref"]["git_blob_sha"]=blob(CURRENT)
 s["state_revision"]+=1;s["updated_at"]=NOW()
 s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK","verified_commit":None}
 s["last_verified_run"]={"run_id":RUN,"action_id":ACTION,"result_id":result,
 "execution_status":"EXECUTED","engineering_status":"PASS",
 "research_delta_status":"DELTA_VERIFIED_"+str(new)+"_REAL_R1_COUNTY_POINTS",
 "research_closure_status":"OPEN","evidence_path":str(DEST),"evidence_sha256":sha(DEST.read_bytes()),
 "csv_path":str(DESTCSV),"csv_sha256":sha(DESTCSV.read_bytes()),"status":"AWAITING_POSTCHECK"}
 s["r1_nationwide_progress"]={"provisional_roster":2847,
 "R1_point_data_counties":12+new,"R1_unscanned_counties":2835-new,"R1_confirmed_exits":0,
 "R1_carry_forward":2847,"R1_new_expanded_point_data":new,
 "R1_new_failed_or_unscanned_targets":d["failed_or_missing_new_targets"],
 "R1_new_province_prefixes":d["new_points_with_provinces"],
 "formal_valid_county_screenings":0,"output":str(DEST),"county_register":str(DESTCSV)}
 write(STATE,s)
 pre=json.loads((OUTPUT/"r1_expand_precheck.json").read_text(encoding="utf-8"))
 log({"kind":"S0-S5","run_id":RUN,"action_id":ACTION,"at":NOW(),
 "source_revision":pre["source_rev"],"source_current_blob":pre["current_blob"],"source_commit":pre["source_commit"],
 "command":"python research_engine/retirement/national_r1_expand_weather.py",
 "evidence_path":str(DEST),"evidence_sha256":sha(DEST.read_bytes()),
 "county_register":str(DESTCSV),"county_register_sha256":sha(DESTCSV.read_bytes()),
 "total":2847,"real_R1_point_count":12+new,"increment":new,"unscanned":2835-new,
 "confirmed_exits":0,"carry_forward":2847,"valid_county_screenings":0,
 "research_delta_status":"DELTA_VERIFIED","engineering_status":"PASS","research_closure_status":"OPEN",
 "result_id":result,"next_action_id":"RET-CASCADE-NATIONAL-R2-001","writeback":"PENDING_REMOTE_CHECK"})
 print(json.dumps({"new_measured":new,"total_R1_point_data":12+new,"unscanned":2835-new,
 "R2_carry_forward":2847,"next_action":"RET-CASCADE-NATIONAL-R2-001"},ensure_ascii=False))
def postcheck():
 s=read(post=True)
 remote=json.loads(subprocess.check_output(["git","show","origin/main:"+str(STATE)],text=True))
 if remote["state_revision"]!=s["state_revision"] or remote["last_verified_run"]["run_id"]!=RUN:
  raise RuntimeError("POSTCHECK_REMOTE_STATE_MISMATCH")
 if remote["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("REMOTE_CURRENT_DRIFT")
 for path,key in [(DEST,"evidence_sha256"),(DESTCSV,"csv_sha256")]:
  raw=subprocess.check_output(["git","show","origin/main:"+str(path)])
  if sha(raw)!=s["last_verified_run"][key]:raise RuntimeError("REMOTE_EVIDENCE_SHA_WRONG")
 entries=subprocess.check_output(["git","show","origin/main:"+str(LOG)],text=True).splitlines()
 if not any(json.loads(z).get("run_id")==RUN and json.loads(z).get("kind")=="S0-S5" for z in entries if z.strip()):
  raise RuntimeError("S0-S5_LOG_NOT_PERSISTED")
 s["writeback_verification"]={"status":"POSTCHECK_PASS",
 "verified_commit":subprocess.check_output(["git","rev-parse","origin/main"],text=True).strip(),
 "verified_at":NOW()}
 s["last_verified_run"]["status"]="POSTCHECK_PASS";s["state_revision"]+=1;s["updated_at"]=NOW()
 write(STATE,s)
 log({"kind":"S6_POSTCHECK","run_id":RUN,"action_id":ACTION,"postcheck":"PASS",
 "state_revision":s["state_revision"],"R1_point_data_counties":s["r1_nationwide_progress"]["R1_point_data_counties"],
 "R1_unscanned_counties":s["r1_nationwide_progress"]["R1_unscanned_counties"],
 "R2_carry_forward":2847,"formal_county_screenings":0,"at":NOW()})
if __name__=="__main__":
 try:{"precheck":precheck,"finalize":finalize,"postcheck":postcheck}[sys.argv[1]]()
 except Exception as e:print("R1_EXPAND_GATE_FAIL",repr(e),file=sys.stderr);sys.exit(2)
