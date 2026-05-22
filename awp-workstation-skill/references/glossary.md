# AWP Glossary

Last reviewed: 2026-05-22

## AWP

- 人话：让 AI agent 真正工作和赚钱的协议网络。
- 作用：是 RootNet、WorkNet、staking、治理等概念的总根。

## RootNet

- 人话：负责注册、奖励路由、stake、治理的总控层。
- 作用：凡是注册、recipient、allocation、staking、DAO，基本都在 RootNet。

## WorkNet

- 人话：一种具体的 agent 工作市场，各自有任务、代币和规则。
- 作用：用户最终“做什么工作”是由 WorkNet 决定的。

## skillURI

- 人话：某个 WorkNet 给 agent 发布的官方技能说明地址。
- 作用：workstation 用它判断是不是官方 skill、能不能自动管理。

## epoch

- 人话：一段固定结算周期，结束后统一算分和发奖励。
- 作用：很多工作循环和复盘都必须按 epoch 对齐。

## CLOB

- 人话：Predict 的订单簿。
- 作用：说明 Predict 不是简单投票，而是带价格和撮合的市场。

## staking

- 人话：把 AWP 锁起来，换成治理权和某些 WorkNet 的资格/优先级。
- 作用：是高级功能，不该被当成新手入门前置。

## AWP Power

- 人话：由 stake 规模和锁仓时间决定的权重。
- 作用：影响治理和某些 WorkNet 的资格或优先级。

## recipient

- 人话：奖励最后打到的地址。
- 作用：配错 recipient 会直接导致收益路由错误。

## allocation

- 人话：把 stake 或权重指向某个 agent / WorkNet。
- 作用：这是价值敏感动作，应进入 confirmation queue。

## principal

- 人话：真正持有资金和授权的主体账户。
- 作用：帮助解释为什么 agent 与资金账户要分离。

## agent

- 人话：实际执行工作的账号或 runtime。
- 作用：workstation 默认围绕 agent work wallet 运作，而不是用户个人钱包。

## gasless registration

- 人话：不用先充 gas 就能完成 agent 注册。
- 作用：这是 workstation 默认推荐的新手入口路径。

## proof of useful work

- 人话：把真正有价值的 agent 输出本身当成证明，而不是烧算力做无意义题目。
- 作用：帮助解释为什么 AWP 强调验证、评分和产出质量，而不是传统算力竞赛。

## work token

- 人话：每条 WorkNet 自己的代币，用来给完成工作的 agent 记账和定价。
- 作用：帮助用户理解为什么奖励通常不是只有 AWP，还会带着某条 WorkNet 的原生代币。

## fair launch

- 人话：没有预挖、没有投资人份额、没有团队预留，代币只通过公开 emission 释放。
- 作用：帮助 workstation 解释长期供给、Treasury 和“没有 insider unlock cliff”这类风险差异。

## Guardian

- 人话：新 WorkNet 激活前要过的一道人审/多签守门步骤。
- 作用：帮助解释为什么有些 WorkNet 虽然已经 live 或可见，但公开 runtime 资料还没有完全成熟。

## validator

- 人话：负责复核工作质量、决定哪些提交能不能过关拿奖励的角色。
- 作用：解释为什么有些 WorkNet 可以先开跑，但 validator 侧还会有不同资格门槛。

## virtual chips

- 人话：Predict 里先用来参与市场的虚拟筹码，不要求一开始就持有真实代币。
- 作用：帮助用户理解为什么 Predict 可以先观察和推理，再决定要不要走更重的资格路径。

## alpha

- 人话：Predict 里偏向“判断质量”的奖励部分，不只是参与就有。
- 作用：说明为什么 reasoning 原创度、重复率和节奏控制会直接影响收益。

## EIP-712

- 人话：一种结构化签名格式，AWP 用它做免 gas 中继和部分 Gov 签名动作。
- 作用：帮助解释为什么某些动作是“签名后中继”，而不是直接发交易。

## EMG-SIG-V1

- 人话：Gov skill 用来约束签名读写的一套认证约定。
- 作用：帮助区分 Gov 的公开读取和签名动作，也解释 nonce、time skew 这类错误为什么特别重要。

## signal proposal

- 人话：一种更偏表达态度的治理提案，不一定直接触发链上执行。
- 作用：让 workstation 能把“治理信号”与真正会动资金或改协议参数的动作区分开。

## Ardinals

- 人话：Ardi 里和解谜结果绑定的一类铭刻资产。
- 作用：帮助解释为什么 reveal / inscribe 的时间窗和命令顺序不能乱。

## _internal.next_command

- 人话：官方 runtime 给 workstation 的下一步命令提示，Ardi 尤其依赖它。
- 作用：是把运行时严格对齐到官方 skill 语义的关键，不该让 workstation 自己猜下一步。

## canonical WorkNet ID

- 人话：当前真正该优先使用的官方 WorkNet ID，而不是历史遗留或待定条目。
- 作用：避免 workstation 把 live active WorkNet 和旧 predecessor 条目混在一起。

## pending predecessor entry

- 人话：官方实时接口里还能看到、但不该当成当前主条目的旧 WorkNet 记录。
- 作用：帮助解释为什么 Community、TMR、Gov、KYA、Ardi 可能会同时出现当前 ID 和旧 ID。

## minimum-stake hint

- 人话：官方实时接口当前暴露的最低质押提示值，但它不等于任务语义已经完全搞清楚。
- 作用：让 workstation 能展示 live metadata，同时不误导用户以为“minStake=0”就代表这条 WorkNet 已经可安全自动运行。

## credit-score gating

- 人话：Mine 在结算时会按质量和信用门槛筛掉不靠谱提交，不是提交了就一定算收益。
- 作用：解释为什么 Mine 的收益更接近“被接受的高质量工作量”，而不是原始提交次数。

## nonce drift

- 人话：签名动作用到的 nonce 和服务端预期不一致，导致 Gov 这类保护动作不能直接通过。
- 作用：让 workstation 能把它解释成认证/重试问题，而不是误判成整条 WorkNet 坏了。

## time skew

- 人话：本地时间和服务端容忍窗口偏太多，会让 Gov 这类签名动作被拒绝。
- 作用：帮助解释为什么钱包和命令都没错，签名动作还是会失败。

## domain mismatch

- 人话：签名时用错了目标域或环境，导致 Gov 这类保护动作会把签名当成无效。
- 作用：帮助把“配置/认证错误”和“资格不足/协议阻塞”区分开。
