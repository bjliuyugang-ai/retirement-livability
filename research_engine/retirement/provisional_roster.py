#!/usr/bin/env python3
"""Build an EXPLORATORY 2026-06 county roster from an attributed 2025 mirror plus
two official regional establishment notices. Not an officially verified 2026 national master.
"""
import csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement")
EVID=ROOT/"evidence";OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
mirror=EVID/"mirror_2025_adcodes.txt"
diff=EVID/"mirror_2025_vs_legacy_diff.json"
updates=EVID/"provisional_2026_admin_updates.json"
links=pathlib.Path("retirement-climate-pilot/status/latest-adcode-probe.json")
res={"run_type":"NONFORMAL_WORKING_ROSTER","generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
     "official_national_2026_roster_direct_verified":False,"valid_county_screenings":0,
     "official_2026_county_code_verifications":0}
try:
    text=mirror.read_text(encoding="utf-8")
    raw=[s.strip().split(maxsplit=1) for s in text.splitlines() if s.strip()]
    if not all(len(r)==2 and len(r[0])==6 and r[0].isdigit() for r in raw):raise ValueError("Invalid mirror code rows")
    counts={s[0]:s[1] for s in raw}
    if len(counts)!=3212:raise ValueError("Unexpected 2025 code count")
    counties={k:v for k,v in counts.items() if k[-2:]!="00"}
    if len(counties)!=2845:raise ValueError("Unexpected 2025 county count")
    delta=json.loads(diff.read_text(encoding="utf-8"))
    changes=json.loads(updates.read_text(encoding="utf-8"))
    sample=json.loads(links.read_text(encoding="utf-8"))["candidate_links"]
    checks=[{"site":s["site"],"code":s["candidate_code"],
             "2025_name":counties.get(s["candidate_code"]),
             "match":counties.get(s["candidate_code"])==s["archival_county_chinese"]} for s in sample]
    if len(checks)!=12 or not all(x["match"] for x in checks):raise ValueError("12-site code/name sample does not align")
    if delta["counts"]["mirror_2025_counties"]!=len(counties) or len(delta["differences"])!=143:raise ValueError("Source diff count disagreement")
    rows=[{"code":k,"name":v,"source_class":"THIRD_PARTY_2025_MIRROR","asof":"2025-12-31",
           "legal_update_verified":False,"official_current_code_verified":False,"county_climate_status":"NOT_SCREENED"} for k,v in counties.items()]
    for change in changes["changes"]:
        c=change["candidate_code"]
        if c in counties:raise ValueError("Duplicate 2026 candidate county: "+c)
        if change["legal_establishment"]!="GOVERNMENT_NOTICE_VERIFIED":raise ValueError("Unverified 2026 legal change")
        rows.append({"code":c,"name":change["name"],"source_class":"2026_LEGAL_ANNOUNCEMENT_PLUS_SECONDARY_CODE",
         "asof":change["decision_date"],"legal_update_verified":True,"official_current_code_verified":False,
         "county_climate_status":"NOT_SCREENED"})
    rows.sort(key=lambda x:x["code"])
    if len(rows)!=2847 or len({x["code"] for x in rows})!=2847:raise ValueError("Provisional 2026 roster count mismatch")
    csvpath=OUT/"provisional_counties_2026_06.csv"
    with csvpath.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=["code","name","source_class","asof","legal_update_verified","official_current_code_verified","county_climate_status"])
        w.writeheader();w.writerows(rows)
    res.update({"status":"PASS_PROVISIONAL_ROSTER_BUILD","mirror_2025_counties":2845,
       "2026_verified_legal_establishments":2,"provisional_2026_midyear_count":2847,
       "2025_mirror_source_blob_sha":delta["source_mirror"]["git_blob_sha"],
       "2025_legacy_diff":delta["counts"],"12_site_archival_crosscheck":checks,
       "official_6digit_codes_2026_new_direct_verified":0,
       "csv_sha256":hashlib.sha256(csvpath.read_bytes()).hexdigest(),
       "source_year_notes":"2025 full mirror; two 2026 province government notices with candidate codes still secondary. 2026-07-Nov official change scan pending.",
       "limitations":["Not a source-verifiable complete 2026 official county denominator.",
                      "No official direct code verification for 2026 additions.",
                      "No climate station coverage, altitude QA, or microclimate exceptions evaluated.",
                      "No valid screening, no grades, no Library Master changes."]})
except Exception as e:
    res.update({"status":"BLOCKED_WITH_EVIDENCE","error":repr(e)})
(OUT/"provisional_roster_summary.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in res.items() if k!="12_site_archival_crosscheck"},ensure_ascii=False))
if res["status"]!="PASS_PROVISIONAL_ROSTER_BUILD":raise SystemExit(2)
