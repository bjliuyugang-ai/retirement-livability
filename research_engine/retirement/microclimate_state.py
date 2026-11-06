#!/usr/bin/env python3
"""S0-S6 evidence handoff for exploratory microclimate assay, no formal county rating."""
import datetime,hashlib,json,os,pathlib,subprocess,sys
TASK="6aead9a989808191ad42f80fd4e32bf1"
ACTION="RET-COUNTY-MICROCLIMATE-QA-001"
ROOT=pathlib.Path("tasks")/TASK/"phase1";STATE=ROOT/"RUN_STATE.json";LOG=ROOT/"RUN_LOG.jsonl"
CURRENT=pathlib.Path("research_assets/retirement/CURRENT_STATE.md")
OUT=pathlib.Path("research_engine/retirement/output")
SOURCE=OUT/"microclimate_pilot.json"
DEST=pathlib.Path("research_engine/retirement/status/latest-microclimate-pilot.json")
RUN=os.environ.get("GITHUB_RUN_ID","LOCAL-UNKNOWN")
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def gitblob(p):return subprocess.check_output(["git","hash-object",str(p)],text=True).strip()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def append(d):
    with LOG.open("a",encoding="utf-8") as h:h.write(json.dumps(d,ensure_ascii=False,sort_keys=True)+"\n")
def read(postcheck=False):
    if not all(p.exists() for p in [STATE,CURRENT,LOG]):raise RuntimeError("STATE_MISSING")
    s=json.loads(STATE.read_text(encoding="utf-8"))
    if s["task_id"]!=TASK or s["schema_version"]!="1.6":raise RuntimeError("STATE_SCHEMA_INVALID")
    if s["current_state_ref"]["git_blob_sha"]!=gitblob(CURRENT):raise RuntimeError("STATE_DRIFT")
    if not postcheck:
        if s["active_action"]["action_id"]!=ACTION:raise RuntimeError("ACTIVE_ACTION_MISMATCH")
        if s["writeback_verification"]["status"]!="POSTCHECK_PASS":raise RuntimeError("UNVERIFIED_PRIOR_WRITE")
        if s["last_completed_action_id"]!="RET-CLIMATE-COUNTY-QA-001":raise RuntimeError("PRIOR_GEOMETRY_QA_MISSING")
    else:
        if s["writeback_verification"]["status"]!="PENDING_REMOTE_CHECK":raise RuntimeError("NO_PENDING_WRITE")
        if s["last_verified_run"]["run_id"]!=RUN:raise RuntimeError("RUN_ID_MISMATCH")
        if s["last_verified_run"]["action_id"]!=ACTION:raise RuntimeError("ACTION_ID_MISMATCH")
    return s
def precheck():
    s=read()
    if SOURCE.exists():SOURCE.unlink()
    write(OUT/"microclimate_precheck.json",{"run_id":RUN,"action_id":ACTION,"start":NOW(),
      "revision":s["state_revision"],"current_state_blob":gitblob(CURRENT),
      "state_sha256":digest(STATE),"prev_result":s["last_verified_run"]["result_id"],
      "source_commit":os.environ.get("GITHUB_SHA"),"status":"PASS"})
def finalize():
    s=read()
    d=json.loads(SOURCE.read_text(encoding="utf-8")) if SOURCE.exists() else {"status":"BLOCKED_WITH_EVIDENCE","error":"No output from microclimate script","valid_county_screenings":0}
    write(DEST,d)
    if d.get("valid_county_screenings")!=0:raise RuntimeError("ILLEGAL_FORMAL_COUNTY_SCREEN")
    points=d.get("points",[])
    passed=(d.get("status")=="PASS_ELEVATION_SENSITIVITY" and d.get("sites_count")==12
      and d.get("dem_points_loaded")==36 and len(points)==12
      and len({x.get("candidate_county_code") for x in points})==12
      and all(len(x.get("points",[]))==3 and x.get("sample_dem_span_m") is not None for x in points)
      and d.get("official_county_codes_verified")==0)
    delta="DELTA_VERIFIED" if passed else "BLOCKED_WITH_EVIDENCE"
    result="RES-DEM-ERA5-MOISTURE-EXPLORATORY-"+RUN
    if passed:
        s["last_completed_action_id"]=ACTION
        s["closed_result_refs"].append(result)
        s["consecutive_no_delta"]=0
        s["active_action"]={
          "action_id":"RET-CLIMATE-SPATIAL-REPRESENTATIVENESS-002",
          "question_id":"Q-CLIMATE-REPRESENTATIVENESS",
          "decision":"判断县内海拔与气候空间异质性是否显著，进一步形成可信县级气候证据或待核",
          "method":"使用冻结DEM采样与ERA5辅助数据检验县域代表性并与可靠站点或CMA1991-2020常年值交叉核对；保留未核县内河谷/沿海异质性",
          "expected_evidence":"有来源和坐标的县级多点时空差异证据、局部微气候例外、覆盖质量与缺口",
          "pass_criteria":"实际空间样本和温湿日照数据同口径可复现；确认县域覆盖/例外方可生成真正有效的广筛记录",
          "fallback":"如果CMA取数不可达，则以有证据的多格点逐日ERA5探索性审查保留待核，不作正式淘汰",
          "timebox_end":"2026-11-08T15:26:00Z","status":"READY"}
        s["phase"]="SPATIAL_REPRESENTATIVENESS_ASSAULT"
    else:
        s["consecutive_no_delta"]=int(s["consecutive_no_delta"])+1
        s["active_action"]["status"]="BLOCKED_WITH_EVIDENCE" if s["consecutive_no_delta"]<2 else "REQUIRES_DIFFERENT_METHOD"
        s["active_action"]["last_error"]=d.get("error") or "DEM and humidity criteria failed"
    with CURRENT.open("a",encoding="utf-8") as h:
        h.write("\n- "+result+": "+("12县级点位完成36个县内Copernicus DEM海拔采样；ERA5露点/湿度真实读取数和地形例外标记详见证据；属于探索性数据工程，正式广筛0。"
           if passed else "微气候DEM或ERA5取数工程失败，详见证据；正式广筛0。")+"\n")
    s["current_state_ref"]["git_blob_sha"]=gitblob(CURRENT)
    s["updated_at"]=NOW();s["state_revision"]+=1
    s["last_verified_run"]={"run_id":RUN,"action_id":ACTION,"result_id":result,
      "execution_status":"EXECUTED","engineering_status":"PASS" if passed else "FAIL",
      "research_delta_status":delta,"research_closure_status":"OPEN",
      "evidence_path":str(DEST),"evidence_sha256":digest(DEST),"status":"AWAITING_POSTCHECK"}
    s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK","verified_commit":None}
    write(STATE,s)
    pre=json.loads((OUT/"microclimate_precheck.json").read_text(encoding="utf-8"))
    append({"kind":"S0-S5","run_id":RUN,"start":pre["start"],"end":NOW(),"action_id":ACTION,
      "source_revision":pre["revision"],"source_commit":pre["source_commit"],
      "command":"python research_engine/retirement/microclimate_pilot.py",
      "evidence_path":str(DEST),"evidence_sha256":digest(DEST),
      "engineering_status":"PASS" if passed else "FAIL","research_delta_status":delta,
      "research_closure_status":"OPEN","next_action":s["active_action"]["action_id"],
      "result_id":result,"writeback":"PENDING_REMOTE_CHECK"})
    print(json.dumps({"engineering":"PASS" if passed else "FAIL","result":result,
      "humidity_sites":d.get("humidity_sites_loaded"),"dem_points":d.get("dem_points_loaded"),
      "county_screenings":0,"next_action":s["active_action"]["action_id"]}))
def postcheck():
    s=read(postcheck=True)
    remote=json.loads(subprocess.check_output(["git","show","origin/main:"+str(STATE)],text=True))
    if remote["state_revision"]!=s["state_revision"] or remote["last_verified_run"]["run_id"]!=RUN:raise RuntimeError("REMOTE_STATE_MISMATCH")
    if remote["current_state_ref"]["git_blob_sha"]!=gitblob(CURRENT):raise RuntimeError("REMOTE_CURRENT_DRIFT")
    data=subprocess.check_output(["git","show","origin/main:"+str(DEST)])
    if hashlib.sha256(data).hexdigest()!=s["last_verified_run"]["evidence_sha256"]:raise RuntimeError("REMOTE_EVIDENCE_HASH_MISMATCH")
    lines=subprocess.check_output(["git","show","origin/main:"+str(LOG)],text=True).splitlines()
    if not any(json.loads(l).get("run_id")==RUN and json.loads(l).get("kind")=="S0-S5" for l in lines if l.strip()):raise RuntimeError("REMOTE_LOG_MISSING")
    s["writeback_verification"]={"status":"POSTCHECK_PASS",
      "verified_commit":subprocess.check_output(["git","rev-parse","origin/main"],text=True).strip(),
      "verified_at":NOW()}
    s["last_verified_run"]["status"]="POSTCHECK_PASS"
    s["updated_at"]=NOW();s["state_revision"]+=1
    write(STATE,s)
    append({"kind":"S6_POSTCHECK","run_id":RUN,"action_id":ACTION,
      "at":NOW(),"postcheck":"PASS","state_revision":s["state_revision"]})
    print("MICROCLIMATE_POSTCHECK_PASS",RUN)
if __name__=="__main__":
    try:{"precheck":precheck,"finalize":finalize,"postcheck":postcheck}[sys.argv[1]]()
    except Exception as exc:
        print("V1.6_MICROCLIMATE_GATE_FAIL",repr(exc),file=sys.stderr);sys.exit(2)
