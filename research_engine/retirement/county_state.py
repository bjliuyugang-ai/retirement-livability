#!/usr/bin/env python3
"""V1.6 single-action geometry QA state handoff. No Library Master modification."""
import datetime,hashlib,json,os,pathlib,subprocess,sys
TASK="6aead9a989808191ad42f80fd4e32bf1"
ACTION="RET-CLIMATE-COUNTY-QA-001"
ROOT=pathlib.Path("tasks")/TASK/"phase1"
STATE=ROOT/"RUN_STATE.json";LOG=ROOT/"RUN_LOG.jsonl"
CURRENT=pathlib.Path("research_assets/retirement/CURRENT_STATE.md")
SOURCE=pathlib.Path("research_engine/retirement/output/county_geometry_qa.json")
DEST=pathlib.Path("research_engine/retirement/status/latest-county-geometry-qa.json")
RUN=os.environ.get("GITHUB_RUN_ID","LOCAL-UNKNOWN")
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def blob(p):return subprocess.check_output(["git","hash-object",str(p)],text=True).strip()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def append(v):
    with LOG.open("a",encoding="utf-8") as f:f.write(json.dumps(v,ensure_ascii=False,sort_keys=True)+"\n")
def read(postcheck_mode=False):
    if not all(p.exists() for p in [STATE,CURRENT,LOG]):raise RuntimeError("STATE_MISSING")
    s=json.loads(STATE.read_text(encoding="utf-8"))
    if s["task_id"]!=TASK or s["schema_version"]!="1.6":raise RuntimeError("STATE_SCHEMA")
    if s["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("STATE_DRIFT")
    if not postcheck_mode:
        if s["active_action"]["action_id"]!=ACTION:raise RuntimeError("ACTION_MISMATCH_OR_CLOSED")
        if s["writeback_verification"]["status"]!="POSTCHECK_PASS":raise RuntimeError("PREVIOUS_POSTCHECK_FAILED")
        if s["last_completed_action_id"]!="RET-OFFICIAL-RECON-001":raise RuntimeError("PRIOR_DEPENDENCY_MISSING")
    else:
        if s["writeback_verification"]["status"]!="PENDING_REMOTE_CHECK":raise RuntimeError("NO_PENDING_POSTCHECK")
        if s["last_verified_run"]["action_id"]!=ACTION:raise RuntimeError("PENDING_ACTION_MISMATCH")
        if s["last_verified_run"]["status"]!="AWAITING_POSTCHECK":raise RuntimeError("PENDING_STATUS_MISMATCH")
    return s
def precheck():
    s=read()
    if SOURCE.exists():SOURCE.unlink()
    receipt={"run_id":RUN,"start":NOW(),"action_id":ACTION,
       "revision":s["state_revision"],"source_current_blob":blob(CURRENT),
       "state_sha256":digest(STATE),"previous_run_id":s["last_verified_run"]["run_id"],
       "previous_result_id":s["last_verified_run"]["result_id"],
       "source_commit":os.getenv("GITHUB_SHA"),"result":"PRECHECK_PASS"}
    save(pathlib.Path("research_engine/retirement/output/county_qa_precheck.json"),receipt)
    print(json.dumps(receipt))
def finalize():
    s=read()
    if SOURCE.exists():d=json.loads(SOURCE.read_text(encoding="utf-8"))
    else:d={"status":"BLOCKED_WITH_EVIDENCE","error":"Geometry source produced no output","valid_county_screenings":0}
    save(DEST,d)
    if d.get("valid_county_screenings")!=0:raise RuntimeError("ILLEGAL_FORMAL_COUNTY_SCREENING")
    passed=(d.get("status")=="PASS_SECOND_BOUNDARY_CODE_QA"
       and d.get("site_count")==12 and d.get("unique_expected_hits")==12
       and d.get("source_geojson_features",0)>=100
       and len(d.get("point_checks",[]))==12
       and all(x.get("two_nonofficial_geometry_sources_agree") for x in d["point_checks"])
       and d.get("official_polygon_verified") is False)
    result="RES-SECONDARY-GEOMETRY-CODE-QA-"+RUN
    if passed:
        delta="DELTA_VERIFIED";engineering="PASS"
        s["last_completed_action_id"]=ACTION
        s["closed_result_refs"].append(result)
        s["active_action"]={
          "action_id":"RET-COUNTY-MICROCLIMATE-QA-001",
          "question_id":"Q-CLIMATE-REPRESENTATIVENESS",
          "decision":"给已匹配的县级点位补充露点、相对湿度、实际海拔与县内地形差异证据；扩大可计算县级覆盖",
          "method":"冻结已匹配12点及县界/代码证据，批量增加1991-2020 ERA5湿度露点及空间差异检验；官方CMA标准值优先，来源与空间口径分级；不以县城点替代全县",
          "expected_evidence":"县级点位气候覆盖字段、质量等级、海拔及河谷/山地/沿海例外、缺口表",
          "pass_criteria":"真实原始气象和空间输入可回放，附县域高差/异常标记及不适宜误排风险；未满足正式证据门槛只记待核",
          "fallback":"无法批量获取官方数据则继续使用明确标注的ERA5试验数据并测试多点区域代表性，保留正式CMA未核",
          "timebox_end":"2026-11-08T15:26:00Z","status":"READY"}
        s["phase"]="COUNTY_MICROCLIMATE_METRICS_ASSAULT"
        s["consecutive_no_delta"]=0
    else:
        delta="BLOCKED_WITH_EVIDENCE";engineering="FAIL"
        s["consecutive_no_delta"]=int(s["consecutive_no_delta"])+1
        s["active_action"]["status"]="BLOCKED_WITH_EVIDENCE" if s["consecutive_no_delta"]<2 else "REQUIRES_DIFFERENT_METHOD"
        s["active_action"]["last_error"]=d.get("error") or "Polygon candidate source did not pass QA"
        s["active_action"]["fallback"]="更换公开地理面数据来源/版本，先核对坐标系与行政编码再重新测试"
    with CURRENT.open("a",encoding="utf-8") as f:
        f.write("\n- "+result+": "+("独立编码县界12点空间匹配验证通过；112个面要素仅用于数据工程，不是县级有效广筛。"
          if passed else "独立编码县界空间验证受阻；错误和证据已登记。")+"\n")
        f.write("- 当前唯一下一动作："+s["active_action"]["action_id"]+"；官方全国代码完整认证和县内微气候仍OPEN。\n")
    s["current_state_ref"]["git_blob_sha"]=blob(CURRENT)
    s["updated_at"]=NOW();s["state_revision"]+=1
    s["last_verified_run"]={"run_id":RUN,"action_id":ACTION,"result_id":result,"execution_status":"EXECUTED",
       "engineering_status":engineering,"research_delta_status":delta,"research_closure_status":"OPEN",
       "evidence_path":str(DEST),"evidence_sha256":digest(DEST),"status":"AWAITING_POSTCHECK"}
    s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK","verified_commit":None}
    save(STATE,s)
    pre=json.loads(pathlib.Path("research_engine/retirement/output/county_qa_precheck.json").read_text(encoding="utf-8"))
    append({"kind":"S0-S5","run_id":RUN,"action_id":ACTION,"start":pre["start"],
      "source_revision":pre["revision"],"source_commit":pre["source_commit"],"end":NOW(),
      "command":"python research_engine/retirement/county_geometry_qa.py",
      "result_id":result,"evidence":str(DEST),"evidence_sha256":digest(DEST),
      "engineering_status":engineering,"research_delta_status":delta,
      "research_closure_status":"OPEN","next_action_id":s["active_action"]["action_id"],
      "writeback":"PENDING_REMOTE_CHECK"})
    print(json.dumps({"run_id":RUN,"engineering":engineering,"delta":delta,
      "next_action":s["active_action"]["action_id"],"counties_effective":0}))
def postcheck():
    s=read(postcheck_mode=True)
    original_run=s["last_verified_run"]["run_id"]
    recovery=os.environ.get("REPAIR_PENDING_POSTCHECK")=="1"
    if original_run!=RUN and not recovery:raise RuntimeError("RUN_ID_MISMATCH")
    if recovery and s["last_verified_run"]["engineering_status"]!="FAIL":
        raise RuntimeError("RECOVERY_ONLY_ALLOWED_FOR_PREVIOUSLY_FAILED_RUN")
    remote=json.loads(subprocess.check_output(["git","show","origin/main:"+str(STATE)],text=True))
    if remote["state_revision"]!=s["state_revision"] or remote["last_verified_run"]["run_id"]!=original_run:raise RuntimeError("REMOTE_STATE_MISMATCH")
    if remote["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("REMOTE_CURRENT_DRIFT")
    remote_evidence=subprocess.check_output(["git","show","origin/main:"+str(DEST)])
    if hashlib.sha256(remote_evidence).hexdigest()!=s["last_verified_run"]["evidence_sha256"]:
        raise RuntimeError("REMOTE_EVIDENCE_HASH_MISMATCH")
    remote_log=subprocess.check_output(["git","show","origin/main:"+str(LOG)],text=True)
    if not any(json.loads(line).get("run_id")==original_run and json.loads(line).get("kind")=="S0-S5"
               for line in remote_log.splitlines() if line.strip()):
        raise RuntimeError("REMOTE_RUN_LOG_MISSING")
    subprocess.check_output(["git","show","origin/main:"+str(CURRENT)])
    s["writeback_verification"]={"status":"POSTCHECK_PASS",
       "verified_commit":subprocess.check_output(["git","rev-parse","origin/main"],text=True).strip(),
       "verified_at":NOW()}
    s["last_verified_run"]["status"]="POSTCHECK_PASS"
    s["updated_at"]=NOW();s["state_revision"]+=1
    save(STATE,s)
    append({"kind":"S6_POSTCHECK_RECOVERY" if recovery else "S6_POSTCHECK",
            "run_id":original_run,"recovery_run_id":RUN if recovery else None,
            "original_engineering_status":s["last_verified_run"]["engineering_status"],
            "action_id":ACTION,"at":NOW(),"postcheck":"PASS",
            "state_revision":s["state_revision"],
            "evidence_sha256":s["last_verified_run"]["evidence_sha256"]})
    print("POSTCHECK_PASS",original_run,"recovery",recovery)
if __name__=="__main__":
    try:{"precheck":precheck,"finalize":finalize,"postcheck":postcheck}[sys.argv[1]]()
    except Exception as exc:
        print("V1.6_COUNTY_GEOMETRY_GATE_FAIL",repr(exc),file=sys.stderr);sys.exit(2)
