# Deep Native v0.1 完整教程

本文中的终端命令是可执行接口；出现 `/deep-native` 的内容要输入 **Claude Code 会话**，而不是系统终端。使用 Python 3.10+ 和 Git，支持 macOS/Linux；原生 Windows 暂不支持运行时锁，请使用 WSL。

## 1. 先理解两个部分

**Skill** 是模型按需读取的工作流规范。它不能改变模型权重，也不保证模型每次都遵守。

**辅助 CLI** 是确定性程序：建立任务、保存进度、运行你指定的检查、记录证据、拒绝使用过期证据完成任务。它不调用模型，不改变你的 DeepSeek 连接，也不负责把不支持的协议字段变成可用能力。

推荐先在一个可丢弃的测试项目使用，再安装到正式项目。检查仓库脚本后再执行；本工具不是沙盒。

## 2. 下载并确认工具

```bash
git clone https://github.com/Anhao1314/deep-native.git
cd deep-native
python3 --version
git --version
python3 deep_native.py --version
```

最后一项应该显示 `0.1.0`。Python 版本需要至少 3.10。

```bash
python3 -m unittest discover -s tests -v
python3 examples/demo.py --output artifacts/demo
```

演示输出目录必须为空或不存在，避免覆盖之前的证据。重复运行时换个新目录，例如 `artifacts/demo-2`。macOS 用 `open artifacts/demo/demo.html` 打开；其他系统用浏览器打开该 HTML。

## 3. 演示具体看什么

| 步骤 | 实际执行内容 | 预期结果 |
| --- | --- | --- |
| 1–2 | 设置回归检查并创建任务 | CLI 退出码 0 |
| 3 | 对有错误的函数运行 3 个测试 | 测试失败，退出码 1 |
| 4 | 没有证据就调用 `finish` | 拒绝，退出码 2 |
| 5 | 执行 `verify` | 记录失败，退出码 1 |
| 6–7 | 脚本修复后保存进度，输入 compact 事件 | 返回检查点数据 |
| 8–9 | 相同 3 个测试及证据验证 | 实际通过 |
| 10 | 继续修改代码，再沿用旧证据完成 | 拒绝，退出码 2 |
| 11–12 | 对最新文件重新验证并交付 | 通过，明确未测模型能力 |

页面顶部的 `OFFLINE SCRIPTED EXPERIMENT` 不可删除或改成模型演示。修复是脚本写入的，Hook 是真实处理函数接收模拟宿主事件，不是一次真实 Claude Code 会话。`demo.json` 保留了逐步执行记录，临时路径已规范化。

## 4. 安装到自己的 Git 项目

保持终端当前目录为刚克隆的 `deep-native`。把 PROJECT 换成你真实项目的绝对路径，不能指向仓库内的某个子文件夹。

```bash
DN="$PWD/deep_native.py"
PROJECT="/absolute/path/to/your/project"
python3 "$DN" --project "$PROJECT" doctor
python3 "$DN" --project "$PROJECT" install
```

安装位置：

```text
你的项目/
└── .claude/skills/deep-native/
    ├── SKILL.md
    ├── references/
    └── scripts/deep_native.py
```

安装器不会改全局 `~/.claude`、不会设置 API Key、不会配置权限白名单。重复安装相同文件是幂等操作；发现内容不同的已有文件则拒绝，保留你的修改。

`doctor` 中 `credential_present=true` 仅表示环境里存在对应变量，**不代表余额足够、鉴权成功或模型兼容性已验证**。`claude_on_path=false` 表示当前终端找不到 CLI；本地测试仍可运行，但不能据此声称 Skill 已被宿主加载。

## 5. 保留现有 DeepSeek 配置

你已接通 DeepSeek 时无需重新配置。新接入用户先按 [DeepSeek 官方 Anthropic 兼容接口文档](https://api-docs.deepseek.com/guides/anthropic_api/) 及其 Claude Code 集成链接配置宿主。官方兼容基址是 `https://api.deepseek.com/anthropic`。

不要把 Key 放进本项目、`CLAUDE.md`、截图、Issue、聊天内容或命令参数。仅通过你本机已有的安全凭据机制/临时进程环境提供。不要为了本 Skill 开启 HTTP trace 或输出整个环境。

模型名称、上下文长度、effort 和兼容字段以当前供应商文档为准。本版不自动设置超大上下文、不强制 max effort，不通过模型别名暗中升级到更贵的模型。

## 6. 在 Claude Code 里使用

从你的目标项目启动或重启 Claude Code。输入：

```text
/deep-native 修复重试次数的边界问题。先检查实现和测试，复现错误，添加回归测试，以最小修改修复。交付时说明真正运行了什么、哪些没有验证。
```

首次使用时，模型应读取仓库规则、Git 状态和相关文件，确认实际检查命令，再创建任务。它不应该一上来修改许多无关文件，也不应该把 Skill 当成跳过权限的理由。

若 `/deep-native` 不出现，先检查 `.claude/skills/deep-native/SKILL.md` 的位置并重启，再对照 [Claude Code 官方 Skills 文档](https://code.claude.com/docs/en/skills)。不要用“安装器成功”替代“宿主真的加载成功”的验证。

## 7. 手动设置可靠的检查

下面是 Python unittest 项目的示例，不要原样用于没有 tests 目录的项目：

```bash
python3 "$DN" --project "$PROJECT" configure --name tests -- python3 -m unittest discover -s tests
```

Node 项目可以在检查过 package.json 脚本后设置：

```bash
python3 "$DN" --project "$PROJECT" configure --name tests -- npm test
python3 "$DN" --project "$PROJECT" configure --name build -- npm run build
```

这些例子二选一或按真实项目改写，不要把不存在的命令也加入。可以设置 1–16 个不同名称的检查，全部都要通过。命令是参数数组，不会自动经过 shell；`&&` 等字符不会被自动解释成串联命令。

配置保存在 `.deep-native.json`，建议人工审查后纳入 Git。任务开始时冻结其规范化哈希；任务中改动配置将使验证/完成被拒绝。需要变更检查时，先用明确原因 `block` 旧任务，再人工调整配置、创建新任务。不能删除失败检查来伪造成功。

建议在项目 `.gitignore` 中加入 `.deep-native/` 和真正的构建产物目录。不要把业务源码、回归测试或检查配置加入忽略列表来规避验证。

## 8. 任务生命周期

```bash
python3 "$DN" --project "$PROJECT" begin --goal "重试计数正确，现有行为不回归"
python3 "$DN" --project "$PROJECT" checkpoint --note "已经定位计数边界，添加了回归用例" --next "修正实现并运行检查"
python3 "$DN" --project "$PROJECT" status
python3 "$DN" --project "$PROJECT" verify --timeout 60
python3 "$DN" --project "$PROJECT" finish --summary "修复重试边界并通过配置的检查" --risk "尚未验证真实 API 超时"
```

实际编辑代码的步骤由你或 Agent 完成；这些命令不会自动替你修复代码。每个检查默认超时 60 秒，可设置为大于 0、最多 600 秒。超时会清理同一进程组，但这不能约束主动脱离进程组的恶意程序。

`verify` 保存退出码与耗时，不保存或显示测试 stdout/stderr。需要排错时，在检查过命令后单独运行原测试查看错误，再重新验证。

无法验证时应明确结束为阻塞：

```bash
python3 "$DN" --project "$PROJECT" block --reason "所需数据库不可用，集成测试尚未运行"
```

`blocked` 不等于 `complete`。进度保存在 `.deep-native/state.json`，检查记录在 `.deep-native/attempts/`。一个工作区同时只允许一个活跃任务，并发项目使用不同 Git worktree。

## 9. 可选 Hooks 与恢复

```bash
python3 "$DN" --project "$PROJECT" install --hooks
```

检查 `.claude/settings.local.json` 后重启 Claude Code。它只追加 Deep Native 的 SessionStart/Stop 命令，不覆盖其他设置。

Skill 创建任务时会传入 `${CLAUDE_SESSION_ID}`。Hook 只处理同一活跃会话；手工 `begin` 默认 session 为 `manual`，因此不会随意接管某个 Claude 会话。恢复到新会话时，先检查原任务，再在有意接续它的情况下使用 `adopt --session <实际新会话ID>`。

SessionStart 在匹配会话中返回简短进度。Stop 在没有当前证据时提醒继续验证；如果 `stop_hook_active=true`，会警告“仍未验证”并允许结束，防止死循环。Hook 异常也不会困住用户，但绝不因此产生成功结论。硬性完成检查仍是 `finish`。

官方 Hook 接口见 [Hooks reference](https://code.claude.com/docs/en/hooks)。本次开发只测试了这些 JSON 输入/输出契约，真实宿主生命周期尚待在有 Claude Code 的环境验收。

## 10. 升级与卸载

升级前先保存你自定义过的 Skill 文件。新版本安装器发现差异会拒绝覆盖；比较差异后，将原安装文件夹移到备份位置，再运行新版本 `install`。不要直接对正式项目使用强制覆盖脚本。

卸载时先在 `.claude/settings.local.json` 中移除指向 `deep-native/scripts/deep_native.py` 的 Hook 条目，保留所有其他条目，再删除或移走 `.claude/skills/deep-native/`，重启 Claude Code。

`.deep-native.json` 和 `.deep-native/` 不会自动删除，便于保留检查定义和证据。确认不再需要时再自行清理。不要为了卸载本 Skill 删除整个 `.claude` 目录。

## 11. 故障排查

| 表现 | 原因与处理 |
| --- | --- |
| `--project must be ... root` | 使用 Git 工作区根目录，不是源码子目录 |
| `No active task` | 先配置检查并 begin；旧任务可能已完成或阻塞 |
| `Worktree changed` | 上次验证后文件发生变化，重新验证 |
| `Check contract changed` | 任务中的检查清单被改动，不能继续使用旧约定 |
| verify 为失败，原测试单独运行却通过 | 检查环境只继承少量安全变量，或测试写了非忽略文件 |
| 命令需要 API Key | 默认不把模型凭据传给检查；设计本地测试或使用独立、受控的集成测试环境 |
| 子模块/大型工作区报错 | 当前不支持子模块；超过 20,000 文件、单文件 64 MiB 或总计 512 MiB 时明确拒绝 |
| Skill 已安装但质量没提升 | 安装不是效果保证；使用外部评测判断，不凭主观语气打分 |

## 12. 真正比较模型效果

见 [evals/README.md](../evals/README.md)。需要比较 DeepSeek 原始、同一 DeepSeek + Skill、明确版本的原生 Claude，在相同起点、权限、预算、任务和独立评分下重复运行。测试工具自身通过，不等于 DeepSeek 变强，也不等于省 token。
