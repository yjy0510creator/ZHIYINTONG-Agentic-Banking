# V3.1 策略版本绑定审计

结论：PASS（仅限本报告测试的本地模拟系统）。

原失败测试保持不变：`test_10_policy_version_change_invalidates_approval`、`test_11_approval_digest_binds_required_fields[policy_version-new-policy]`。旧 HTTP 证据位于 backend/test-results/final-security-audit：workflow=429949d1764e424ea2c5d0d5fc0e6027，5000100 分，旧版本审批后新版执行返回200 COMPLETED并写入一条模拟账本。原 plan_hash 忽略 policy_version，Checker 只保存 approved_hash；最终执行只复核当前 TrustEngine 规则，没有审批版本绑定。不是从报告推测根因。

修复调用链：POST /api/transactions → ExecutionGateway.prepare → 当前服务端策略 → 规范化金额（整数分）与计划摘要 → 沙箱 → PolicyService.seal → 不可更新/删除的 authorization_snapshots。客户端 TransactionRequest extra=forbid，不能传入或覆盖 policy_version。

快照字段：policy_version、policy_fingerprint、policy_generation、plan_hash、sandbox_run_id、sandbox_result_hash、transaction_amount（单位：分）、recipient、action_type、idempotency_key_hash、maker_id、workflow_id。authorization_digest 为该规范 JSON 的 SHA256；plan_hash 同时绑定 DAG、权限、风险标记和交易内容。见 [backend/services/policy_service.py:107](backend/services/policy_service.py#L107)。

policy_fingerprint 绑定 TrustEngine/网关/沙箱/策略服务源码 SHA256、运行时动作权限、连接器/对象白名单、HITL 阈值、MFA TTL、环境和模拟 MFA 开关。不是客户端字符串，也不是仅由版本字符串生成。policy_generation 防止版本回退后旧授权恢复。

每个授权阶段及执行前均调用 [backend/services/execution_gateway.py:104](backend/services/execution_gateway.py#L104)：比较当前注册策略、工作进程加载策略、原快照及其摘要；再核对 Maker/MFA/Checker 各自持久化的授权摘要。原沙箱内容摘要与计划摘要也必须一致。

策略激活见 [backend/services/policy_service.py:84](backend/services/policy_service.py#L84)：与资金写入共用 BEGIN IMMEDIATE 写锁，在同一事务内激活策略、撤销未完成工作流授权、写 policy_stale。状态 POLICY_STALE 不可恢复；旧 Maker/MFA/Checker 摘要清空，sandbox_valid=false。不可变原快照保留作为证据。必须创建新 workflow 和新幂等键，并重新完成所有授权。

初始化采用延迟方式：导入、健康检查、工作流只读查询、SSE重连不创建新策略记录、不迁移正式业务数据；首次授权变更/交易准备请求前进行服务端策略注册。没有新增对外策略更新接口。部署协调者也可在隔离/受控部署中调用 initialize/activate；客户不能激活策略。工作进程记录启动时观察到的注册版本；若延迟初始化时发现其他部署已激活新策略，不得回写旧策略，写操作失败关闭。

原子性：最终事务内读取策略及快照、重新评估 TrustEngine、核对 Maker/MFA（300秒有效期）、独立 supervisor 审批、幂等键、状态、沙箱、余额与保护性预留，然后才写 execution_started、账本、execution_completed、完成审计、工作流及幂等回执。任何审计插入失败都回滚。execute 成功的 api_request_completed 已从提交后的中间件移入事务，避免完成审计失败却已扣减的窗口。

并发语义：以数据库事务获得写锁并提交为线性化顺序。策略激活先获得锁时，旧执行等待后409；执行先合法提交时属于旧策略激活前完成的交易，后续策略变更不追溯撤销已提交模拟账本。不能把“同一时刻发送”误解为没有事务先后顺序。

完成后的同键请求只返回既有回执，不再次执行；策略/快照检查仍在缓存返回之前。已完成、已拒绝、失败的历史终态不被批量改写为未执行状态；没有新快照的旧未完成工作流必须重新创建。

证据：[负向报告](NEGATIVE_SECURITY_TEST_REPORT.md)、backend/test-results/v31-security/full/v31-policy-evidence、full/final-security-audit，及 v31-acceptance.xml。正式数据库未用于任何资金或授权测试。
