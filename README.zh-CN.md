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

## 已验证与未验证

本地工具测试、失败路径、12 步演示、三组同起点评测夹具已执行，结果见[验证报告](docs/validation.md)。

**开发环境中没有 Claude Code 可执行程序或模型凭据，外部 DNS 也不可用。因此，真实宿主加载、真实 DeepSeek 调用以及与原生 Claude 的对照尚未执行。** 没有成功率提升百分比，没有 token 节省数据，没有模型等价承诺。

这版交付的是可安装、可复现、可继续评测的基础版本。它不是安全沙盒；本地记录也不是不可伪造的证明。请在可信项目运行，并由独立测试与人工评审判断最终正确性。
