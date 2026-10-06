# Deep Native

**让接入 DeepSeek 的 Claude Code，以证据驱动编码交付。**

[English](README.md) · [详细教程](docs/tutorial.zh-CN.md) · [实际演示](docs/demo/demo.html) · [验证报告](docs/validation.md) · [三组评测方法](evals/README.md)

> No evidence, no done.
> 这是一个 Skill + 本地验证工具，不是模型升级器，也没有“DeepSeek 已达到 Claude 水平”的结论。

## 当前能做什么

Skill 引导模型先读代码、复现问题，再小步修改、回归验证和交付。辅助工具负责实际执行预设检查、记录退出码和超时，将证据绑定到代码内容；修改后仍想沿用旧证据，会被 `finish` 拒绝。

长任务可以保存进度并恢复。可选 Hooks 在匹配的会话恢复时补充检查点，在缺少验证时提醒一次；不会无限阻止结束，不会扩大工具权限，也不会修改全局模型配置。

## 先运行一次演示

要求 Python 3.10+、Git，macOS 或 Linux。无需 API Key。

```bash
git clone https://github.com/Anhao1314/deep-native.git
cd deep-native
python3 -m unittest discover -s tests -v
python3 examples/demo.py --output artifacts/demo
open artifacts/demo/demo.html
```

最后一行适用于 macOS；Linux 直接用浏览器打开该文件。演示内容为：

```text
真实失败测试 -> 拒绝提前完成 -> 明确标注的脚本修复
-> 恢复进度 -> 实际验证通过 -> 代码再变更后拒绝旧证据
-> 重新验证 -> 带限制说明完成
```

**代码修复由演示脚本执行，不是 DeepSeek 自主完成。** 网页展示的是实际命令回放，不是实时 Agent，也不是模型性能评测。

## 装进你正在使用的项目

保留你现有的 Claude Code + DeepSeek API 配置，不要把 Key 发到聊天或仓库。

```bash
PROJECT="/你的项目的绝对路径"
python3 deep_native.py --project "$PROJECT" doctor
python3 deep_native.py --project "$PROJECT" install
```

重启该项目内的 Claude Code，输入：

```text
/deep-native 修复这个项目的问题。先调查和复现，再修改、添加回归测试，最后提供真实验证结果与未覆盖的风险。
```

需要可选会话恢复和停止提醒时：

```bash
python3 deep_native.py --project "$PROJECT" install --hooks
```

只安装到指定项目。安装器不会覆盖内容不同的已有 Skill；不会替你购买模型、改 API Key 或开启绕过权限。完整参数、如何设置项目测试命令、卸载与故障处理，见[详细教程](docs/tutorial.zh-CN.md)。

## 真实本机 Preliminary Pilot：已暂停

**阶段判断：STOP，停止扩样。** 原计划 60 次，按用户要求在当前运行完成后暂停，
实际保留 21 次：Raw 10 次、Deep Native 11 次。
其中 20 次构成 10 个完整配对；额外的 T08 第二次 B 运行通过，单独保留。

![配对阶段成功率](evals/benchmark-v1/reviews/preliminary-v4-matched.png)

| 指标 | Raw DeepSeek | DeepSeek + Deep Native |
| --- | ---: | ---: |
| 配对 20 次独立成功率 | 8/10（80.0%） | 7/10（70.0%） |
| 全部保留运行的成功率 | 8/10（80.0%） | 8/11（72.7%） |
| Verified Completion / 明确 DONE | 5/5 | 1/1 |
| 完成声明未知 | 5/10 | 10/11 |
| 全部运行耗时中位数（秒） | 108.0 | 103.7 |
| 可用总 token 中位数（含缓存） | 465,399（9/10 可用） | 482,782（9/11 可用） |
| 工具调用中位数 | 29.0 | 36.0 |
| 真实 API 费用 | unavailable | unavailable |

配对耗时 B/A 比值中位数约 1.20（10 对），token 比值约 1.21（8 对）。
质量结果为 B 胜 0、负 1（T08）、平 9；没有观察到完成率改善信号。
固定最终声明规则下，两组 false completion 均为 0，但明确 DONE 样本很少，
尤其 B 的未知声明较多，不能据此声称降低了 false completion。

这是阶段性描述，不是正式统计结论。原冻结规则下的完整实验判断仍为 INCONCLUSIVE。
独立评分与证据哈希核对通过；轨迹中有 17 次沙箱导致的 shell 临时文件拒写，
自动验证标记也存在误识别，因而不能将当前差异完全归因于 Skill。
Deep Native 保持 `fda3dd0`，未做任务调优，暂停后没有继续模型调用。

[阶段报告](evals/benchmark-v1/reviews/preliminary-v4.zh-CN.md) · [机器可读结果](evals/benchmark-v1/reviews/preliminary-v4.json) ·
[方法与复现](evals/benchmark-v1/README.md) ·
[原始证据](evals/benchmark-v1/results/2026-10-06-pilot-v4/runs/)

## 已验证与未验证

本地工具测试、失败路径、12 步演示、三组同起点评测夹具已执行，结果见[验证报告](docs/validation.md)。

v0.1 最初开发环境没有 Claude Code 或模型凭据。后续本机 Preliminary Pilot 已记录真实宿主加载与 DeepSeek 调用，见上方阶段结果；与原生 Claude 的对照仍未执行，没有模型等价承诺。

这版交付的是可安装、可复现、可继续评测的基础版本。它不是安全沙盒；本地记录也不是不可伪造的证明。请在可信项目运行，并由独立测试与人工评审判断最终正确性。
