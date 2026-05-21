# AWP Glossary

Last reviewed: 2026-05-20

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
