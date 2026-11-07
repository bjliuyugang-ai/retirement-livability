# 退休城市·集中攻关｜V1.6唯一执行入口
1. 先打开 `tasks/6aead9a989808191ad42f80fd4e32bf1/phase1/RUN_STATE.json`、本文件和 `research_assets/retirement/CURRENT_STATE.md`，核对blob/版本、上次结论和上轮日志；再只读个人Library固定目录的正式V1.2基线、Excel Master及增量。二者任一真值不可读则登记阻塞，不宣称PASS。
2. 严格执行S0—S6：状态读取→对账→领取唯一ACTION_ID→真实运行→区分工程/研究增量→证据与状态写回→重新打开核验。每轮留下RUN_ID、PRECHECK/POSTCHECK证据、命令/源文件与hash；完成状态不可代替研究增量。
3. 本轮只执行RUN_STATE.active_action，严禁从历史长提示中任选其他研究事项。入口不硬编码当前ACTION_ID，必须以每次实读RUN_STATE.active_action.action_id为准；上轮完成时依证据封存并转下一唯一动作。如两轮失败，同法不得再试，必须更换合规源/方法。到24/48h节点给PASS/FAIL/INCONCLUSIVE裁决。保留全国有效县级覆盖100%最终门槛、数据缺失待核、海拔/微气候例外、官方口径对账、阈值未批准不得正式排除、Library正式Master不在无人值守覆盖等全部冻结约束。
此入口只变更执行方式，不变更研究目标/批准门槛。GitHub仓库为工程指针，个人Library仍为正式研究基线与Master。

## 集中攻关期调度决定｜2026-11-07
用户明确同意在集中攻关阶段暂停例行小时任务，形成实质成果后再考虑恢复。本条仅改变调度方式，所有正式研究约束和V1.6执行规范均继承。
- ChatGPT 定时任务 ID `6aead9a989808191ad42f80fd4e32bf1` 当前已暂停（未删除）；禁止在未获用户新授权时自动恢复。
- GitHub Actions工作流的每小时`schedule`已取消；保留`workflow_dispatch`和按特定代码提交触发的路径，以便集中攻关和单次实证。其余工程工作流无定时`schedule`。
- 重新启用小时任务的建议验收门：①产生首批可核验的县级有效广筛记录并完成适用边界审计；②批处理具有可复现输入/输出、失败分类与自动状态交接；③至少连续两次不同RUN_ID运行完整S0—S6并通过POSTCHECK；④经用户同意恢复小时调度。未通过时继续按用户主动触发的集中攻关方式执行，不以时间流逝自动恢复。
- 当前RUN_STATE.active_action仍为研究执行唯一指针；暂停调度不代表项目完成、正式县级广筛增量、或解除已登记阻塞。无人值守不覆盖Library Master。
