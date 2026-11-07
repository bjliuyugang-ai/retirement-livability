#!/usr/bin/env python3
"""V1.6 state machine, one unique action per late nationwide cascade R4 or R5."""
import datetime,hashlib,json,os,pathlib,subprocess,sys
if len(sys.argv)!=3 or sys.argv[1] not in ("R4","R5") or sys.argv[2] not in ("precheck","finalize","postcheck"):
 raise SystemExit("usage: national_r45_state.py R4|R5 precheck|finalize|postcheck")
R=sys.argv[1];STAGE=sys.argv[2]
T="6aead9a989808191ad42f80fd4e32bf1"
A="RET-CASCADE-NATIONAL-"+R+"-001"
B=pathlib.Path("tasks")/T/"phase1"
STATE=B/"RUN_STATE.json";LOG=B/"RUN_LOG.jsonl"
CUR=pathlib.Path("research_assets/retirement/CURRENT_STATE.md")
ROOT=pathlib.Path("research_engine/retirement");O=ROOT/"output"
N="national_r4_city_context" if R=="R4" else "national_r5_tap_water"
SRC=O/(N+"_evidence.json");CSRC=O/(N+"_batch.csv")
DEST=ROOT/"status"/(N+"_evidence.json");CDEST=ROOT/"status"/(N+"_batch.csv")
PRIOR="RET-CASCADE-NATIONAL-R3-001" if R=="R4" else "RET-CASCADE-NATIONAL-R4-001"
COUNT=2 if R=="R4" else 1
RUN=os.getenv("GITHUB_RUN_ID","LOCAL")
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(p):return subprocess.check_output(["git","hash-object",str(p)],text=True).strip()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def log(d):
 with LOG.open("a",encoding="utf-8") as f:f.write(json.dumps(d,ensure_ascii=False,sort_keys=True)+"\n")
def read(post=False):
 if not all(x.exists() for x in [STATE,LOG,CUR]):raise RuntimeError("STATE_INPUT_MISSING")
 s=json.loads(STATE.read_text(encoding="utf-8"))
 if s.get("schema_version")!="1.6" or s.get("task_id")!=T:raise RuntimeError("SCHEMA_INVALID")
 if s["current_state_ref"]["git_blob_sha"]!=blob(CUR):raise RuntimeError("CURRENT_BLOB_DRIFT")
 if not post:
  if s["active_action"]["action_id"]!=A:raise RuntimeError("ACTIVE_ACTION_WRONG")
  if s["last_completed_action_id"]!=PRIOR:raise RuntimeError("PREVIOUS_ROUND_MISSING")
  if s["writeback_verification"]["status"]!="POSTCHECK_PASS":raise RuntimeError("PREVIOUS_S6_PENDING")
 else:
  if s["writeback_verification"]["status"]!="PENDING_REMOTE_CHECK" or s["last_verified_run"]["run_id"]!=RUN:
   raise RuntimeError("POSTCHECK_MISMATCH")
 return s
def precheck():
 s=read()
 for p in (SRC,CSRC):
  if p.exists():p.unlink()
 save(O/(N+"_precheck.json"),{"run_id":RUN,"source_rev":s["state_revision"],
  "current_blob":blob(CUR),"source_commit":os.getenv("GITHUB_SHA"),"at":NOW()})
def finalize():
 s=read()
 if not SRC.exists() or not CSRC.exists():raise RuntimeError("MISSING_SOURCE_COMPUTATION")
 d=json.loads(SRC.read_text(encoding="utf-8"))
 if not(d["input"]==2847 and d[R+"_carry_forward"]==2847
   and d[R+"_confirmed_exclusions"]==0 and d[R+"_unscanned"]==2847-COUNT
   and d[R+"_direct_evidence_counties"]==COUNT
   and d["formal_valid_county_screenings"]==0 and d["formal_grade_changes"]==0
   and len(d["records"])==COUNT and sha(CSRC.read_bytes())==d["CSV_sha256"]):
    raise RuntimeError("FROZEN_R45_COUNTS_AND_SOURCE_INVARIANT_FAILED")
 DEST.parent.mkdir(parents=True,exist_ok=True)
 DEST.write_bytes(SRC.read_bytes());CDEST.write_bytes(CSRC.read_bytes())
 result="RES-NATIONAL-"+R+"-PARTIAL-SOURCE-ANCHORED-"+RUN
 s["last_completed_action_id"]=A;s["closed_result_refs"].append(result);s["consecutive_no_delta"]=0
 s["phase"]="NATIONAL_PARAMETER_CASCADE_"+("R5_READY" if R=="R4" else "FINAL_MISSING_AUDIT_READY")
 if R=="R4":
  next_action={"action_id":"RET-CASCADE-NATIONAL-R5-001",
   "question_id":"Q_NATIONAL_WATER_DISASTERS",
   "decision":"从2847个R4继续县区进行R5饮用水与地灾底线初筛，利用蒙自2026年官方16条已归档末梢水记录作为可追溯来源，其他地区资料缺失继续保留",
   "method":"用官方末梢水监测点实际来源建立区域级有限证据，不凭水源地达标证明住宅水质，不凭地灾清单没有坐标宣称安全",
   "expected_evidence":"至少1县16条逐点末梢水观测的有限归属、R5缺失单元、全量2847传递对账",
   "pass_criteria":"真实数据可溯源，R5通过或缺失不改变正式等级",
   "fallback":"饮用水/地灾缺失全部留待最终缺口表而不阻塞",
   "status":"READY","timebox_end":"2026-11-08T15:26:00Z"}
 else:
  next_action={"action_id":"RET-CASCADE-NATIONAL-GAP-AUDIT-001",
   "question_id":"Q_NATIONAL_MISSING_PARAMETER_PRIORITIES",
   "decision":"正式整理全国2847县级候选的R1—R5逐参数证据覆盖、未扫描与待核清单、退出历史和需要重点补的缺口，不宣称全国筛选已经完成",
   "method":"R5全国台账逐行对账，按R1真实取数、R2-R5不同空间证据及实际候选住宅定位排序，输出全国完整审计表、可复用证据与技术取数瓶颈",
   "expected_evidence":"R1-R5各轮输入/证据数量、待补缺口总表、已确认退出记录和最终优先级清单，区分正式有效覆盖与探索性覆盖",
   "pass_criteria":"所有2847地区去重并可追溯，未知不等于淘汰、单点不等于县域；用户可审查难取数据与真实覆盖率",
   "fallback":"如资料仍不足，仍输出全量缺口与获取失败清单，诚实报告不可判定",
   "status":"READY","timebox_end":"2026-11-08T15:26:00Z"}
 s["active_action"]=next_action
 with CUR.open("a",encoding="utf-8") as f:
  f.write("\n- "+result+": 全国逐参数漏斗"+R+"已执行：2847候选继续，真实有据的区域/命名监测点县区"+str(COUNT)+"个，"+str(2847-COUNT)+"个此参数未扫描，确证淘汰0、进入下一轮2847、正式有效县级广筛0。"+("R4依据2025年蒙自PM2.5、攀枝花城市空气和工业整改等公开来源，但均不是住宅暴露。R5依据2026年蒙自16条官方末梢水公开采样，不能代表具体楼栋水质及地灾安全。" if R=="R4" else "R5依据2026年蒙自16条官方末梢水公开采样，不能代表具体楼栋完整水质标准、地灾/洪涝未核。")+" 证据："+str(DEST)+"；全量县级台账："+str(CDEST)+"。\n")
 s["current_state_ref"]["git_blob_sha"]=blob(CUR);s["state_revision"]+=1;s["updated_at"]=NOW()
 s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK","verified_commit":None}
 s["last_verified_run"]={"run_id":RUN,"action_id":A,"result_id":result,
 "execution_status":"EXECUTED","engineering_status":"PASS",
 "research_delta_status":"PARTIAL_DELTA_VERIFIED_"+str(COUNT)+"_R"+R[-1]+"_COUNTIES",
 "research_closure_status":"OPEN","evidence_path":str(DEST),"evidence_sha256":sha(DEST.read_bytes()),
 "csv_path":str(CDEST),"csv_sha256":sha(CDEST.read_bytes()),"status":"AWAITING_POSTCHECK"}
 s["national_parameter_rounds"]=s.get("national_parameter_rounds",{})
 s["national_parameter_rounds"][R]={"input_counties":2847,"real_source_counties":COUNT,
  "unscanned":2847-COUNT,"confirmed_exits":0,"carry_forward":2847,
  "formal_valid_county_screenings":0}
 save(STATE,s)
 pre=json.loads((O/(N+"_precheck.json")).read_text(encoding="utf-8"))
 log({"kind":"S0-S5","run_id":RUN,"action_id":A,"source_rev":pre["source_rev"],
 "source_commit":pre["source_commit"],"source_current_blob":pre["current_blob"],
 "command":"python research_engine/retirement/national_r4_r5_source_steps.py "+R,
 "evidence_path":str(DEST),"evidence_sha256":sha(DEST.read_bytes()),
 "csv_path":str(CDEST),"csv_sha256":sha(CDEST.read_bytes()),"at":NOW(),
 "real_evidence_counties":COUNT,"unscanned":2847-COUNT,
 "carry_forward":2847,"confirmed_exits":0,"formal_valid_county_screenings":0,
 "engineering_status":"PASS","research_delta_status":"PARTIAL_DELTA_VERIFIED",
 "research_closure_status":"OPEN","next_action_id":s["active_action"]["action_id"],
 "result_id":result,"writeback":"PENDING_REMOTE_CHECK"})
 print(json.dumps({"round":R,"actual_counties":COUNT,"not_scanned":2847-COUNT,
 "next_action":next_action["action_id"]},ensure_ascii=False))
def postcheck():
 s=read(post=True)
 remote=json.loads(subprocess.check_output(["git","show","origin/main:"+str(STATE)],text=True))
 if remote["state_revision"]!=s["state_revision"] or remote["last_verified_run"]["run_id"]!=RUN:
  raise RuntimeError("REMOTE_STATE_REV_WRONG")
 if remote["current_state_ref"]["git_blob_sha"]!=blob(CUR):raise RuntimeError("REMOTE_CURRENT_MISMATCH")
 for p,key in [(DEST,"evidence_sha256"),(CDEST,"csv_sha256")]:
  if sha(subprocess.check_output(["git","show","origin/main:"+str(p)]))!=s["last_verified_run"][key]:
   raise RuntimeError("REMOTE_SOURCE_DIGEST_WRONG")
 lines=subprocess.check_output(["git","show","origin/main:"+str(LOG)],text=True).splitlines()
 if not any(json.loads(line).get("run_id")==RUN and json.loads(line).get("kind")=="S0-S5" for line in lines if line.strip()):
  raise RuntimeError("REMOTE_RUN_LOG_MISSING")
 s["writeback_verification"]={"status":"POSTCHECK_PASS",
  "verified_commit":subprocess.check_output(["git","rev-parse","origin/main"],text=True).strip(),
  "verified_at":NOW()}
 s["last_verified_run"]["status"]="POSTCHECK_PASS";s["state_revision"]+=1;s["updated_at"]=NOW()
 save(STATE,s)
 log({"kind":"S6_POSTCHECK","run_id":RUN,"action_id":A,"postcheck":"PASS",
  "state_revision":s["state_revision"],"real_source_counties":COUNT,
  "unscanned":2847-COUNT,"carry_forward":2847,"formal_valid_county_screenings":0,"at":NOW()})
try:{"precheck":precheck,"finalize":finalize,"postcheck":postcheck}[STAGE]()
except Exception as e:print("V16_LATE_CASCADE_FAIL",R,STAGE,repr(e),file=sys.stderr);sys.exit(2)
