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
