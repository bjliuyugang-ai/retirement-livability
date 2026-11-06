#!/usr/bin/env python3
"""S0-S6 attack-state handoff for RET-OFFICIAL-RECON-001 only.
Do not use for Library Master or any county suitability rating.
"""
import datetime,hashlib,json,os,pathlib,subprocess,sys
TASK="6aead9a989808191ad42f80fd4e32bf1"
ACTION="RET-OFFICIAL-RECON-001"
MODE=os.environ.get("OFFICIAL_RECON_MODE","direct")
ROOT=pathlib.Path("tasks")/TASK/"phase1"
STATE=ROOT/"RUN_STATE.json";LOG=ROOT/"RUN_LOG.jsonl"
CURRENT=pathlib.Path("research_assets/retirement/CURRENT_STATE.md")
SOURCE=pathlib.Path("research_engine/retirement/output")/("provisional_roster_summary.json" if MODE=="fallback" else "official_probe.json")
EVIDENCE=pathlib.Path("research_engine/retirement/status")/("latest-provisional-roster.json" if MODE=="fallback" else "latest-official-recon.json")
RUN=os.environ.get("GITHUB_RUN_ID","LOCAL-UNKNOWN")
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def blob(path):return subprocess.check_output(["git","hash-object",str(path)],text=True).strip()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def append(value):
    with LOG.open("a",encoding="utf-8") as fh:fh.write(json.dumps(value,ensure_ascii=False,sort_keys=True)+"\n")
def getstate():
    if not all(p.exists() for p in (STATE,LOG,CURRENT)):raise RuntimeError("STATE_MISSING")
    s=json.loads(STATE.read_text(encoding="utf-8"))
    for k in ["schema_version","task_id","authority","current_state_ref","active_action","closed_result_refs","last_verified_run","state_revision","writeback_verification"]:
        if k not in s:raise RuntimeError("STATE_SCHEMA_MISSING_"+k)
    if s["schema_version"]!="1.6" or s["task_id"]!=TASK:raise RuntimeError("STATE_SCHEMA_OR_TASK_INVALID")
    if s["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("STATE_DRIFT")
    return s
def precheck():
    s=getstate()
    if s["active_action"].get("action_id")!=ACTION:raise RuntimeError("NO_ACTION_OR_ILLEGAL_REOPEN")
    if s["writeback_verification"]["status"]!="POSTCHECK_PASS":raise RuntimeError("PREVIOUS_WRITEBACK_UNVERIFIED")
    if s["last_completed_action_id"]!="RET-ADCODE-001":raise RuntimeError("PREVIOUS_RESULT_NOT_CLOSED")
    if MODE=="direct" and s["active_action"].get("status")=="REQUIRES_DIFFERENT_METHOD":raise RuntimeError("OLD_METHOD_FORBIDDEN")
    if SOURCE.exists():SOURCE.unlink()
    receipt={"run_id":RUN,"action_id":ACTION,"start":NOW(),"start_state_revision":s["state_revision"],
       "state_sha256":sha(STATE),"previous_run":s["last_verified_run"]["run_id"],
       "previous_result":s["last_verified_run"]["result_id"],
       "current_state_blob":blob(CURRENT),"source_commit":os.getenv("GITHUB_SHA"),
       "result":"PRECHECK_PASS"}
    write(pathlib.Path("research_engine/retirement/output/official_precheck.json"),receipt)
    print(json.dumps(receipt,ensure_ascii=False))
def finalize():
    s=getstate()
    if s["active_action"]["action_id"]!=ACTION:raise RuntimeError("ACTION_DID_NOT_MATCH")
    if SOURCE.exists():d=json.loads(SOURCE.read_text(encoding="utf-8"))
    else:d={"status":"OFFICIAL_DIRECT_UNAVAILABLE","error":"The source script never emitted output","valid_county_screenings":0}
    write(EVIDENCE,d)
    if int(d.get("valid_county_screenings",-1))!=0:raise RuntimeError("INVALID_OFFICIAL_ONLY_COUNTY_SCREENING")
    attempts=d.get("official_attempts",[])
    if MODE=="fallback":
        passed=(d.get("status")=="PASS_PROVISIONAL_ROSTER_BUILD"
            and int(d.get("mirror_2025_counties",0))==2845
            and int(d.get("provisional_2026_midyear_count",0))==2847
            and int(d.get("2026_verified_legal_establishments",0))==2
            and d.get("official_national_2026_roster_direct_verified") is False
            and len(d.get("12_site_archival_crosscheck",[]))==12
            and all(v.get("match") for v in d["12_site_archival_crosscheck"]))
    else:
        passed=(d.get("status")=="PASS_OFFICIAL_DIRECT"
            and int(d.get("official_records_with_name_and_code",0))>2750
            and int(d.get("six_digit_county_like_keys",0))>2600
            and d.get("archival_diff") is not None
            and d.get("official_12_site_checks") is not None
            and len(d["official_12_site_checks"])==12
            and any(a.get("usable_full_coverage") for a in attempts))
    result=("RES-2026-PROVISIONAL-ROSTER-" if MODE=="fallback" else "RES-2025-OFFICIAL-SOURCE-")+RUN
    previous=s["active_action"]
    if passed:
        status="DELTA_VERIFIED";engine="PASS"
        s["last_completed_action_id"]=ACTION
        s["closed_result_refs"].append(result)
        s["active_action"]={
          "action_id":"RET-CLIMATE-COUNTY-QA-001","question_id":"Q-CLIMATE-REPRESENTATIVENESS",
          "decision":"确定行政区划版本差异及县域气候点位的空间代表性，形成可核验县级广筛证据",
          "method":"从2025-12-31官方年版与历史边界/第三方县级代码作差集；以气候点位、海拔和县域微气候例外做质量分类；继续优先取得官方CMA1991-2020",
          "expected_evidence":"县级行政差集、时空源和微气候例外标志；具证据的有效县域广筛首批记录",
          "pass_criteria":"有实际年份、行政码、气候源、位置、质量与例外记录；缺失继续待核，未经用户批准不得硬淘汰",
          "fallback":"无法取得2025官方空间边界则冻结行政名字对照与气候点位，仅标待核；切换政府/学术可靠空间源",
          "timebox_end":"2026-11-08T15:26:00Z","status":"READY"}
        if MODE=="fallback":
            s["active_action"]["method"]="仅使用标注来源的2026-06临时县级底盘开展可复现县级气候覆盖试验；正式全国行政代码完整核验仍未解决"
            s["active_action"]["pass_criteria"]="有完整气候与县域空间/海拔、微气候例外证据后才计有效县级广筛；只列名称或未确认编码不计"
            s.setdefault("open_blockers",[]).append({"question_id":"Q-OFFICIAL-ADCODE",
                "status":"OPEN_2026_NATIONWIDE_OFFICIAL_RECONCILIATION",
                "reason":"Official MCA source DNS failed; mirror and Xinjiang government legal notices support only a provisional roster, not official national code certification"})
            s["phase"]="PROVISIONAL_COUNTY_CLIMATE_QA_OFFICIAL_GAP"
        else:
            s["phase"]="COUNTY_CLIMATE_EVIDENCE"
        s["consecutive_no_delta"]=0
    else:
        status="BLOCKED_WITH_EVIDENCE";engine="FAIL"
        s["consecutive_no_delta"]=int(s["consecutive_no_delta"])+1
        s["active_action"]["status"]="BLOCKED_WITH_EVIDENCE" if s["consecutive_no_delta"]<2 else "REQUIRES_DIFFERENT_METHOD"
        s["active_action"]["last_error"]=d.get("error") or ("official API unavailable / result partial; see evidence "+str(EVIDENCE))
        s["active_action"]["fallback"]="切换2025官方年版独立镜像交叉核验及其他官方省级材料，不能以镜像冒充官方直读；2轮无增量禁止继续同入口"
    if MODE=="fallback":
        narrative=("2025年全年镜像2845县级代码与2026年两项政府设立公告，构成有来源边界的2026-06临时2847县级计算底盘；全国官方代码逐项认证仍OPEN。"
          if passed else "临时底盘工程对账未通过，保留原始失败证据。")
    else:
        narrative=("直接读取民政部2025行政数据完成对账；仍需2026变更核查。"
          if passed else "官方直接取数未通过，完整错误已冻结，禁止无限同法重试。")
    line="\\n- "+result+": "+narrative+" 有效县级广筛仍为0。\\n"
    with CURRENT.open("a",encoding="utf-8") as fh:fh.write(line)
    s["current_state_ref"]["git_blob_sha"]=blob(CURRENT)
    s["updated_at"]=NOW();s["state_revision"]+=1
    s["last_verified_run"]={
      "run_id":RUN,"action_id":ACTION,"result_id":result,"execution_status":"EXECUTED",
      "engineering_status":engine,"research_delta_status":status,
      "research_closure_status":"OPEN","evidence_path":str(EVIDENCE),"evidence_sha256":sha(EVIDENCE),
      "status":"AWAITING_POSTCHECK"}
    s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK","verified_commit":None}
    write(STATE,s)
    start=json.loads(pathlib.Path("research_engine/retirement/output/official_precheck.json").read_text(encoding="utf-8"))
    append({"kind":"S0-S5","run_id":RUN,"action_id":ACTION,"start":start["start"],"end":NOW(),
        "source_revision":start["start_state_revision"],"source_commit":start["source_commit"],
        "command":("python research_engine/retirement/provisional_roster.py" if MODE=="fallback" else "python research_engine/retirement/official_recon_probe.py"),
        "evidence":str(EVIDENCE),"evidence_sha256":sha(EVIDENCE),
        "official_source_status":d["status"],"result_id":result,
        "execution_status":"EXECUTED","engineering_status":engine,
        "research_delta_status":status,"research_closure_status":"OPEN",
        "next_action_id":s["active_action"]["action_id"],"writeback":"PENDING_REMOTE_CHECK"})
    print(json.dumps({"run_id":RUN,"engineering":engine,"research_delta":status,
      "code_checks":d.get("official_code_verified",0),"county_screenings":0,
      "next_action":s["active_action"]["action_id"]},ensure_ascii=False))
def postcheck():
    s=getstate()
    if s["last_verified_run"]["run_id"]!=RUN:raise RuntimeError("RUN_ID_MISMATCH")
    remote=json.loads(subprocess.check_output(["git","show","origin/main:"+str(STATE)],text=True))
    if remote["state_revision"]!=s["state_revision"]:raise RuntimeError("REMOTE_STATE_REVISION_MISMATCH")
    if remote["last_verified_run"]["run_id"]!=RUN:raise RuntimeError("REMOTE_RESULT_MISMATCH")
    if remote["current_state_ref"]["git_blob_sha"]!=blob(CURRENT):raise RuntimeError("REMOTE_CURRENT_DRIFT")
    for path in [CURRENT,EVIDENCE,LOG]:
        subprocess.check_output(["git","show","origin/main:"+str(path)])
    s["writeback_verification"]={"status":"POSTCHECK_PASS","verified_commit":subprocess.check_output(["git","rev-parse","origin/main"],text=True).strip(),"verified_at":NOW()}
    s["last_verified_run"]["status"]="POSTCHECK_PASS"
    s["updated_at"]=NOW();s["state_revision"]+=1
    write(STATE,s)
    append({"kind":"S6_POSTCHECK","run_id":RUN,"action_id":ACTION,"at":NOW(),
            "postcheck":"PASS","state_revision":s["state_revision"],
            "checked_paths":[str(STATE),str(CURRENT),str(EVIDENCE),str(LOG)]})
    print("OFFICIAL_RECON_POSTCHECK_PASS",RUN)
if __name__=="__main__":
    try:{"precheck":precheck,"finalize":finalize,"postcheck":postcheck}[sys.argv[1]]()
    except Exception as exc:
        print("V1.6_OFFICIAL_GATE_FAIL",repr(exc),file=sys.stderr);sys.exit(2)
