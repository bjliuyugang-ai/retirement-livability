# 退休宜居城市｜第一阶段 Current State（技术攻关执行指针）

更新时间：2026-11-06T15:36:06.356Z
权威研究基线：个人Library /安居/退休宜居城市/退休宜居城市_长期研究基线_Master_Latest.docx（V1.2）及2026-11-05冻结补充。
权威评级/历史：同目录Excel Master与增量快照。此文件不替代Library，也不覆盖正式Master。

## 已证实（限定边界）
- RES-CLIMATE-12POINT-20261106：Open-Meteo ERA5 1991—2020，12个探索性坐标点位，共131,496个逐日记录、144条逐月统计，原始运行摘要在 retirement-climate-pilot/status/latest-summary.json。该结果不是CMA站点常年值，不具备县级广筛/正式评级资格。
- 行政代码：Library中的第三方历史开源县级代码2,978条，仅供工程底盘；未核2026官方口径，不能等同最新官方县级单元数量。
- 县级有效广筛：0（截至本次初始化）。正式A/B/C/D不变。

## 未决核心问题
- Q-COUNTY-SPATIAL-MATCH：县级边界能否实际读入并将12个探索性坐标点匹配到有证据的历史边界，明确失败、歧义、数据年代。
- Q-OFFICIAL-ADCODE：现行官方县级代码与边界对账，消除历史功能区和行政调整冲突。
- Q-CLIMATE-REPRESENTATIVENESS：县域内高差、河谷、山脉、沿海微气候代表性，形成有效广筛证据。
- Q-CMA-NORMALS：优先官方1991—2020常年值或可核实替代的气温、日照、湿度原始数据。

## 当前唯一攻关动作
RET-SPATIAL-001：执行2017口径geoBoundaries历史县级边界空间匹配真实试验；这是空间工程能力验证，不计正式有效县级广筛。若边界服务阻塞，记录真实错误，按根因切换合规来源或获取路径，禁止直接判县域D。

## 无人值守权限及完成底线
- 无人值守不得覆盖Library Master，必要时仅追加唯一增量并回读。
- RUN_STATE/RUN_LOG 位于 tasks/6aead9a989808191ad42f80fd4e32bf1/phase1/，只有此处是该任务的执行指针。
- 工程PASS与研究DELTA分判；不因GitHub Actions completed宣称研究完成。
- S0—S6与回归门禁必须经代码验证，部署前不得宣称已经正式上线。

- RES-SPATIAL-ENGINEERING-42244926780: 2017历史边界点面匹配真实试验；PASS：点位匹配工程可运行，不代表2026行政对账或县级有效广筛。

- RES-ARCHIVAL-ADCODE-42245603994: 历史开源行政代码与历史县界12点对齐；工程PASS，仅代表候选编码，不等于2026官方对账，也不计有效县级广筛。

- RES-2025-OFFICIAL-SOURCE-42248287808: 国家地名信息库直接取数尚未达到正式源验收条件；记录服务端返回/错误并按升级规则处置。 有效县级广筛仍为0。

- RES-2026-PROVISIONAL-ROSTER-42249396217: 2025年全年镜像2845县级代码与2026年两项政府设立公告，构成有来源边界的2026-06临时2847县级计算底盘；全国官方代码逐项认证仍OPEN。 有效县级广筛仍为0。

- RES-SECONDARY-GEOMETRY-CODE-QA-42250420760: 独立编码县界空间验证受阻；错误和证据已登记。
- 当前唯一下一动作：RET-CLIMATE-COUNTY-QA-001；官方全国代码完整认证和县内微气候仍OPEN。

- RES-SECONDARY-GEOMETRY-CODE-QA-42251289106: 独立编码县界12点空间匹配验证通过；112个面要素仅用于数据工程，不是县级有效广筛。
- 当前唯一下一动作：RET-COUNTY-MICROCLIMATE-QA-001；官方全国代码完整认证和县内微气候仍OPEN。

- RES-DEM-ERA5-MOISTURE-EXPLORATORY-42251953046: 12县级点位完成36个县内Copernicus DEM海拔采样；ERA5露点/湿度真实读取数和地形例外标记详见证据；属于探索性数据工程，正式广筛0。

- RES-SPATIAL-MULTIGRID-002-42315459712: 多格点气候差异实测被阻塞，原始错误见证据；县级有效广筛仍为0。

- RES-SPATIAL-MULTIGRID-002-42317042892: 4个高海拔差异县域完成12格点1991-2020 ERA5气候差异实测，保留微气候例外，不能据此完成正式县级广筛。

- RES-STAGE3-11POINT-FIRSTBATCH-42317771144: 用户明确授权从11个已有ERA5点位直接进入第三关方法验证。首次4个县域11点初筛已生成逐点偏好命中与县域风险分层（研究增量）；现行行政身份、CMA站点、住宅海拔、空气/水/污染/灾害未关闭，正式有效县级广筛仍为0。旧RET-CMA-ERA5-CROSSCHECK-003标记DEFERRED而非PASS。详见 research_engine/retirement/status/latest-first-batch-prescreen.json。

- RES-STAGE3-ENVIRONMENT-EVIDENCE-20261107: 按用户批准的第三关初筛（4县域11点），继续核验第一优先级蒙自/攀枝花东区的空气、水源、工业整改和地质灾害公示。已取得2025年蒙自PM2.5官方来源及官方公报内优良率98.8%/99.2%冲突、2025年单年气候；攀枝花2025年新闻发布会城市级空气数据及2026年工业整改/地灾公告。住宅级污染、末梢水、灾害坐标及1991—2020气象站证据仍待核，正式县级有效广筛0。机器证据：research_engine/retirement/evidence/stage3_firstbatch_public_environment_evidence_20261107.json；状态为PARTIAL，不代表完成当前唯一动作。

- RES-STAGE3-2026-MENGZI-TAP-AND-ANCHOR-20261107-002: 第三关第一批居住片区证据突破：2026年红河州卫健委Q1/Q3官方末梢水公报，共8个实采点、16条监测记录，已报告指标均符合各自公告限值；其中柒彩滇南·第一城及四季花城各有两季记录，均非楼栋完整106项确认。攀枝花东区炳草岗望江街社区作为现有居住型社区锚点；水务集团页面披露炳草岗水厂服务片区，但“水质供水”页面为污水排放数据，禁止误用为自来水检测。三处都缺完整住宅坐标/住宅海拔、独立气候站、空气分站、污染点源、地灾GIS叠加，不改变Master暂定等级，正式有效县级广筛0。证据：research_engine/retirement/evidence/stage3_mengzi_2026_tapwater_16_site_observations_v1.json、research_engine/retirement/status/stage3_firstbatch_residential_anchor_audit_v1.json。

- RES-CASCADE-R1R5-4COUNTY-AND-R0-2847-20261107: 用户确认实施逐参数漏斗法（R0底盘、R1冬夏气温、R2日照湿度、R3真实住宅海拔、R4空气污染、R5饮用水/灾害），关键已核实且不可有效规避者仅按批准规则提前退出，缺失/偏好不合均暂留下一轮。已完成4个县域11点R1—R5工程试运行（全部暂留，0确证淘汰，缺口72条），以及2847条历史/临时县级R0在册（全部未扫描，非官方2026完整认证）。已追加可回溯退出轮次、证据及重新入池条件机制。此前RET-STAGE3-EVIDENCE-GAPS-002因用户新工作方法暂缓而非完成，环境数据可复用；下一唯一动作为RET-CASCADE-NATIONAL-R1-001，使用真实气温证据开展逐片参数广筛。正式县级有效广筛仍0；Library Master和现有20片区暂定等级未改。权威执行补充：research_assets/retirement/STAGED_PARAMETER_CASCADE_V1.0_20261107.md。证据：research_engine/retirement/status/staged_parameter_cascade_v1.json；research_engine/retirement/status/national_cascade_r0_summary.json。

- RES-NATIONAL-R1-12-REAL-ERA5-COUNTY-POINTS-42320769375: 全国R1首次真实数据批处理通过：沿用GitHub Actions历史归档12点1991—2020 ERA5逐日气温记录，匹配12个独立历史县级候选编码（仅单点、非住宅），形成冬季、6—9月夏季和≥35℃热天证据；总2847临时县级，12个R1有探索性点证据、2835个R1未扫描、确证退出0、继续2847、正式有效县级广筛0。首批R2交接输入可继续但R1未扫描必须保留未知，不冒充R1完成。证据：research_engine/retirement/status/national_r1_first_real_batch_evidence.json，县级全量增量台账：research_engine/retirement/status/national_r1_first_real_batch.csv。

- RES-NATIONAL-R1-DISTRIBUTED-EXPAND-42321222770: 本轮全国R1从12个已取数历史县级点位扩展到22，新增10个真实1991—2020 ERA5温度取数点，历史县界/2025临时代码精确拼音关联、跨7省级代码前缀。另2825个县级R1未扫描（含20个接口失败/验证失败），确证淘汰0、下轮继续2847、正式有效县级广筛0。各结果严格记为点位/2017历史县界探索性，不作2026官方或居住片区证实。已批准递进法，唯一下一动作转R2，不阻塞于R1缺失。证据：research_engine/retirement/status/national_r1_expanded_summary.json，全量CSV：research_engine/retirement/status/national_r1_expanded.csv。

- RES-NATIONAL-R2-12-SUNRAIN-HUMIDITY-ERA5-42321544843: R2已按用户漏斗要求实际衔接：全国2847个R1继续地区全部进入R2，重用12个已缓存1991—2020 ERA5逐日原始点位获得年日照、冬季日照、年降水和连续阴雨证据，其中11点位已有湿度/露点独立字段；R2真实点位12、R2尚未扫描2835、R2确证淘汰0、进入R3共2847，正式有效县级广筛0。R1未扫描与已有不足证据保留待核。证据：research_engine/retirement/status/national_r2_first_real_batch_evidence.json，全国台账：research_engine/retirement/status/national_r2_first_real_batch.csv。

- RES-NATIONAL-R3-12COUNTY-36DEM-SAMPLES-42321725405: 按逐参数漏斗R3真实运行：全国2847个保留县级候选输入；12个历史编码县域关联36个Copernicus DEM GLO90真实采样点，记录原点/县内最低最高/跨度与低海拔潜在例外，2835个R3未扫描、确证淘汰0、继续2847。没有任何住宅精确定位和2026官方现行县界确认，因此正式有效县级广筛0。依据：research_engine/retirement/status/national_r3_first_real_batch_evidence.json；全量：research_engine/retirement/status/national_r3_first_real_batch.csv。

- RES-NATIONAL-R4-PARTIAL-SOURCE-ANCHORED-42321931812: 全国逐参数漏斗R4已执行：2847候选继续，真实有据的区域/命名监测点县区2个，2845个此参数未扫描，确证淘汰0、进入下一轮2847、正式有效县级广筛0。R4依据2025年蒙自PM2.5、攀枝花城市空气和工业整改等公开来源，但均不是住宅暴露。R5依据2026年蒙自16条官方末梢水公开采样，不能代表具体楼栋水质及地灾安全。 证据：research_engine/retirement/status/national_r4_city_context_evidence.json；全量县级台账：research_engine/retirement/status/national_r4_city_context_batch.csv。

- RES-NATIONAL-R5-PARTIAL-SOURCE-ANCHORED-42321981720: 全国逐参数漏斗R5已执行：2847候选继续，真实有据的区域/命名监测点县区1个，2846个此参数未扫描，确证淘汰0、进入下一轮2847、正式有效县级广筛0。R5依据2026年蒙自16条官方末梢水公开采样，不能代表具体楼栋完整水质标准、地灾/洪涝未核。 证据：research_engine/retirement/status/national_r5_tap_water_evidence.json；全量县级台账：research_engine/retirement/status/national_r5_tap_water_batch.csv。

- RES-NATIONAL-2847-FIVE-ROUND-COVERAGE-GAP-AUDIT-42322194367: 全国逐参数R1—R5执行与缺失总审计已完成（不是全国正式有效广筛验收）：R0临时在册2847县级候选，R1真实ERA5点位22、R2真实日照雨量点位12、R3真实DEM多点县域12、R4仅区域空气/污染来源2、R5仅官方命名末梢水观测县域1；总计仅22候选具有至少一种参数真实探索证据，2825完全没有任何参数，20个新取数点因HTTP429失败。确证淘汰0、继续2847、正式有效县级广筛0。已保留全部缺口、失败、按省份覆盖、复活条件和历史档案。任务转为跨省真实数据覆盖攻坚，不在少数区域反复补细节。完整：research_engine/retirement/status/national_cascade_all_2847_audit.csv；摘要：research_engine/retirement/status/national_cascade_gap_coverage_audit.json；按省份：research_engine/retirement/status/national_cascade_province_coverage.csv。

- RES-METEOSTAT-CN-70-STATION-NORMALS-7-ERA5-CROSSCHECK-20261107: 全国R1数据源集中攻坚取得真实观测数据突破：Meteostat bulk 1991—2020已下载152,559,044B月度Parquet及32,804,864B站点SQLite，识别中国CN站257，其中70站满足各月≥20年且合计≥300个月的Tmax/Tmin观测类来源记录（GHCND/CLIMAT/ISD/METAR；未自动视为CMA正式站常年值）。已有42个历史县区点位中10处有近距高覆盖站点候选，其中7组与ERA5冬季日最高温差绝对值均<2°C（平均绝对误差0.882°C、最大1.816°C）。NASA区域接口无视指定1991—2020返回2001—2025；NASA点位接口自定义最高/最低温与同年度逐日平均差异>2°C，30份原始数据保留但全部指标隔离，新增20点不计有效R1。当前真实ERA5点22，正式县级有效广筛0，临时2847县级底盘官方2026对账仍OPEN。下一动作以70站真实数据的历史县界/现行代码空间关联来扩大有效参数证据，缺失仍暂留。资料：research_engine/retirement/status/meteostat_CN_1991_2020_station_candidate_normals.json，对照：research_engine/retirement/evidence/meteostat_ERA5_independent_7site_calibration_20261107.json，隔离：research_engine/retirement/status/national_R1_NASA_custom_QUARANTINE_evidence.json。

- RES-CN-70STATIONS-69CODE-65NEW_R1-20261107: 集中攻关唯一动作RET-CASCADE-NATIONAL-STATION-COUNTY-QA-003真实通过：运行42325609706下载第三方整理、宣称来源天地图的县界GeoJSON 11.8MB，2891个唯一6位adcode县级要素；把70个1991—2020观测来源长站点全部唯一落入这套县界，与2025第三方代码名录及2017历史县界关联逐一交叉检查。69个站点代码/名称/位置无明显冲突，1个大连气象站54662存在2017甘井子(210211)与带码地图中山区(210202)冲突已HOLD。69站代表69候选县级代码，其中65为此前R1未扫描，现新增65个站点气温月度部分证据；全国2847候选R1点位探索证据覆盖22→87、未扫描2760、R1-R5确证淘汰0、正式有效县级筛选0。第三方县界年份及2026官方代码均未认证，气象站并不代表住宅地块；NASA不合口径数据继续隔离。证据：research_engine/retirement/status/meteostat_70_station_coded_county_spatial_QA.json；70站追溯：research_engine/retirement/status/meteostat_70_station_coded_county_spatial_QA.csv；全国台账：research_engine/retirement/status/national_R1_meteostat_coded_county_candidate_overlay_2847.csv。下一阶段复用Meteostat同一月度原始站点资料扩大R2降雨日照，严格源字段和覆盖门禁，不直接作正式评级。

- RES-CN-69-R2-STATIONS-61NEW_PARTIAL-20261107: 全国R2气候参数有真实新增：GitHub Actions 42325955761成功复用Meteostat月度Parquet原始SHA7f5f37abaf67e57cbaeacefa20fae58c202a53d4d7250b1d2044dc7d98b5d68c，对69个可信临时县域代码站点分别审计1991—2020降水与日照source。各参数独立要求≥300有观测来源月、各日历月份≥20月；64站降雨符合，33站日照符合，61个此前R2未扫描县区取得至少一个参数真实点证据。R2探索性部分证据县域12→73，R2未扫描2774；R1 87保持不变，所有2847候选继续，无未经核准淘汰和正式评级。降水mm月累计、日照minutes月累计；月度资料无法说明极端连续阴雨、住宅水质或住宅局地气候。证据：research_engine/retirement/status/national_R2_meteostat_station_source_evidence.json；R2全国台账：research_engine/retirement/status/national_R2_meteostat_station_source_2847.csv。下一唯一动作为2025/2026官方县级代码和边界真实性核对，之后才能判断是否具备合法的行政单元第一阶段临时筛选资格。

- RES-2025-2845_PLUS2026TWO-2838_GEOCODE_MATCH_7MISSING-20261107: GitHub 42326645079真实运行完成：2025年末历史编纂码2845个县级＋2026新疆合法新设岑岭县653132、草湖市659013两个附加候选＝R0共2847。第三方GeoJSON 2891个独立带码要素与2025县级代码/名称一致2838个，7个2025县级缺几何(460302,460303,500157,540481,540581,653228,653229)；地图多53条拆分39台港澳底盘外、7非普通县级、2重庆已撤销、4旧别名待核、1特殊管理区。69气象站县码均与2025历史码相同。民政部官方dmfw接口真实DNS失败，最新2026全量官方码仍未认证。R1部分证据87、R2部分证据73，正式有效县级广筛0。明细 research_engine/retirement/status/national_2025_roster_vs_2891_coded_geometry_evidence.json；全国差异 research_engine/retirement/status/national_2025_roster_vs_2891_coded_geometry_diff.csv；分类 research_engine/retirement/evidence/national_county_geometry_diff_53_classified_20261107.json；官方访问障碍 research_engine/retirement/status/mca_official_api_real_access_QA.json。下轮实际核对并修补7+2个县区现行几何，不能因地图缺失淘汰候选。

- RES-NINE-COUNTY-DATAV-STRICT_CODE_NAME_0_VALID-20261107: 7个2025历史县级缺地图+2个2026新设县(共9)逐项真实HTTP检验完成，严谨V2 run42327187015通过：DataV单县请求西沙区460302虽HTTP200，原始GeoJSON却给出了同code但名称“南沙区”和南部海域形状，故代码/名称/坐标不一致，已拒绝；其余8个县级代码单独HTTP404，上级市/省full.json虽HTTP200却无对应代码要素。有效恢复2026可追溯带码县界0个，9个当前缺地图均保留待核，正式有效县级广筛仍0。上次仅以代码匹配得出1/9的V1结果已由严格V2替代，不能宣称恢复；该错误已登记以防复用。国家地名信息库接口DNS受阻依然OPEN，不在缺地图9县空耗旧路径。下一步转向扩大真实气候参数覆盖，优先复用有实测源的1991—2020原始站点或通过严格日值验收的替代气候网格源；原87个R1、73个R2点位保留，未扫描仍2760/2774。证据 research_engine/retirement/status/nine_missing_county_geoatlas_actual_requests.json。

- RES-CN226-GIS-SHORT_HISTORY_127_NEW_R1-20261107: 按V1.6国家广筛唯一动作真实运行GitHub Actions 42337163881，复用1991—2020年范围内226个有来源审核的中国气象站月度温度观测档案，2017历史县界与第三方2025六位代码GeoJSON双GIS点面匹配。原70长历史站结果完全复现：69通过+1冲突；额外≥180月、每个日历月≥10年但不满足≥300/20年条件的短历史站138个，其中132通过双图空间质量，覆盖132县级候选，127个此前无R1任何气温数据。R1分层统计：已较长基期或ERA5候选87县不变，新短历史真实观测初证127县，合计214县具某类R1数据，另2633完全无气温实证。132站不算合格1991—2020气候常年值，不用于排除或正式A/B/C/D；GIS冲突3站、名称不匹配1站等独立登记、保留待核。R2原部分参数证据73县不变、正式有效广筛0，全国2847保留。证据 research_engine/retirement/status/meteostat_CN_226_R1_tiered_expansion_evidence.json；站点逐行 research_engine/retirement/status/meteostat_CN_226_station_spatial_period_quality.csv；2847候选新增质量分层台账 research_engine/retirement/status/national_R1_226_obs_station_quality_tiers_2847.csv。下一动作在同批132站复用真实Meteostat月度原始源，单项扩展R2降水/日照初证；必须同样冻结长历史R2的73县，不以短史冒充正规常年值。

- RES-CN132-R2-126_NEW_SHORT_OBS_COUNTIES-20261107: V1.6当前唯一动作已在GitHub Actions run42337518958真实计算并独立SHA验收。复用最初已下载Meteostat 1991—2020月度Parquet(与旧SHA相同)，针对132个双GIS通过的短历史站，逐参数剔除补全模型/未知来源，降雨≥180月各历月≥10年站点130、日照站点10，出现牙克石市150782两个站点时单独保留两份记录并选择质量最高的主站，不算重复县域。130站具至少一个R2参数，覆盖129个临时县码，其中126个此前没有R2数据。R2质量分层：旧较长来源/ERA5部分证据县73保持不变，新增短史观测县126，累计有任一R2观测点位证据县199，2648无R2气候证据。R1原87+短史127=214县保持。短历史资料只作发现与缺口跟踪，不满足完整30年正式基期、不得代替正式A/B/C/D、不得排除，无全量2026官方县界认证。证据 research_engine/retirement/status/meteostat_CN132_interim_R2_evidence.json、132站原始来源 research_engine/retirement/status/meteostat_CN132_interim_R2_parameter_source.csv、全国2847参数进度 research_engine/retirement/status/national_R2_132_interim_obs_source_2847.csv。下一动作按原用户冻结方法将R1与R2逐县联结，明确同时取证数、只温度、只降雨、均无证据，以及首次可用筛选候选集和待核逻辑，不改变正式评级门槛。

- RES-214-R1_199-R2_INTERSECTION199_2633_NO_SOURCES-20261107: 全国2847县R1+R2源交集GitHub run42337775860实际执行且远程hash核验通过。R1某类点位214，R2某类点位199，双轮都有部分数据199(73双较长基期、125双短历史、1个R1较长R2短历史)，仅R1 15(13长+2短)，仅R2 0，双无2633，2847守恒，无正式评级/淘汰。已通过个人Library实读V1.2正式母版与V1.3全国覆盖补充，明确冬白天18—25℃、夏白天25—29℃、日照2200h、雨量1000mm为理想参考并非硬淘汰阈值，缺证据保留待核。审计 research_engine/retirement/status/national_2847_R1_R2_joint_cascade_summary.json；全国台账 research_engine/retirement/status/national_2847_R1_R2_joint_cascade_evidence_and_next_gap.csv；首批199个双证据候选 research_engine/retirement/status/national_R1_R2_double_observed_candidate_list.csv。下一动作以73个双较长来源县为对象，做真实参数偏好对照与缺项分类，不因不符理想单项自行排除。

- RES-73-LONG_HISTORY-NONFATAL_IDEALS-42_4PARAM-20261107: 依据已读Library正式V1.2 §四、§七理想值（非硬淘汰线），GitHub Actions 42338105942实际读取全国2847交叉台账，截取R1/R2同时较长来源73个真实县级点位，逐项冻结源分层：冬白天Tmax 18—25℃ 达12/低60/高1；夏季Jun-Sep Tmax 25—29℃ 达25/低14/高34；年日照≥2200h 达30/低12/未测31；年降水≤1000mm 达44/超29。仅42个有完整四项数值，0个四项同时落理想区间；但此为预审偏离记录，住宅气候/潮湿热连续期、空气与饮水及地灾未核，不能作正式等级或提前直接淘汰。遇ERA5网格与Meteostat站点并存，独立保留原始替代值并记模型/站点来源；NASA异常温度不得使用。正式有效县级广筛0，淘汰0，2847全量保留；R1证据214、R2证据199不变。原始摘要：research_engine/retirement/status/national_73_climate_ideal_source_comparison_evidence.json；73行数据：research_engine/retirement/status/national_73_longer_R1_R2_climate_ideal_preference_triage.csv。下一阶段直接继续R3海拔证据，严格以实际住宅海拔而非站点标高确定海拔等级，推进缺失参数分轮漏斗。

- RES-R3-201_STATIONS_PLUS36_DEM_205_COUNTRY_PARTIAL-20261107: V1.6全国R3海拔有真实新增，GitHub Actions 42338533885成功：复用201个已有双GIS气象站海拔元数据分属198县级候选，并复用12县共36个真实Copernicus DEM GLO90点，二者重叠5县，联合205个不同县级候选具有部分地形/海拔点位证据，其余2642无R3点位。193县仅站点、5县双证据、7县仅DEM。27县至少一个站点或3点DEM海拔超过2000米，只记空间警示，不作住宅D级或直接淘汰；5县局部海拔高差大于等于500米：东区510402、蒙自市532503、景洪市532801、大理市532901、格尔木市632801。蒙自县内3点376/1311/2087m，大理1972/2299/3307m，格尔木双站2809/4535m，均必须保留低海拔河谷/成熟住宅例外。此轮不新增2026官方县界、不确认住宅位置、洪涝地灾/空气/水质、不变A/B/C/D，全部2847继续，正式有效县级筛选0。证据 research_engine/retirement/status/national_R3_205_station_dem_altitude_source_evidence.json；2847条R3全量 research_engine/retirement/status/national_R3_205_station_dem_altitude_partial_2847.csv；205县实际点位来源 research_engine/retirement/status/national_R3_205_station_dem_point_evidence.csv。下一行动转R4全国空气/臭氧质量来源攻关，优先全国可批量下载的官方多年城市级PM2.5、臭氧和污染源，区分城市监测与住宅点、行政口径和缺数据待核。

- RES-MEE-2025-168_CITY_PM25_1510_PARENT_CONTEXT_ONLY-20261107: 根据正式R4环境空气自然条件要求，实际读取中国生态环境部2026-01-28发布2025年度168重点城市空气PM2.5浓度原始六张JPG附表并逐张获得HTTP200、原图SHA256，建立168个城市2025年全年PM2.5统计表，全部168城与2025代码源唯一关联。GitHub Actions成功run42339149785、原图6/6下载、结果CSV远端SHA回读通过。168个城市可给2847暂定县码中的1510县提供所属上级城市年度PM2.5背景上下文，其余1337无该城市上下文；城市空气浓度不是县域/住宅街道监测，更不是O3、污染源审核，故县级正式R4完成仍0，正式自然分级0、淘汰0。转录源图虽真实下载及可视核验，168个数字仍待独立第二轮逐格复核，必须在进一步重大决定前执行。样本年值：拉萨10.5、海口15.4、厦门17.4、贵阳20.0、昆明20.2、成都33.1微克/立方米。源 research_engine/retirement/status/mee_2025_168_official_city_PM25_context_evidence.json；城市数据 research_engine/retirement/status/mee_2025_168_official_city_PM25_verified_source.csv；全国2847城市背景映射 research_engine/retirement/status/national_R4_2025_168_city_PM25_CONTEXT_ONLY_2847.csv。下一动作优先生态环境部官方2025年度臭氧及优良天数的可获取城市级实际数据、2024/2025可比性核验和工业污染空间局部例外，不把全国平均数强加到各城市。

- RES-R4-58_FJ_COUNTY_2YEAR_PM25_AND_10CITY_O3_ALL_UP-20261107: 唯一R4-O3-TREND-013本轮真实闭环，GitHub run42339392998成功从福建省生态环境厅原始2024年与2025年全年两份HTML年报对应2025/02/06、2026/01/23下载并解析SHA，58县年度PM2.5两年逐一同代码配对：29县下降、14县上升、15县不变；9设区市+平潭共10个单位O3日最大8小时均值第90百分位浓度2025比2024全部上升，厦门114→136、福州132→136μg/m³；十城另有真实优良天数及PM2.5两年比较。县级原表仅“首要污染物”为臭氧，不提供县级O3数值，禁止将十城O3灌入县级监测表。同期生态环境部另有168个重点城市2025年PM2.5官方表格且提供1510县级上级城市背景，仅作CITY_CONTEXT，绝不能冒充1510县级PM2.5实测。R4真正县级部分实测仍60（此前2+福建58），R1=214，R2=199，R3=205，正式有效县级筛选0、淘汰0、全国2847全留。福建两年交叉证据 research_engine/retirement/status/Fujian2024_2025_air_pollution_two_year_evidence.json，城市10行 research_engine/retirement/status/Fujian2024_2025_10city_PM25_O3_two_year_source.csv，58县两年 research_engine/retirement/status/Fujian2024_2025_county_PM25_two_year_source.csv，R4全国2847台账 research_engine/retirement/status/national_R4_official_Fujian2025_county_PM25_2847.csv。下一唯一动作R5全国真实饮用水水源/出厂/末梢监测和工业源；优先县级官方批量，城市水源不代替住宅供水。

- RES-R5-FUJIAN2025DEC-109_SOURCES_56_COUNTY-20261107: R5 取水口原水真实县级批量突破。GitHub run42339705540真实读取福建省生态环境厅2026-01-23发布《2025年12月县级以上集中式生活饮用水水源水质》附表，109个在用集中式饮用水水源点全部达标（按地表/地下水Ⅲ类及优于Ⅲ类标准），82处县级名称精确链接56个临时代码，26处仅地级市环境背景、1处平潭综合实验区行政名未精确对应而HOLD。旧R5仅1县部分源证据，新增56县原水点位→R5共57县具有至少一种部分水源证据，余2790县R5尚无源数据。不能把原水取水口达标当自来水厂出厂水或住宅末梢健康达标；采样期仅2025年12月，禁止作为多年水质认定和正式县级评级，全量2847继续、正式完成0、剔除0。原始官方URL https://sthjt.fujian.gov.cn/zwgk/sjfb/hjsj/yyssysz/202601/t20260126_7085249.htm；县级证据 research_engine/retirement/status/Fujian2025_12_R5_official_raw_water_source_evidence.json，109条点位 research_engine/retirement/status/Fujian2025_12_109_official_intake_sources.csv，2847全国台账 research_engine/retirement/status/national_R5_Fujian2025_12_109_official_source_intakes_2847.csv。下一动作专门查2025/2026福建及其他省市卫健委/供水公司县级出厂水和管网末梢官方报告，并进行水源/出厂/末梢三层对应与历史风险审计。

- RES-R5_4NEW_COUNTY_FINISHED_TAP_OUTLET_61_PARTIAL-20261107: GitHub Actions 42340188268真实成功执行2025年跨省7县级卫健/供水官方原始材料查验，4份通过网络下载、正文关键检验项目和2025临时行政代码严格核对：阜新蒙古族自治县39户居民家末梢水、科尔沁右翼中旗15城乡末梢点、湖南鹤城区25末梢点、宁波海曙区第四季度末梢水指标合格率（站点数未明）；均为单季度/有限点位，不是全县住宅安全证明。福建泉港2025年Q3官方PDF存在但当前文字层无法实际校验，包头青山区官方PDF执行网络不可达，香格里拉出厂水官方网页HTTP404，三条保留不计。R5从福建56县原水点＋蒙自既有具名末梢的57个部分县级证据增至61，仍缺2786，全部2847保留，县级正式完成0。源报告 research_engine/retirement/status/R5_2025_crossprovince_7counties_finished_tap_plant_source_evidence.json，完整增量总表 research_engine/retirement/status/national_R5_2025_7district_finished_water_source_partial_2847.csv，Library正式Master不覆盖。下一行动为全国R0-R5统一联表与缺失优先排序，禁止把城市级空气、水源或低质量气候模型冒充住宅/正式合格评级。

- RES-2847_R1R2R3R4R5_UNIFIED_214_199_205_58_61-20261107: GitHub Actions 42340740092通过真实R0-R5来源SHA校验并将全部2847临时县级候选按唯一县级编码左连接：R1气温点证据214(长期/ERA5 87＋短于完整30年127)、R2降雨日照点199(73＋126)、R3站点/DEM海拔点205、R4福建官方县级PM2.5记录58，另2025生态环境部168城市官方PM2.5背景仅可映射1510县作市级参照(不是县空气实测)、R5福建56县取水口＋蒙自既有具名末梢＋2025四县水龙头样本合计61。R1R2R3部分点证据交叉199县，五轮均至少一种部分资料仅福建永安市350481(并非具备所有最终必需参数，更不能评估适居)。目前没有可按冻结标准正式评A级B级C级D级的县域；全2847待核继续、自动淘汰0。三份新增可重复资产：一张2847行全国联表 research_engine/retirement/status/national_R0_R5_unified_2847_county_evidence_and_missing.csv、一张31省级代码覆盖 research_engine/retirement/status/national_R0_R5_by_province_evidence_coverage.csv、150个资料较完整候选工作清单 research_engine/retirement/status/national_R0_R5_high_evidence_local_followups.csv。审计 research_engine/retirement/status/national_R0_R5_unified_evidence_audit.json。此为工作证据总表，绝不覆盖个人Library正式Master。下一行动应从全国R1/R2覆盖最少的2633/2648县级候选继续找可批量核验的1991—2020格网气候，保持时间和空间质量门；高资料区只用于核验管线，不能代替全国覆盖。

- GHA-42391693365: ScienceDB V8 tasmax单变量全国空间计算未形成可验证县级数值增量（FAILED_OR_BLOCKED）；记录本次错误/状态，不把下载或流程运行计作研究进展。当前R1/R2动作保留，所有2847候选继续，正式广筛0。


- RES-NATIONAL-73-EXISTING-EVIDENCE-HARD-SCREEN-20261108-42432941043: 对已有73个较长历史R1/R2候选按用户确认的第一阶段硬线进行实际批量筛查。冬季低于10℃信号46个、夏季达到/超过32℃信号10个、日照低于1800小时信号6个，至少一项气候信号56个；其中42个有三项气候数据，12个未见已测硬线信号，5个无已知温度触发但缺日照。73个中11个有站点/DEM点位超过2000m，3个仅海拔点位触发。冬夏指标为多月平均日最高温，触线只作单向预筛；点位不等于住宅点，故正式居住片区淘汰0、正式县级筛选0、2847底盘全部保留。明细：research_engine/retirement/status/national_73_existing_evidence_hard_screen_20261108.csv；205点海拔复核：research_engine/retirement/status/national_205_altitude_point_hardline_review_20261108.csv；审计：research_engine/retirement/status/national_73_existing_evidence_hard_screen_20261108.json。下一动作直接处理127个短历史R1和126个短历史R2候选，继续扩大批量硬线信号筛查。

- RES-NATIONAL-SHORT-HISTORY-127R1-126R2-HARD-SCREEN-20261108-42433374537: 对127个短历史R1温度候选及126个短历史R2降雨/日照候选执行第二批真实硬线信号筛查。R1冬季低于10℃97个、夏季达到/超过32℃15个，至少一项温度信号109个；R2仅9个候选有日照观测，均未低于1800h，其余117个日照待定；R1中16个站点/DEM点超过2000m，仅触发实际住宅海拔复核。短历史不冒充30年常年值，站点不等于住宅点，正式排除0、正式县级筛选0、2847底盘全部保留。明细：research_engine/retirement/status/national_127_short_history_R1_hard_screen_20261108.csv；日照：research_engine/retirement/status/national_126_short_history_R2_sunshine_review_20261108.csv；审计：research_engine/retirement/status/national_short_history_hard_screen_20261108.json。下一动作筛查剩余14个长期R1-only候选，并把已筛信号映射到第一阶段实际居住片区清单。

- RES-NATIONAL-14-LONG-R1-ONLY-AND-214-ROLLUP-20261108-42433856408: 将此前未纳入73长R1/R2批次的14个长期R1-only候选全部筛查，并与73个长期R1/R2、127个短历史R1合并为214个去重点位温度证据候选。14个新增中11个至少触发一项温度硬线，3个未见温度触发但日照缺项。214个候选汇总冬季<10℃153个、夏季≥32℃26个、日照<1800h6个，至少一项气候硬线信号176个；日照有直接观测51个，其余待核；站点/DEM点位海拔>2000m警示16个。正式住宅片区淘汰0、正式县级筛选0、2847底盘继续保留。214点位汇总：research_engine/retirement/status/national_214_R1_all_evidence_hard_screen_20261108.csv；14个补筛：research_engine/retirement/status/national_14_long_R1_only_hard_screen_20261108.csv；审计：research_engine/retirement/status/national_214_R1_hardline_signal_rollup_20261108.json。下一步不再扩展全县参数表，转入29个首轮居住片区+14个扩样片区精确交叉映射，形成区域去留清单。

- RES-NATIONAL-40-NAMED-REGION-CROSSWALK-20261108-42434214142: 完成29个首轮样点+14个扩样记录交叉映射，去重为40个具体居住片区；精确匹配214个R1点位证据，匹配片区18个、无精确匹配22个、匹配到气候硬线信号10个。同步修复214行汇总表的海拔字段映射错误：73长历史批次11个、127短历史批次16个点位>2000m，合计27个点位警示；正式住宅片区退出仍为0，所有缺失待定。明细：research_engine/retirement/status/national_40_named_region_candidate_crosswalk_20261108.csv；审计：research_engine/retirement/status/national_40_named_region_candidate_crosswalk_20261108.json。下一动作直接形成40个居住片区的首轮保留/待核/退出清单，不再做2847县逐行参数表。

- RES-NATIONAL-40-REGION-DISPOSITION-20261108-42434491753: 对40个去重后的第一阶段居住片区形成首轮处置草案：12个既有样点继续退出；新增3个强冬季/夏季硬线预排除（武都、伊宁、荣成）；百色1个温度来源冲突待一次核验；大理按2000m实际住宅海拔分片；4个优先保留，其他按条件保留/待核流转。昆明中心城区1891m、蒙自坝区约1300m，DEM周边高点不作为住宅淘汰。正式住宅片区退出仍待最后一次住宅点代表性确认；第二、三阶段名单不缩减。明细：research_engine/retirement/status/national_40_region_disposition_20261108.csv；审计：research_engine/retirement/status/national_40_region_disposition_20261108.json。下一轮只核实7个最有价值的预排除/冲突样点，其余缺数区域暂搁置，不再逐一耗时。

- 2026-11-08T01:42:20.882Z: SCOPE CORRECTION. 重新读取Library正式母表《退休宜居城市_第一阶段全国首轮区域收敛_V2_20261107.xlsx》后，确认正式第一阶段底盘为20个既有片区+14个去重新增片区=34个评价单元；29个全国代表性气候样点是独立证据集，不得与14个扩样池拼成40个正式候选。12个是29样点中的样点级硬线信号，不是12个正式退出；当前正式住宅片区退出仍为0。V2扩样池中仅霞浦、勉县、利川3个为预排除待复核。此前RES-NATIONAL-40-REGION-DISPOSITION-20261108-42434491753及其40区映射已隔离，保留审计但不得用于正式候选池/退出统计。已重建34单元正式名册、29样点独立筛查表、7项硬线核验队列。下一步只核7项：霞浦、勉县、利川、百色城区、武都、伊宁、荣成；单项一次主源+一次替代源，缺失即PENDING，不再耗时追索。