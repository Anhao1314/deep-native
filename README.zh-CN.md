# Deep Native

**让接入 DeepSeek 的 Claude Code，默认少折腾，必要时才进入深度 Agent 工作流。**

[English](README.md) · [完整教程](docs/tutorial.zh-CN.md) · [架构](docs/architecture.md) · [v0.1 实验结论](docs/v0.1-pilot-findings.md) · [v0.2 消融实验](evals/v0.2-ablation.md)

> **默认轻量，证据要求升级时再升级。**
>
> Deep Native 是一个 Skill + 本地确定性验证工具，不是模型权重升级器，也没有“DeepSeek 已达到 Claude”的结论。

## 为什么要重做 v0.2 Candidate

第一次真实 A/B Pilot 没有得到我们想要的结果。

10 个完整配对中：

| 指标 | Raw DeepSeek | Deep Native v0.1 |
| --- | ---: | ---: |
| 严格任务成功率 | **8/10** | **7/10** |
| 配对质量结果 | — | **0 胜 / 1 负 / 9 平** |
| 工具调用中位数 | 29 | 36 |
| 真实检查失败后继续处理 | 4/5 | 10/10 |

Deep Native 确实改变了行为，让模型更愿意在失败后继续工作；问题是，更多工作没有稳定变成更好的结果，配对耗时和上下文处理 token 还分别约增加到 **1.20x / 1.21x**。

所以 v0.2 不再给所有任务套完整流程。

## 三档自适应工作流

```text
                         任务
                          |
                     判断复杂度
                /          |          \
             FAST       STANDARD      DEEP
              |             |           |
       局部修改+检查   复现+假设+验证   检查点+证据Runtime
                \          |          /
                      新鲜验证证据
                          |
                        交付
```

- **FAST**：局部、目标清楚、低风险、没有失败尝试。直接读相关代码、修改、跑一个有意义的检查、交付。
- **STANDARD**：跨文件、根因不确定，或第一次尝试失败。先复现并写出一个可验证假设，再修改和验证。
- **DEEP**：两次无效尝试、repo-wide、多子系统、长任务、高风险、可能 compact/中断。只有这时才启用持久状态、checkpoint、verify/finish 和恢复 Hook。

也就是说，小 bug 不再为了“专业感”举行项目启动仪式。

## 失败不是一种东西

v0.2 Candidate 将失败分成：

`implementation · hypothesis · contract · environment · dependency · budget · unknown`

比如 heredoc / temp path 被沙箱拒绝，这是 **environment failure**。正确动作是调整命令、可写路径或执行方式，而不是开始改业务代码。

第二次无效尝试则是升级信号，不能原样再试第三次然后期待宇宙突然变友善。

## 证据层保持稳定

v0.1 已经测试过的本地验证 Runtime 暂时不大改。

DEEP 任务仍然可以：

- 冻结项目实际检查命令；
- 保存小型 checkpoint；
- 执行检查并记录退出码/超时；
- 将通过结果绑定到当前 worktree；
- 代码发生变化后拒绝沿用旧证据；
- 可选地在匹配 Claude Code 会话恢复/停止时提供提醒。

v0.2 主要重做的是**什么时候启用这些机制，以及失败后下一步怎么决策**。

## 安装

```bash
git clone https://github.com/Anhao1314/deep-native.git
cd deep-native

PROJECT="/你的 Git 项目绝对路径"
python3 deep_native.py --project "$PROJECT" doctor
python3 deep_native.py --project "$PROJECT" install
```

重启目标项目中的 Claude Code：

```text
/deep-native 修复重试问题。使用能够安全完成任务的最小工作流，只有证据要求时再升级。
```

长任务需要恢复 Hook 时：

```bash
python3 deep_native.py --project "$PROJECT" install --hooks
```

安装器仍然只作用于项目，不修改全局模型配置、不写 API Key、不扩大权限。

## 真实 Pilot 怎么处理

完整 21-run 原始证据保留在
[`benchmark-v1` 分支](https://github.com/Anhao1314/deep-native/tree/benchmark-v1)，
没有把几十万行 artifact 直接塞进主线。

该实验还发现：

- 17 次 shell/temp 写入拒绝，影响了 14 个 run；
- T09 的“验证时效”没有形成有效观察；
- T10 在真实代码进展前就被中断，没真正测到恢复收益。

所以正式结论仍然是 **INCONCLUSIVE**，而不是“v0.1 已证明失败”或“只是运气不好”。

详细见 [v0.1 实验结论](docs/v0.1-pilot-findings.md)。

## 下一轮不是 60 次

下一步是 **12-run 机制消融**：

```text
Raw DeepSeek
vs
Deep Native v0.1
vs
Deep Native v0.2 Candidate
```

只测四类真正有差距空间的任务：困难根因调试、环境失败分类、最终代码的新鲜验证、中断后真实恢复。

如果 12 次里 v0.2 都没有机制级收益，就停下来继续研究，不机械烧到 60 次。

完整协议见 [evals/v0.2-ablation.md](evals/v0.2-ablation.md)。

## 边界

Skill 可以改善流程，不能凭空生成模型智力。更多规划、更多工具调用、更多 token 都不是“更 Agentic”的证据。

本地验证工具也不是安全沙盒或签名证明。最终仍应依赖真实测试、独立 CI 和代码审查。

MIT License。独立开源项目，与 Anthropic、DeepSeek 无官方隶属或背书关系。
