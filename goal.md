# AWP Workstation 最终实现方案

## Summary
AWP Workstation 最终形态是一个 **agent-native meta-skill**，不是浏览器产品。用户在 OpenClaw、Claude Code、Codex、Hermes 等 agent 里直接对话：`awp start` / `帮我用 AWP 工作赚钱`，Workstation 负责解释 AWP、完成 onboarding、扫描 WorkNet、安装子 skill、生成工作 playbook、组织长期运行、复盘收益与风险。

实现目标：用户不需要理解 RootNet、WorkNet、skillURI、epoch、CLOB、staking 等协议细节，只需要通过对话拥有一个会研究、会学习、会执行、会复盘的个人 AWP agent 工作站。

依据资料：AWP [whitepaper](https://awp.pro/awp-whitepaper.pdf)、[WorkNets](https://awp.pro/worknet)、[AIP-001 Mine](https://raw.githubusercontent.com/awp-core/AIPs/main/AIPS/aip-001.md)、[AIP-002 Predict](https://raw.githubusercontent.com/awp-core/AIPs/main/AIPS/aip-002.md)、[awp-skill](https://raw.githubusercontent.com/awp-core/awp-skill/main/README.md)、[Ardi skill](https://raw.githubusercontent.com/awp-worknet/ardi-skill/main/SKILL.md)、[KYA skill](https://raw.githubusercontent.com/awp-worknet/kya-skill/main/SKILL.md)、[Gov skill](https://raw.githubusercontent.com/awp-worknet/gov-skill/main/SKILL.md)。

## Key Changes
- 新建 `awp-workstation-skill`，作为总控 skill。
- 顶层入口使用 `SKILL.md`，触发词包括：`awp start`、`开始 AWP`、`帮我用 AWP 赚钱`、`workstation`、`研究 WorkNet`、`开始工作`。
- 内部脚本统一放在 `scripts/`，优先 Python 3，所有输出必须是 agent 可读 JSON。
- 本地状态统一保存在 `~/.awp-workstation/`，包括 worknet 扫描缓存、skill 安装状态、用户风险偏好、playbook、运行记录和 epoch 复盘。
- 浏览器只作为可选 companion，用于展示图表、日志、audit trail；所有核心流程必须能在纯 agent 对话中完成。

## Core Product Flow
- 用户说 `awp start` 后，Workstation 先用自然语言解释：AWP 是 agent 工作网络，Workstation 会帮用户注册、扫描机会、开始工作，不会要求私钥，资金动作会先确认。
- 运行 `preflight`：检查 `awp-wallet`、agent work wallet、AWP 注册状态、recipient/bind 状态、可用链、当前 agent 地址。
- 如果未注册，调用 `awp-skill` 的 gasless registration 流程；默认创建 agent work wallet，不导入用户个人钱包。
- 扫描 AWP JSON-RPC：`worknets.list`、`worknets.getSkills`、`tokens.getWorknetTokenPrice`、`staking.getAgentInfo`、`worknets.getEarnings`。
- 对每个 WorkNet 生成 `WorkNetCapabilityReport`：是否 active、skillURI 是否存在、是否官方源、min_stake、API/CLI 是否可用、是否能无 stake 开始、是否适合自动长期运行。
- 自动安装官方 `github.com/awp-worknet/*` skill；第三方 skill 必须提示风险并等待用户确认。
- 生成用户专属 `WorkPlaybook`，再启动对应工作循环。
- 每个 epoch 或任务窗口结束后生成复盘：收益、失败、风险、策略调整、下一步确认项。

## Public Interfaces And Types
- `scripts/workstation-preflight.py`  
  输入：无或 `--json`。输出：`walletReady`、`registered`、`agentAddress`、`recipient`、`nextAction`、`blockingIssues[]`。
- `scripts/scan-worknets.py`  
  输出 `WorkNetCapabilityReport[]`，字段固定为：`worknetId`、`name`、`symbol`、`status`、`skillsUri`、`officialSkill`、`minStake`、`runnable`、`automationLevel`、`riskLevel`、`recommendedRole`、`reason`。
- `scripts/build-playbook.py --worknet <id>`  
  输出 `WorkPlaybook`：`goal`、`role`、`loop`、`requiredSkill`、`commands[]`、`successMetrics[]`、`failureModes[]`、`humanConfirmations[]`。
- `scripts/run-workstation.py --mode autopilot`  
  读取 playbook，按 WorkNet 节奏执行；普通任务自动跑，资金和不可逆动作进入 confirmation queue。
- `scripts/review-epoch.py`  
  输出 `EpochReview`：`workDone[]`、`estimatedRewards[]`、`failures[]`、`strategyChanges[]`、`userActions[]`。

## WorkNet Behaviors
- Mine：默认作为第一优先级数据工作流。循环为 URL 发现、去重、crawl、clean、schema extract、submit、heartbeat；优化目标为 confirmed submissions、avg score、低重复率、低 IP decay。
- Predict：默认作为 reasoning/alpha 工作流。循环为读取 market context、拉取价格和外部信号、生成方向/limit price/tickets/reasoning、提交、追踪 chip excess；必须控制 reasoning 重复率和 rate limit。
- KYA：只作为一次性身份/attestation/delegated staking 工具，不进入循环运行。
- Ardi：按 epoch 事件运行，读谜题、选择最多 5 个高置信答案、commit、等待 reveal、inscribe；严格跟随 `ardi-agent` 的 `_internal.next_command`。
- Gov：按 phase 运行，支持 list/watch markets、vote、submit-order、monitor results；所有交易/投票类动作要求确认。
- TMR/Community 等 skill 信息不完整的 active WorkNet：只展示为“已发现但不可自动运行”，不强行执行。

## Safety And Confirmation Rules
- 永远不询问、不接收、不打印用户私钥、seed phrase、个人钱包密码。
- 默认使用 agent work wallet；提示用户不要存放个人资产。
- 所有链上交易、stake、allocate、deallocate、bind、set-recipient、delegate、claim、order、vote、transfer、inscribe 前必须展示 action、chain、target、预计成本和风险，并等待明确确认。
- gasless 免费注册可以自动执行，但仍需在对话里告知用户发生了什么。
- Workstation 不手写 calldata、不直接操作合约；所有 WorkNet 操作必须通过官方 skill/CLI 或 awp-skill 脚本。
- 第三方 skill 安装、非官方 API、长期守护进程、自动资金策略默认关闭，必须用户确认。

## Agent Orchestration
- `Protocol Analyst`：读取 AIP、SKILL.md、官网/API，生成 WorkNet 理解。
- `Skill Inspector`：安装 skill，跑 preflight/context/dry-run，判断可运行性。
- `Strategy Agent`：生成收益策略、任务选择策略、stake 使用建议。
- `Operator Agent`：执行 playbook，维护 heartbeat 和任务循环。
- `Risk Guardian`：拦截资金动作、权限风险、rate limit、封禁风险、异常收益假象。
- `Reporter`：把复杂日志翻译成用户能读懂的每日工作报告。

## User Experience
- 用户入口始终是对话，不要求打开网页。
- 输出格式固定为短进度条加自然语言解释，例如：`[3/5] WorkNet 扫描：发现 7 个 active，2 个可立即运行`。
- 推荐动作必须用人话表达：`建议先跑 Mine，同时让 Predict 观察 24 小时`，不要暴露协议细节作为主文案。
- 用户可随时说：`暂停`、`继续`、`只跑 Mine`、`不要动资金`、`今天赚了多少`、`为什么失败`、`换一个 WorkNet`。

## Test Plan
- Onboarding：无钱包、已有钱包、未注册、已注册、API 不可达、awp-wallet 缺失。
- WorkNet 扫描：active WorkNet、有官方 skill、无 SKILL.md、第三方 skill、min_stake > 0、Coordinator 不可达。
- Mine playbook：能生成完整 crawl/clean/extract/submit/heartbeat 流程，并正确识别 PoW、IP decay、quality gate 风险。
- Predict playbook：能生成 market/context/submit/reasoning/rate-limit 流程，并正确处理 reasoning quality gate。
- Safety：模拟 stake、allocate、vote、order、claim、transfer，确认全部进入 confirmation queue。
- Cross-runtime：在 Codex、Claude Code、OpenClaw/Hermes 风格环境里验证 `SKILL.md` 触发、JSON 输出、无浏览器依赖。
- Recovery：中断后从 `~/.awp-workstation/` 恢复 playbook、运行状态和待确认动作。
- Reporting：epoch 复盘必须包含工作量、估算收益、失败原因、策略调整和下一步用户动作。

## Assumptions And Defaults
- 默认产品本体是 `awp-workstation-skill`，不是 web app。
- 默认依赖 `awp-skill` 处理 AWP 注册、staking、allocation、worknet 查询。
- 默认只自动安装 `github.com/awp-worknet/*` 官方 skill。
- 默认先推荐可无 stake 运行的 WorkNet；staking 是增强项，不是入门前置条件。
- 默认长期运行只执行非资金类工作；所有资产相关动作必须确认。
- 默认浏览器 companion 不参与核心执行，只做可选可视化。
