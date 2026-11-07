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
