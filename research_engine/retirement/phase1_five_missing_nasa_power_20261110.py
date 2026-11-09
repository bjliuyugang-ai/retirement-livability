#!/usr/bin/env python3
"""Focused 1991–2020 NASA POWER MERRA-2 grid reference for five unfilled locations.
No formal residential climate validation, no rating/exclusion changes.
Monthly T2M is degC; PRECTOTCORR is mm/day; annual precipitation sums daily means*days.
"""
import calendar,csv,datetime,json,pathlib,time,requests
ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"status";OUT.mkdir(parents=True,exist_ok=True)
SITES=[
 {"code":"460303","region":"海南·南沙区","site":"永暑礁/永暑岛固定点","lat":9.621,"lon":112.974,"source":"https://www.weather.com.cn/cityintro/101310219.shtml","note":"岛礁点仅代表指定固定点，不代表南沙区广域；模型海陆混合格点风险特别高"},
 {"code":"653229","region":"新疆·和安县","site":"红柳镇政府驻地/大红柳滩代理","lat":35.9794,"lon":79.1944,"source":"https://www.xinjiang.gov.cn/xinjiang/tzgg/202412/a0b3b3ac363546589618dd9d49cc7fd7.shtml","note":"县域2024年设立，行政区边界未匹配；坐标为镇级代理"},
 {"code":"653228","region":"新疆·和康县","site":"昆岭镇（原赛图拉镇）/三十里营房代理","lat":36.3521,"lon":78.0280,"source":"https://www.xzqh.org/show/china/2025/65/653228.html","note":"高海拔山地、0.5°格点代表性极弱；原12.5℃低证据参考与高山实体可能冲突"},
 {"code":"653132","region":"新疆·岑岭县","site":"新华镇镇中心代理","lat":36.39883,"lon":76.66264,"source":"https://www.xinjiang.gov.cn/xinjiang/tzgg/202603/285e5d25b8ad4eae8df6b0f0efe847f6.shtml","note":"新设县界未确定，镇中心非具体住宅"},
 {"code":"540581","region":"西藏·错那市","site":"麻麻门巴民族乡麻麻村（新驻地）代理","lat":27.87912,"lon":91.79295,"source":"https://www.tibetology.ac.cn/2022-04/06/content_41927570.htm","note":"绝不能以海拔约4380米的旧错那镇替代新驻地麻麻门巴民族乡；再分析海拔硬线"}
]
RESULT=[]
for s in SITES:
 url="https://power.larc.nasa.gov/api/temporal/monthly/point"
 args={"parameters":"T2M,PRECTOTCORR","community":"AG","longitude":s["lon"],"latitude":s["lat"],"start":"1991","end":"2020","format":"JSON"}
 data=None;error=""
 for attempt in range(3):
  try:
   response=requests.get(url,params=args,headers={"User-Agent":"RetirementLivabilityAcademic/1.0 (climate-research@users.noreply.github.com)"},timeout=95)
   response.raise_for_status();data=response.json()
   if data.get("messages") and not data.get("properties",{}).get("parameter"):raise ValueError(str(data["messages"])[:500])
   break
  except Exception as e:
   error=repr(e);time.sleep(2+attempt*2)
 record=dict(s)
 record.update({"dataset":"NASA POWER historical monthly MERRA-2 meteorological grid","statistical_period":"1991—2020","n_requested_months":360,"url":response.url if data is not None else url,"api_error":error if data is None else ""})
 if data:
  params=data.get("properties",{}).get("parameter",{})
  ts=params.get("T2M",{});ps=params.get("PRECTOTCORR",{})
  tmonth=[];pmonth=[];t_monthly_for_year={};p_monthly_for_year={}
  for y in range(1991,2021):
   for m in range(1,13):
    key=f"{y}{m:02d}";days=calendar.monthrange(y,m)[1]
    a=ts.get(key);b=ps.get(key)
    if isinstance(a,(float,int)) and -100<a<70:
     tmonth.append((float(a),days));t_monthly_for_year.setdefault(y,[]).append((float(a),days))
    if isinstance(b,(float,int)) and 0<=b<500:
     pmonth.append((float(b),days));p_monthly_for_year.setdefault(y,[]).append((float(b),days))
  record["valid_temp_months"]=len(tmonth);record["valid_precip_months"]=len(pmonth)
  tyears=[sum(v*d for v,d in t_monthly_for_year[y])/sum(d for _,d in t_monthly_for_year[y]) for y in range(1991,2021) if len(t_monthly_for_year.get(y,[]))==12]
  pyears=[sum(v*d for v,d in p_monthly_for_year[y]) for y in range(1991,2021) if len(p_monthly_for_year.get(y,[]))==12]
  record["complete_temp_years"]=len(tyears);record["complete_precip_years"]=len(pyears)
  record["grid_annual_mean_temp_c"]=round(sum(tyears)/len(tyears),2) if len(tyears)>=25 else ""
  record["grid_annual_precip_mm"]=round(sum(pyears)/len(pyears),1) if len(pyears)>=25 else ""
  record["geometry_lon_lat"]=data.get("geometry",{}).get("coordinates",[])
  record["data_sources"]=data.get("header",{}).get("sources",[])
  record["api_message"]="; ".join(str(x) for x in data.get("messages",[]))
  # Baseline conflict alert; never silently replace higher spatially resolved data.
  record["representativeness"]="COARSE_GLOBAL_GRID_REFERENCE_ONLY_NOT_SETTLEMENT_NORMAL"
  record["use_for_hard_exclusion"]="NO"
 RESULT.append(record)
 print(json.dumps({k:record.get(k) for k in ("region","grid_annual_mean_temp_c","grid_annual_precip_mm","valid_temp_months","valid_precip_months","api_error")},ensure_ascii=False),flush=True)
meta={"schema":"RETIREMENT_CLIMATE_FIVE_MISSING_NASA_POWER_MONTHLY_CROSSCHECK_20261110_V1",
 "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "data_source":"NASA POWER MERRA-2 monthly meteorology, historical 1991—2020",
 "method":"Only completed years with 12 monthly values; annual temperature is calendar-day-weighted mean; precipitation is sum of daily precipitation rates times days; 30-year average of annual totals.",
 "spatial_limit":"POWER meteorological grid is coarse (~0.5 x 0.625 degrees), subject to mountainous elevation/grid mismatch and reef land-sea mixing; not substitute for site normal or 1km climate raster.",
 "formal_hard_exclusions":0,"grade_overwrite":False,"sites":RESULT}
j=OUT/"phase1_236_five_missing_nasa_power_1991_2020_20261110.json"
j.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
headers=["code","region","site","lat","lon","grid_annual_mean_temp_c","grid_annual_precip_mm","valid_temp_months","valid_precip_months","complete_temp_years","complete_precip_years","representativeness","use_for_hard_exclusion","statistical_period","dataset","source","url","note","api_error","api_message"]
with (OUT/"phase1_236_five_missing_nasa_power_1991_2020_20261110.csv").open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=headers,extrasaction="ignore");writer.writeheader();writer.writerows(RESULT)
print("FINAL",json.dumps({"n_sites":len(RESULT),"temp_count":sum(isinstance(x.get("grid_annual_mean_temp_c"),float) for x in RESULT),"precip_count":sum(isinstance(x.get("grid_annual_precip_mm"),float) for x in RESULT)},ensure_ascii=False))
