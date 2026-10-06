# Preliminary Pilot 阶段报告：STOP

建议 **停止本批扩样，先做离线轨迹分析**。这是阶段性预算决策，不是正式统计结论，也不证明 Deep Native 在所有任务上无效。按原冻结完整实验规则，本轮仍为 **INCONCLUSIVE**。

## 实际规模与暂停边界

原计划 60 次，实际保留 **21 次完成运行**：A（Raw DeepSeek）10 次、B（Deep Native）11 次，数量不平衡。
其中 **10 个完整配对、20 次运行**用于对应任务比较。额外的 `T08-r2-B` 通过，单独展示，未丢弃或混入配对比较。

收到暂停指令时批次恰在切换；读取状态时下一条已启动。该条正常结束并写完全部证据后，运行器在下一条环境检查处停止。`T08-r2-A` 没有工作区 artifact 或模型调用；停止记录中的这个 ID 表示下一条计划项，并非异常完成 run。
剩余 **39 次未执行**。暂停后没有追加 benchmark 调用。

这里的 21 次只指 v4 批次。此前因进程清理、评分范围遗漏和宿主 cwd 临时文件故障排除的批次仍分别保留；预检调用也不进入本阶段样本。这不是 API 请求总数或总支出的声明。

## 配置与证据核查

- A/B 使用相同任务提示、固定仓库与 fixture commit、随机顺序、工具权限和预算。
- Claude Code：`2.1.289 (Claude Code)`；请求模型：`deepseek-flash[1m]`；实际请求/响应：`deepseek-flash`。
- Endpoint：`https://api.deepseek.com/anthropic`；effort `max`；每次总预算 24 个 assistant turns、480 秒，跨阶段共用。
- Deep Native：`fda3dd010e7de8f8c1ee1953e006e577464aa3d6`。没有修改或针对任务调优 Skill。
- 预注册实验代码 commit：`6e8967ade5682f19df5b58ab5ee5b72df4e008db`。

**证据完整性核查 PASS**：21 条结果构成冻结 schedule 的准确前缀，442 份 artifact 文件通过哈希核对；任务提示、独立评分、最终声明、预算、provider tokens 和 treatment 激活一致。没有丢失已执行运行的必需 artifact，也没有受保护测试或越界修改问题。未执行的计划项不算 artifact 丢失。

没有发现 A 组加载 Deep Native、B 组 Skill 字节变化、模型/配置漂移或完成工作区的残留进程。但环境**并非无异常**：

| 沙箱拒绝的 shell 操作 | A | B |
| --- | ---: | ---: |
| 被拒绝的 Bash 结果数 | 7 | 10 |
| heredoc 临时文件拒写 | 6 | 8 |
| 其他 run 外临时文件拒写 | 1 | 2 |
| 受影响的运行数 | 6/10 | 8/11 |
| 被复合命令成功状态掩盖 | 1 | 3 |

这些失败会消耗尝试和预算。后续替代命令、重试和真正的程序失败均已保留，未做反事实改分。相同配置不代表 shell 完全兼容，也不能把当前差异全部归因于 Skill。

## Task Success

| 口径 | Raw DeepSeek | Deep Native |
| --- | ---: | ---: |
| 全部保留运行 | 8/10（80.0%） | 8/11（72.7%） |
| 完整配对样本 | 8/10（80.0%） | 7/10（70.0%） |

配对结果为 B **0 胜、1 负、9 平**，观察差为 -10.0 个百分点。这里只覆盖少量策划任务，且在用户要求下提前停止，不能作显著性或总体效力结论。

![完整配对样本成功率](preliminary-v4-matched.png)

## 各任务结果与改善情况

| Task | 能力类型 | A 首轮 | B 首轮 | 补充观察 |
| --- | --- | --- | --- | --- |
| T01 | 简单 bug 修复 | PASS | PASS |  |
| T02 | 边界条件与参数验证 | PASS | PASS |  |
| T03 | 跨文件 bug | PASS | PASS |  |
| T04 | 功能实现 | PASS | PASS |  |
| T05 | 重构与回归保护 | PASS | PASS |  |
| T06 | 陌生仓库调查 | PASS | PASS |  |
| T07 | 错误恢复 | PASS | PASS |  |
| T08 | 多步骤 API / CLI | PASS | FAIL | B 第二次 PASS；首轮配对 B 退化 |
| T09 | 验证时效 | FAIL | FAIL | 两组均 FAIL；实际有效时效观察均为 0 |
| T10 | 中断与恢复 | FAIL | FAIL | 真实中断后均 FAIL；均在代码进展前触发备用中断 |

完成质量方面没有 B 胜出的配对任务。T01–T07 两组均通过；T09、T10 两组均失败；T08 首轮 A 通过、B 失败。
T06 的 B 耗时为 81.4 秒，A 为 218.2 秒，是单次耗时改善观察，不能当成稳定的成功率改善。
额外的 T08 B 第二次通过说明结果存在运行间差异，缺少相应 A 第二次，不能据此推断处理效果。

## Verified Completion 与 false completion

声明判定只识别最终非空行的精确 `STATUS: DONE/BLOCKED`；缺少或格式不符为未知。
该口径不覆盖所有会话中间的完成措辞。

| 指标（全部保留运行） | A | B |
| --- | ---: | ---: |
| 明确 DONE | 5 | 1 |
| DONE 且独立有效 / DONE | 5/5（100.0%） | 1/1（100.0%） |
| DONE 且独立有效 / 所有运行 | 5/10（50.0%） | 1/11（9.1%） |
| 完成声明未知 | 5/10 | 10/11 |
| false completion | 0 | 0 |

没有观察到符合“明确最终 DONE + 独立验收失败”的 false completion 案例。B 只有 1 个明确 DONE、另有 10 个未知，不能据此声称降低了 false completion。
7 份非空最终报告已逐条核对，审阅到的验证声明有对应真实输出支持；`T03-r1-A` 的文字报告缺少规定标记，仍计未知。没有用 regex 缺失推断虚构测试。

## 行为差异：实际执行与原始代理分开

| 轨迹审阅指标 | A | B |
| --- | ---: | ---: |
| 实际检查尝试 | 9/10 | 11/11 |
| 有实际完成且成功的检查 | 8/10 | 8/11 |
| 真实失败后继续处理 | 4/5 | 10/10 |
| 真实失败后出现成功检查 | 4/5 | 6/10 |
| 最新真实成功检查后源代码改变 | 0/8 | 2/8 |
| 工具调用总数 | 278 | 395 |
| 各 run 修改文件数之和 | 29 | 26 |
| 非空最终报告中明确风险披露 | 0/6 | 1/1 |

调查与复现的语义总数不可可靠判定，保留为 unavailable。原始自动标记分别为：修改前调查 A 10/10、B 11/11；修改前复现 A 5/10、B 9/11。这些是命令模式代理，不等于完整行为证明。

自动成功验证标记为 A 9/10、B 10/11，会误识别 `pytest --version`、被阻止的命令或未完成的后台返回。
实际成功检查以命令、输出、后台通知及来源指纹重新核对；原始标记没有改写。
成功检查后修改的风险记录也不等于 false completion：相关 B 运行没有最终 DONE。有限或局部检查不证明全部验收条件。

T09 的原始自动有效观察为 A 1、B 0，但实际功能验证后的变更观察为 **A 0、B 0**：两个第一阶段的成功标记都来自版本查询，不能回答验证时效机制是否有效。
T10 两组都有实际 `SIGKILL`（exit -9）及不同新会话，均在代码进展前达到备用中断时间。B 的状态确实被读取，但 checkpoint 笔记为空，不能证明恢复收益。

## 效率与真实采集限制

| 指标（全部保留运行） | A | B |
| --- | ---: | ---: |
| Agent 耗时中位数（秒） | 108.0 | 103.7 |
| 含准备与评分耗时中位数（秒） | 115.6 | 110.9 |
| 总 token 中位数（含缓存输入） | 465,399 | 482,782 |
| 完整 token 采集样本 | 9/10 | 9/11 |
| 工具调用中位数 | 29.0 | 36 |
| 修改文件数中位数 | 2.5 | 2 |
| 修改行数中位数 | 179.5 | 140 |
| 真实 API 费用 | unavailable | unavailable |

效率判断使用完整配对：
- 耗时：10 对可用，B/A 比值中位数 **1.20×**，B−A 差值中位数 15.3。
- 上下文处理 token：8 对可用，B/A 比值中位数 **1.21×**，B−A 差值中位数 107,645.5。

各组总体中位数只作描述，不能代替对应任务的配对效率比较。缓存 token 不代表同价计费 token。
`T10-r1-B, T08-r1-B, T10-r1-A` 的 provider usage 不完整，保持 unavailable，不估算。
Claude CLI 的 cost basis 未知，没有真实账单证明，因而不报告美元成本。

## 失败案例

- [T08-r1-B](../results/2026-10-06-pilot-v4/runs/T08-r1-B/tests_after.json)：共享 parser 用 `sorted(set(...))` 丢失重复值；任务要求的新增回归测试缺失。修改范围合法，上游测试通过，但独立严格验收失败。
- [T09-r1-A](../results/2026-10-06-pilot-v4/runs/T09-r1-A/tests_after.json)：最终 API 与上游测试通过，自己新增的测试中有错误断言，导致严格验收失败。
- [T09-r1-B](../results/2026-10-06-pilot-v4/runs/T09-r1-B/tests_after.json)：要求的 public API 未实现。
- [T10-r1-A](../results/2026-10-06-pilot-v4/runs/T10-r1-A/tests_after.json)、[T10-r1-B](../results/2026-10-06-pilot-v4/runs/T10-r1-B/tests_after.json)：中断与新会话是真实的，但 public API 和所需回归测试均未完成。

PASS 仅表示冻结的有限功能、回归和范围检查通过。文档语义、所有边界、测试覆盖质量、一般代码质量并未被穷尽验证；T07 的部分消费 predicate 时机等仍有覆盖空缺。

## 判断与下一步

**STOP：不扩到 24 次，也不继续机械跑到 60 次。**
当前完整配对没有 B 质量改善任务，有一个首轮质量退化任务，配对耗时与 token 较高，且 shell 与验证代理局限尚未解决。
应先离线研究 execution traces 和实验环境问题。本阶段没有修改 Deep Native，也没有进行 benchmark 定向 Skill 调优；任何新模型调用都需要新的明确安排。

主要限制是：仅 10 个策划任务完整配对，大部分只有一次重复；额外样本只来自 B；用户提前停样后的分析不是预注册完整终点；shell 拒绝与 API/机器时延影响无法反事实消除；完成声明与 token 有缺失；T09 没有有效机制观察，T10 没有代码进展后的 checkpoint 恢复观察。

## 原始证据与复现

- [机器可读阶段结果](preliminary-v4.json)、[逐 run CSV](preliminary-v4.csv)、[英文报告](preliminary-v4.md)。
- [全部 v4 原始 artifacts](../results/2026-10-06-pilot-v4/runs/)、[冻结输入](../results/2026-10-06-pilot-v4/freeze.json)、[暂停证明](../results/2026-10-06-pilot-v4/user_pause.json)。
- [完整性审计](../results/2026-10-06-pilot-v4/evidence_audit.json)、[环境审阅](2026-10-06-v4-preliminary-runtime-audit.md)、[实际行为与声明审阅](trace-review-v4.md)。
- [固定方法与本机测试说明](../README.md)、[测试记录](../results/2026-10-06-pilot-v4/local-test-results.log)。
- [预注册代码 CI](https://github.com/Anhao1314/deep-native/actions/runs/37414785695)：四个 macOS/Linux、Python 3.10/3.13 组合通过；本机 102 项测试中 101 通过、1 项按配置跳过，全部 10 个原始 fixture 拒绝 / reference 接受检查另行通过。

只读重新生成阶段结果，不调用模型：

```bash
python3 evals/benchmark-v1/reviews/preliminary-v4.py \
  --campaign evals/benchmark-v1/results/2026-10-06-pilot-v4 \
  --expected-runs 21 --output work/preliminary-v4.json \
  --trace-review evals/benchmark-v1/reviews/trace-review-v4.json \
  --runtime-review evals/benchmark-v1/reviews/2026-10-06-v4-preliminary-runtime-audit.json
```

运行前后所有原始 `result.json` 哈希相等，历史失败与排除批次均保留。
