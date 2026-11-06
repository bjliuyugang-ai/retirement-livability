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
