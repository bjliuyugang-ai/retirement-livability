#!/usr/bin/env python3
"""Produce a national official-airport master and 110-area nearest-airport matrix.

Primary source: CAAC's 2025-12-31 licensed civil transport airport directory
(27 paginated pages; control total 270). All airports are geocoded with AMap.
For each study area, the two closest airports by straight-line distance are
routed; the shortest successful driving distance is selected. Government
office coordinates are proxies, not verified residential-centre coordinates.
"""
import csv, datetime as dt, html, json, math, os, pathlib, re, time, urllib.parse, urllib.request
from collections import Counter
from html.parser import HTMLParser

BASE="https://www.caac.gov.cn/GYMH/MHGK/MYJC/"
SOURCE=pathlib.Path("anju/results/pharmacy_1km/latest.json")
OUT=pathlib.Path("anju/results/airport_access_110")
AMAP_KEY=os.environ.get("AMAP_WEB_KEY","")
EXPECTED_AIRPORTS=270
MAX_REQUESTS=560
REQUESTS=0
HALT=""
UA="Anju-Second-Stage-Research/1.0 (official airport directory crosswalk)"

PROVINCES=set("北京 天津 河北 山西 内蒙古 辽宁 吉林 黑龙江 上海 江苏 浙江 安徽 福建 江西 山东 河南 湖北 湖南 广东 广西 海南 重庆 四川 贵州 云南 西藏 陕西 甘肃 青海 宁夏 新疆".split())
REGIONS=set(["华北地区","东北地区","华东地区","中南地区","西南地区","西北地区","新疆地区"])

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[];self.in_tr=False;self.in_cell=False
        self.row=[];self.cell=[]
    def handle_starttag(self,tag,attrs):
        t=tag.lower()
        if t=="tr":
            self.in_tr=True;self.row=[]
        elif t in ("td","th") and self.in_tr:
            self.in_cell=True;self.cell=[]
    def handle_data(self,data):
        if self.in_tr and self.in_cell:
            self.cell.append(data)
    def handle_endtag(self,tag):
        t=tag.lower()
        if t in ("td","th") and self.in_tr and self.in_cell:
            value=" ".join("".join(self.cell).split()).strip()
            self.row.append(value);self.cell=[];self.in_cell=False
        elif t=="tr" and self.in_tr:
            if self.in_cell:
                self.row.append(" ".join("".join(self.cell).split()).strip())
            if self.row:self.rows.append(self.row)
            self.row=[];self.cell=[];self.in_cell=False;self.in_tr=False

def get(url,timeout=25):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/json,*/*"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read(5_000_000)

def clean(s):
    return re.sub(r"\s+","",html.unescape(str(s or ""))).strip()

def parse_airports(page_no,raw):
    p=TableParser();p.feed(raw.decode("utf-8","replace"))
    found=[]
    for row in p.rows:
        cells=[clean(x) for x in row if clean(x)]
        if len(cells)>=3:
            for i in range(len(cells)-2):
                name,region,province=cells[i:i+3]
                if province in PROVINCES and region in REGIONS and "机场" in name and len(name)<=35:
                    found.append({"airport_name":name,"region":region,"province":province,"source_page":page_no})
                    break
    if found:return found
    # Fallback for a future CAAC page layout change.
    text=clean(re.sub(r"<[^>]+>"," ",raw.decode("utf-8","replace")))
    pat=r"([\u4e00-\u9fffA-Za-z0-9（）()·\-]{2,35}机场)(华北地区|东北地区|华东地区|中南地区|西南地区|西北地区|新疆地区)("+"|".join(sorted(PROVINCES,key=len,reverse=True))+r")"
    for m in re.finditer(pat,text):
        found.append({"airport_name":m.group(1),"region":m.group(2),"province":m.group(3),"source_page":page_no})
    return found

def caac_directory():
    rows=[]
    for page in range(27):
        suffix="" if page==0 else f"index_{page}.html"
        raw=get(BASE+suffix)
        got=parse_airports(page,raw)
        if len(got)<5:
            raise RuntimeError(f"CAAC_PAGE_PARSE_LOW page={page} parsed={len(got)}")
        rows.extend(got)
        time.sleep(0.15)
    unique={}
    for x in rows:
        unique[(x["airport_name"],x["province"])]=x
    result=list(unique.values())
    if len(result)!=EXPECTED_AIRPORTS:
        raise RuntimeError(f"CAAC_CONTROL_TOTAL_MISMATCH expected={EXPECTED_AIRPORTS} parsed={len(result)} raw_rows={len(rows)}")
    return sorted(result,key=lambda x:(x["province"],x["airport_name"]))

def amap_json(path,params):
    global REQUESTS,HALT
    if REQUESTS>=MAX_REQUESTS:
        HALT="AMAP_REQUEST_CAP"
        return None,"AMAP_REQUEST_CAP"
    if not AMAP_KEY:
        HALT="AMAP_KEY_MISSING"
        return None,"AMAP_KEY_MISSING"
    q=dict(params);q["key"]=AMAP_KEY;q["output"]="JSON"
    REQUESTS+=1
    try:
        raw=get("https://restapi.amap.com"+path+"?"+urllib.parse.urlencode(q),timeout=25)
        d=json.loads(raw.decode("utf-8","replace"))
        if str(d.get("status"))!="1":
            return None,"AMAP_"+str(d.get("infocode","BAD_RESPONSE"))
        return d,None
    except Exception as e:
        return None,"AMAP_"+type(e).__name__
    finally:
        time.sleep(0.28)

def geocode_airport(a):
    # Try exact CAAC name with province first, then exact POI text search.
    q=f'{a["province"]}{a["airport_name"]}'
    d,err=amap_json("/v3/geocode/geo",{"address":q,"city":a["province"]})
    if d and d.get("geocodes"):
        g=d["geocodes"][0]
        loc=str(g.get("location") or "")
        if re.fullmatch(r"\d{1,3}\.\d+,\d{1,2}\.\d+",loc):
            return {**a,"location_gcj02":loc,"geocode_source":"AMap v3 geocode",
                    "formatted_address":g.get("formatted_address",""),
                    "geocode_level":g.get("level",""),"adcode":g.get("adcode",""),
                    "geocode_status":"OK"}
    d2,err2=amap_json("/v5/place/text",{"keywords":a["airport_name"],"city":a["province"],
                  "page_size":"5","page_num":"1","show_fields":"business"})
    if d2:
        pois=d2.get("pois") or []
        for p in pois:
            name=clean(p.get("name"))
            if name==clean(a["airport_name"]) or (clean(a["airport_name"]) in name and "机场" in name):
                loc=str(p.get("location") or "")
                if re.fullmatch(r"\d{1,3}\.\d+,\d{1,2}\.\d+",loc):
                    return {**a,"location_gcj02":loc,"geocode_source":"AMap v5 exact POI",
                            "formatted_address":p.get("address",""),
                            "geocode_level":"POI","adcode":p.get("adcode",""),
                            "geocode_status":"OK"}
    return {**a,"location_gcj02":"","geocode_source":"","formatted_address":"",
            "geocode_level":"","adcode":"","geocode_status":err or err2 or "NO_MATCH"}

def haversine(a,b):
    lon1,lat1=map(float,a.split(","));lon2,lat2=map(float,b.split(","))
    r=6371000
    p1,p2=math.radians(lat1),math.radians(lat2)
    dp=math.radians(lat2-lat1);dl=math.radians(lon2-lon1)
    z=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(z))

def route(origin,dest):
    d,err=amap_json("/v5/direction/driving",{"origin":origin,"destination":dest,
                    "strategy":"32","show_fields":"cost"})
    if err:return None,err
    paths=(d.get("route") or {}).get("paths") or []
    if not paths:return None,"NO_ROUTE"
    valid=[]
    for p in paths:
        cost=p.get("cost") or {}
        try:dist=int(float(p.get("distance")))
        except Exception:continue
        try:secs=int(float(cost.get("duration")))
        except Exception:secs=None
        valid.append({"distance_m":dist,"duration_s":secs})
    if not valid:return None,"ROUTE_FIELDS_MISSING"
    return min(valid,key=lambda x:x["distance_m"]),None

def main():
    global HALT
    if not AMAP_KEY:raise SystemExit("AMAP_KEY_MISSING")
    if not SOURCE.is_file():raise SystemExit("MISSING_110_AREA_GEOCODE_SOURCE")
    src=json.loads(SOURCE.read_text(encoding="utf-8"))
    areas=src.get("rows",[])
    if len(areas)!=110 or len({x.get("area") for x in areas})!=110:
        raise SystemExit("AREA_SOURCE_NOT_110_UNIQUE")
    if not all(x.get("center_gcj02") for x in areas):
        raise SystemExit("AREA_SOURCE_HAS_MISSING_COORDINATES")

    airports=caac_directory()
    master=[geocode_airport(a) for a in airports]
    geocoded=[a for a in master if a["geocode_status"]=="OK"]
    if len(geocoded)<250:
        raise RuntimeError(f"AIRPORT_GEOCODE_COVERAGE_LOW {len(geocoded)}/{len(master)}")
    results=[]
    for area in areas:
        origin=area["center_gcj02"]
        candidates=sorted([(haversine(origin,a["location_gcj02"]),a) for a in geocoded],
                          key=lambda x:x[0])[:2]
        row={"area":area["area"],"reference_anchor":area.get("geocode_address",""),
             "reference_point_gcj02":origin,"airport_master_total":len(airports),
             "airport_master_geocoded":len(geocoded),"candidate_count_routed":0,
             "nearest_airport_name":"","nearest_airport_province":"",
             "straight_distance_m":"","driving_distance_m":"","driving_duration_s":"",
             "route_candidates":[],"regular_scheduled_flight_status":"NOT_INDIVIDUALLY_VERIFIED",
             "status":"NOT_ATTEMPTED",
             "metric_note":"Nearest CAAC-licensed civil transport airport by shortest AMap driving distance among the two closest geocoded airports; CAAC directory baseline 2025-12-31; government-office reference point proxy."}
        routes=[]
        for straight,a in candidates:
            if HALT:break
            row["candidate_count_routed"]+=1
            r,err=route(origin,a["location_gcj02"])
            rec={"airport_name":a["airport_name"],"province":a["province"],
                 "straight_distance_m":int(straight),"driving_distance_m":r["distance_m"] if r else "",
                 "driving_duration_s":r["duration_s"] if r else "","route_status":err or "OK"}
            routes.append(rec)
        row["route_candidates"]=routes
        valid=[x for x in routes if x["driving_distance_m"]!=""]
        if valid:
            best=min(valid,key=lambda x:x["driving_distance_m"])
            row.update({"nearest_airport_name":best["airport_name"],
                        "nearest_airport_province":best["province"],
                        "straight_distance_m":best["straight_distance_m"],
                        "driving_distance_m":best["driving_distance_m"],
                        "driving_duration_s":best["driving_duration_s"],
                        "status":"ROUTE_OK_TWO_CANDIDATES" if len(valid)==2 else "ROUTE_OK_ONE_CANDIDATE"})
            if len(geocoded)!=len(airports):
                row["status"]+="_AIRPORT_MASTER_GEOCODE_INCOMPLETE"
        elif len(geocoded)<len(airports):
            row["status"]="UNKNOWN_AIRPORT_MASTER_GEOCODE_INCOMPLETE"
        else:
            row["status"]="UNKNOWN_ROUTE_FAILED"
        results.append(row)

    OUT.mkdir(parents=True,exist_ok=True)
    status=Counter(x["status"] for x in results)
    doc={"schema":"anju_110_airport_access_caac_2025_v1",
         "generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
         "source":"CAAC official transport airport directory pages, as of 2025-12-31",
         "source_urls":[BASE, "https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202602/t20260226_230119.html"],
         "official_control_total":270,"official_regular_flight_control_total":266,
         "areas_total":110,"airport_master_total":len(airports),
         "airport_master_geocoded":len(geocoded),
         "amap_requests":REQUESTS,"amap_request_cap":MAX_REQUESTS,"halt_reason":HALT,
         "status_counts":dict(status),
         "limitations":[
           "CAAC directory lists 270 licensed transport airports; CAAC 2025 production bulletin reports 266 airports with scheduled flights but does not identify the four non-scheduled airports in the directory page",
           "Therefore nearest-airport distance is to a CAAC-licensed civil transport airport; scheduled-flight operation is not individually verified",
           "Only two closest geocoded airports by straight-line distance are road-routed; a third candidate could have a shorter road route in unusual terrain",
           "Each area uses county/district government office coordinates as a proxy, not the centre of residential neighbourhoods"
         ],
         "airport_master":master,"rows":results}
    (OUT/"airport_master_270.json").write_text(json.dumps({"total":len(master),"rows":master},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"latest.json").write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    fields=sorted(set().union(*(x.keys() for x in results)))
    with (OUT/"latest.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for x in results:
            y=dict(x);y["route_candidates"]=json.dumps(y["route_candidates"],ensure_ascii=False)
            w.writerow(y)
    print(json.dumps({"areas":110,"airport_master":len(airports),"geocoded":len(geocoded),
       "unmatched_airports":[x["airport_name"] for x in master if x["geocode_status"]!="OK"],
       "statuses":dict(status),"amap_requests":REQUESTS,"halt":HALT},ensure_ascii=False,indent=2))

if __name__=="__main__":main()
