#!/usr/bin/env python3
"""V1.6 S0-S6 state transaction for multi-point spatial-variability experiment."""
import datetime,hashlib,json,os,pathlib,subprocess,sys
TASK="6aead9a989808191ad42f80fd4e32bf1"
ACTION="RET-CLIMATE-SPATIAL-REPRESENTATIVENESS-002"
ROOT=pathlib.Path("tasks")/TASK/"phase1";STATE=ROOT/"RUN_STATE.json";LOG=ROOT/"RUN_LOG.jsonl"
CURRENT=pathlib.Path("research_assets/retirement/CURRENT_STATE.md")
OUT=pathlib.Path("research_engine/retirement/output")
SOURCE=OUT/"spatial_variability_002.json"
DEST=pathlib.Path("research_engine/retirement/status/latest-spatial-variability-002.json")
RUN=os.getenv("GITHUB_RUN_ID","LOCAL-UNKNOWN")
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def blob(p):return subprocess.check_output(["git","hash-object",str(p)],text=True).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def log(obj):
    with LOG.open("a",encoding="utf-8") as f:f.write(json.dumps(obj,ensure_ascii=False,sort_keys=True)+"\n")
def read(post=False):
    if any(not p.exists() for p in (STATE,LOG,CURRENT)):raise RuntimeError("STATE_MISSING")
    s=json.loads(STATE.read_text(encoding="utf-8"))
    if s.get("schema_version")!="1.6" or s.get("task_id")!=TASK:raise RuntimeError("STATE_SCHEMA_BAD")
    if s["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("STATE_DRIFT")
    if not post:
        if s["active_action"]["action_id"]!=ACTION:raise RuntimeError("UNIQUE_ACTION_MISMATCH")
        if s["writeback_verification"]["status"]!="POSTCHECK_PASS":raise RuntimeError("PREVIOUS_WRITE_UNVERIFIED")
        if s["last_completed_action_id"]!="RET-COUNTY-MICROCLIMATE-QA-001":raise RuntimeError("PREREQUISITE_MISSING")
    else:
        if s["writeback_verification"]["status"]!="PENDING_REMOTE_CHECK":raise RuntimeError("POSTCHECK_NO_PENDING")
        if s["last_verified_run"]["run_id"]!=RUN:raise RuntimeError("RUN_MISMATCH")
    return s
def precheck():
    s=read()
    if SOURCE.exists():SOURCE.unlink()
    write(OUT/"spatial_variability_002_precheck.json",{"run_id":RUN,"action_id":ACTION,"start":NOW(),
     "source_revision":s["state_revision"],"current_blob":blob(CURRENT),
     "state_sha256":sha(STATE),"source_commit":os.getenv("GITHUB_SHA"),
     "last_result_id":s["last_verified_run"]["result_id"]})
def finalize():
    s=read()
    raw=json.loads(SOURCE.read_text(encoding="utf-8")) if SOURCE.exists() else {"status":"BLOCKED_WITH_EVIDENCE","error":"No source result","formal_county_screenings":0}
    write(DEST,raw)
    if raw.get("formal_county_screenings")!=0:raise RuntimeError("EXPLORATORY_MUST_NOT_MARK_COUNTY_SCREENINGS")
    cases=raw.get("cases",[])
    passed=raw.get("status")=="PASS_EXPLORATORY_SPATIAL_VARIABILITY" and len(cases)==4 and raw.get("request_count_completed")==12 and all(x.get("succeeded")==3 and len(x.get("metric_spans",{}))==5 for x in cases)
    decision="DELTA_VERIFIED" if passed else "BLOCKED_WITH_EVIDENCE"
    result_id="RES-SPATIAL-MULTIGRID-002-"+RUN
    if passed:
        s["last_completed_action_id"]=ACTION
        s["closed_result_refs"].append(result_id)
        s["consecutive_no_delta"]=0
        s["active_action"]={"action_id":"RET-CMA-ERA5-CROSSCHECK-003",
         "question_id":"Q-CLIMATE-REPRESENTATIVENESS",
         "decision":"交叉检验ERA5多点气候差异与可溯源站点1991-2020标准值，判别是否具备县级广筛资格",
         "method":"优先CMA真实常年值/可下载历史站点数据；同基期同空间口径比较；局部微气候例外逐项标待核",
         "expected_evidence":"站点真实来源、日期、气温/日照/湿度与格点差异、无法核验县域列表",
         "pass_criteria":"以合格身份与空间证据支持逐县有效判断；不具备资格明确待核和阻塞而非误判D",
         "fallback":"站点数据不可达则扩宽独立空间来源并以不具备正式广筛资格裁决",
         "timebox_end":"2026-11-08T15:26:00Z","status":"READY"}
        s["phase"]="CMA_ERA5_CROSSCHECK_ASSAULT"
    else:
        s["consecutive_no_delta"]=int(s.get("consecutive_no_delta",0))+1
        s["active_action"]["status"]="BLOCKED_WITH_EVIDENCE" if s["consecutive_no_delta"]<2 else "REQUIRES_ALTERNATIVE_METHOD"
        s["active_action"]["last_error"]=raw.get("error") or str(raw.get("errors",[]))[:1200]
    with CURRENT.open("a",encoding="utf-8") as f:
        f.write("\n- "+result_id+": "+("4个高海拔差异县域完成12格点1991-2020 ERA5气候差异实测，保留微气候例外，不能据此完成正式县级广筛。" if passed else "多格点气候差异实测被阻塞，原始错误见证据；县级有效广筛仍为0。")+"\n")
    s["current_state_ref"]["git_blob_sha"]=blob(CURRENT)
    s["state_revision"]+=1;s["updated_at"]=NOW()
    s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK","verified_commit":None}
    s["last_verified_run"]={"run_id":RUN,"action_id":ACTION,"result_id":result_id,
      "execution_status":"EXECUTED","engineering_status":"PASS" if passed else "FAIL",
      "research_delta_status":decision,"research_closure_status":"OPEN",
      "evidence_path":str(DEST),"evidence_sha256":sha(DEST),"status":"AWAITING_POSTCHECK"}
    write(STATE,s)
    pre=json.loads((OUT/"spatial_variability_002_precheck.json").read_text(encoding="utf-8"))
    log({"kind":"S0-S5","run_id":RUN,"start":pre["start"],"end":NOW(),
      "action_id":ACTION,"source_revision":pre["source_revision"],"source_commit":pre["source_commit"],
      "command":"python research_engine/retirement/spatial_variability_002.py",
      "evidence_path":str(DEST),"evidence_sha256":sha(DEST),"result_id":result_id,
      "engineering_status":"PASS" if passed else "FAIL","research_delta_status":decision,
      "next_action_id":s["active_action"]["action_id"],"writeback":"PENDING_REMOTE_CHECK"})
    print(json.dumps({"passed":passed,"sites":len(cases),"requests":raw.get("request_count_completed"),
      "delta":decision,"next":s["active_action"]["action_id"]},ensure_ascii=False))
def postcheck():
    s=read(post=True)
    rr=json.loads(subprocess.check_output(["git","show","origin/main:"+str(STATE)],text=True))
    if rr["state_revision"]!=s["state_revision"] or rr["last_verified_run"]["run_id"]!=RUN:raise RuntimeError("REMOTE_STATE_MISMATCH")
    if rr["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("REMOTE_CURRENT_BLOB_MISMATCH")
    remote=subprocess.check_output(["git","show","origin/main:"+str(DEST)])
    if hashlib.sha256(remote).hexdigest()!=s["last_verified_run"]["evidence_sha256"]:raise RuntimeError("REMOTE_EVIDENCE_SHA_MISMATCH")
    entries=subprocess.check_output(["git","show","origin/main:"+str(LOG)],text=True).splitlines()
    if not any(json.loads(x).get("run_id")==RUN and json.loads(x).get("kind")=="S0-S5" for x in entries if x.strip()):
        raise RuntimeError("REMOTE_LOG_MISSING")
    s["writeback_verification"]={"status":"POSTCHECK_PASS",
       "verified_commit":subprocess.check_output(["git","rev-parse","origin/main"],text=True).strip(),
       "verified_at":NOW()}
    s["last_verified_run"]["status"]="POSTCHECK_PASS"
    s["state_revision"]+=1;s["updated_at"]=NOW()
    write(STATE,s)
    log({"kind":"S6_POSTCHECK","run_id":RUN,"at":NOW(),"action_id":ACTION,"postcheck":"PASS","state_revision":s["state_revision"]})
if __name__=="__main__":
    try:{"precheck":precheck,"finalize":finalize,"postcheck":postcheck}[sys.argv[1]]()
    except Exception as e:print("V1.6_GATE_FAIL",repr(e),file=sys.stderr);sys.exit(2)
