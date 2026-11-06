#!/usr/bin/env python3
"""V1.6 phase1 assault gate: check -> judge -> writeback -> remote postcheck.

This script manages *execution state*, not the formal Library research Master.
No exploratory point/polygon match counts as valid county screening.
"""
import datetime, hashlib, json, os, pathlib, subprocess, sys

TASK="6aead9a989808191ad42f80fd4e32bf1"
ROOT=pathlib.Path("tasks")/TASK/"phase1"
STATE=ROOT/"RUN_STATE.json"
LOG=ROOT/"RUN_LOG.jsonl"
CURRENT=pathlib.Path("research_assets/retirement/CURRENT_STATE.md")
OUTPUT=pathlib.Path("retirement-climate-pilot/output")
ACTION=os.getenv("ASSAULT_ACTION","RET-SPATIAL-001")
SOURCE_NAME="adcode_probe.json" if ACTION=="RET-ADCODE-001" else "spatial_probe.json"
STATUS=pathlib.Path("retirement-climate-pilot/status")/("latest-adcode-probe.json" if ACTION=="RET-ADCODE-001" else "latest-spatial-probe.json")
COMMAND="python retirement-climate-pilot/adcode_probe.py" if ACTION=="RET-ADCODE-001" else "python retirement-climate-pilot/spatial_probe.py"
RUN_ID=os.getenv("GITHUB_RUN_ID","MANUAL-UNKNOWN")
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def blob_sha(path):
    return subprocess.check_output(["git","hash-object",str(path)],text=True).strip()
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def load_state():
    if not STATE.exists() or not LOG.exists() or not CURRENT.exists():
        raise RuntimeError("STATE_MISSING: required RUN_STATE, RUN_LOG or CURRENT_STATE missing")
    state=json.loads(STATE.read_text(encoding="utf-8"))
    req=["schema_version","task_id","track_id","authority","current_state_ref",
         "last_verified_run","last_completed_action_id","closed_result_refs",
         "active_action","phase","milestone_deadline","consecutive_no_delta",
         "writeback_verification","updated_at","state_revision"]
    missing=[k for k in req if k not in state]
    if missing: raise RuntimeError("STATE_SCHEMA_MISSING: "+repr(missing))
    if state["schema_version"]!="1.6" or state["task_id"]!=TASK:raise RuntimeError("STATE_ID_MISMATCH")
    if state["authority"]["branch"]!="main":raise RuntimeError("BRANCH_MISMATCH")
    if state["current_state_ref"]["git_blob_sha"]!=blob_sha(CURRENT):
        raise RuntimeError("STATE_DRIFT: CURRENT_STATE blob SHA differs from RUN_STATE")
    if not LOG.read_text(encoding="utf-8").strip(): raise RuntimeError("EMPTY_RUN_LOG")
    return state
def emit_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def append_log(row):
    with LOG.open("a",encoding="utf-8") as f:f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")
def precheck():
    s=load_state()
    a=s["active_action"]
    if a.get("action_id")!=ACTION:
        raise RuntimeError("NO_ACTION_OR_WRONG_ACTION: expected "+ACTION+" but got "+str(a.get("action_id")))
    if s["writeback_verification"]["status"] in ("PENDING_REMOTE_CHECK","WRITEBACK_FAILED"):
        raise RuntimeError("PREVIOUS_WRITEBACK_UNVERIFIED")
    if (OUTPUT/SOURCE_NAME).exists(): (OUTPUT/SOURCE_NAME).unlink()
    receipt={"run_id":RUN_ID,"action_id":ACTION,"read_at":NOW(),"state_revision":s["state_revision"],
      "state_sha256":digest(STATE),"current_blob_sha":blob_sha(CURRENT),
      "source_commit":os.getenv("GITHUB_SHA"),"last_verified_run":s["last_verified_run"],
      "previous_result_refs":s["closed_result_refs"],"status":"PRECHECK_PASS"}
    emit_json(OUTPUT/"precheck_receipt.json",receipt)
    print(json.dumps(receipt,ensure_ascii=False))
def finalize():
    s=load_state()
    if s["active_action"].get("action_id")!=ACTION:raise RuntimeError("WRONG_ACTION_AT_FINALIZE")
    source=json.loads((OUTPUT/SOURCE_NAME).read_text(encoding="utf-8")) if (OUTPUT/SOURCE_NAME).exists() else {
      "status":"BLOCKED_WITH_EVIDENCE","error":SOURCE_NAME+" did not write output","valid_county_screenings":0}
    emit_json(STATUS,source)
    pts=source.get("point_hits") or []
    if ACTION=="RET-ADCODE-001":
        codes=source.get("candidate_links") or []
        passed=(source.get("status")=="PASS_ARCHIVAL_CODE_CANDIDATES"
          and len(codes)==12 and all(x.get("candidate_count")==1 and x.get("candidate_code") for x in codes)
          and int(source.get("raw_area_count",0))>=2500
          and int(source.get("official_code_verified",1))==0
          and int(source.get("valid_county_screenings",-1))==0)
    else:
        passed=(source.get("status")=="PASS_HISTORIC_POINT_IN_POLYGON"
          and int(source.get("geometry_features_loaded",0))>=2000
          and len(pts)==12 and all("historic_polygon_hits" in p for p in pts)
          and source.get("geometry_sha256") and int(source.get("valid_county_screenings",-1))==0)
    decision="DELTA_VERIFIED" if passed else "BLOCKED_WITH_EVIDENCE"
    if source.get("valid_county_screenings",0)!=0:raise RuntimeError("ILLEGAL_COUNTY_SCREENING_IN_EXPLORATORY_SPATIAL")
    started=json.loads((OUTPUT/"precheck_receipt.json").read_text(encoding="utf-8"))
    evidence_sha=digest(STATUS)
    result_id=("RES-ARCHIVAL-ADCODE-" if ACTION=="RET-ADCODE-001" else "RES-SPATIAL-ENGINEERING-")+RUN_ID
    line=("\n- "+result_id+": "+("历史开源行政代码与历史县界12点对齐" if ACTION=="RET-ADCODE-001" else "2017历史边界点面匹配")+"；"+
          ("工程PASS，仅代表候选编码，不等于2026官方对账，也不计有效县级广筛。" if passed else "BLOCKED，错误："+str(source.get("error","criteria failed"))+"；有效县级广筛仍为0。"))
    with CURRENT.open("a",encoding="utf-8") as f:f.write(line+"\n")
    if passed:
        s["last_completed_action_id"]=ACTION
        s["closed_result_refs"].append(result_id)
        if ACTION=="RET-ADCODE-001":
            s["active_action"]={
              "action_id":"RET-OFFICIAL-RECON-001","question_id":"Q-OFFICIAL-ADCODE",
              "decision":"把已找到的历史代码候选逐一与现行官方县级名录核对，处理行政调整和微气候例外",
              "method":"获取官方县级代码及口径，逐项作差集和名称层级查验；核对空间代表性与海拔差异",
              "expected_evidence":"可核验现行行政代码逐项差集、历史冲突、例外与无法核验名单",
              "pass_criteria":"真实官方来源逐项比对并明确空间代表性；无证据标UNKNOWN",
              "fallback":"更换官方来源或缩小验证窗口，保留现行官方未获证据状态",
              "timebox_end":"2026-11-08T15:26:00Z","status":"READY"}
            s["phase"]="OFFICIAL_CURRENT_ADCODE_QA"
        else:
            s["active_action"]={
              "action_id":"RET-ADCODE-001","question_id":"Q-OFFICIAL-ADCODE",
              "decision":"历史县界真实命中点位与独立历史行政代码候选对齐",
              "method":"从开源行政区划归档获取三级代码，按省-地-县层级和人工核对的双语名称做唯一候选关联",
              "expected_evidence":"retirement-climate-pilot/status/latest-adcode-probe.json",
              "pass_criteria":"12点全部获得独立历史代码唯一候选、来源hash记录，明确非2026官方且不计有效广筛",
              "fallback":"数据下载受阻则走GitHub可访问内容源，禁止重复泛搜",
              "timebox_end":"2026-11-08T15:26:00Z","status":"READY"}
            s["phase"]="ARCHIVAL_CODE_CANDIDATE_MATCH"
        s["consecutive_no_delta"]=0
    else:
        s["active_action"]["status"]="BLOCKED_WITH_EVIDENCE"
        s["active_action"]["last_error"]=str(source.get("error","spatial proof criteria not met"))
        s["consecutive_no_delta"]=int(s["consecutive_no_delta"])+1
        if s["consecutive_no_delta"]>=2:
            s["active_action"]["status"]="REQUIRES_DIFFERENT_METHOD"
            s["active_action"]["fallback"]="必须更换对应步骤的合法数据来源或访问方式；不得第三次同法运行"
    s["current_state_ref"]["git_blob_sha"]=blob_sha(CURRENT)
    s["updated_at"]=NOW()
    s["state_revision"]+=1
    s["last_verified_run"]={"run_id":RUN_ID,"action_id":ACTION,"result_id":result_id,
       "research_delta_status":decision,"execution_status":"EXECUTED" if source.get("status") else "BLOCKED",
       "engineering_status":"PASS" if passed else "FAIL",
       "research_closure_status":"OPEN","evidence_path":str(STATUS),"evidence_sha256":evidence_sha,
       "status":"AWAITING_POSTCHECK"}
    s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK","verified_commit":None}
    emit_json(STATE,s)
    append_log({"run_id":RUN_ID,"start_time":started["read_at"],"end_time":NOW(),"kind":"S0-S5",
      "source_revision":started["state_revision"],"action_id":ACTION,
      "input_blob_sha":started["current_blob_sha"],"actual_command":COMMAND,
      "evidence_path":str(STATUS),"evidence_sha256":evidence_sha,"result_id":result_id,
      "execution_status":s["last_verified_run"]["execution_status"],
      "engineering_status":s["last_verified_run"]["engineering_status"],
      "research_delta_status":decision,"research_closure_status":"OPEN",
      "writeback":"PENDING_REMOTE_CHECK","next_action_id":s["active_action"]["action_id"]})
    print(json.dumps({"run_id":RUN_ID,"research_delta":decision,"engineering_pass":passed,
       "result_id":result_id,"next_action":s["active_action"]["action_id"]},ensure_ascii=False))
def postcheck():
    s=load_state()
    if s["last_verified_run"]["run_id"]!=RUN_ID:raise RuntimeError("RUN_ID_MISMATCH")
    remote_state=subprocess.check_output(["git","show","origin/main:"+str(STATE)],text=True)
    rr=json.loads(remote_state)
    if rr["state_revision"]!=s["state_revision"] or rr["last_verified_run"]["run_id"]!=RUN_ID:
        raise RuntimeError("REMOTE_STATE_MISMATCH")
    if rr["current_state_ref"]["git_blob_sha"]!=blob_sha(CURRENT):
        raise RuntimeError("REMOTE_CURRENT_STATE_MISMATCH")
    for path in (STATUS,CURRENT,LOG):
        subprocess.check_output(["git","show","origin/main:"+str(path)])
    s["writeback_verification"]={"status":"POSTCHECK_PASS","verified_commit":subprocess.check_output(["git","rev-parse","origin/main"],text=True).strip(),"verified_at":NOW()}
    s["last_verified_run"]["status"]="POSTCHECK_PASS"
    s["updated_at"]=NOW();s["state_revision"]+=1
    emit_json(STATE,s)
    append_log({"kind":"S6_POSTCHECK","run_id":RUN_ID,"at":NOW(),"action_id":s["last_verified_run"]["action_id"],
      "postcheck":"PASS","checked_paths":[str(STATE),str(CURRENT),str(STATUS),str(LOG)],
      "state_revision":s["state_revision"]})
    print(json.dumps({"postcheck":"PASS","run_id":RUN_ID,"state_revision":s["state_revision"]}))
def selftest():
    s=load_state()
    assert s["active_action"]["action_id"] not in [None,""],"missing action"
    assert isinstance(s["closed_result_refs"],list)
    assert len(s["closed_result_refs"])==len(set(s["closed_result_refs"]))
    # Prevent accidental classification of exploratory data as valid screening.
    sm=pathlib.Path("retirement-climate-pilot/status/latest-summary.json")
    if sm.exists():
        d=json.loads(sm.read_text(encoding="utf-8"))
        assert d["valid_county_screenings"]==0
    print("V1.6_SCHEMA_AND_EXPLORATORY_GUARDS_PASS")
if __name__=="__main__":
    try:
        {"precheck":precheck,"finalize":finalize,"postcheck":postcheck,"selftest":selftest}[sys.argv[1]]()
    except Exception as exc:
        print("V1.6_GATE_FAIL:",repr(exc),file=sys.stderr);sys.exit(2)
