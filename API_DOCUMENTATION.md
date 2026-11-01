# API 接口与事件
以运行实例 GET /openapi.json 为精确 Schema。金额字符串单位为元，内部整数分；幂等键为 UUID。除健康/OpenAPI/开发登录等公开入口外，受保护请求需 Authorization: Bearer 本机临时会话。角色由服务端决定。

|接口|方法与关键请求|作用|
|---|---|---|
|/api/dev/login|POST username,password|仅development固定账号，返回临时token；不得公开|
|/api/session|GET|查询服务端身份|
|/api/analyze|POST prompt, scenario_key(可选)|生成任务、DAG与卡片，返回202|
|/api/transactions|POST action,amount,recipient,idempotency_key|建立独立交易工作流，返回201|
|/api/workflows/{id}|GET|当前服务端状态|
|/api/workflows/{id}/maker-confirm|POST confirmed:true|Maker确认同一快照|
|/api/workflows/{id}/mfa/verify|POST method:"simulated_face",consent:true|开发模拟MFA，300秒有效|
|/api/workflows/{id}/submit-review|POST 空对象|大额提交Checker复核|
|/api/workflows/{id}/human-review|POST decision,reason,plan_hash|独立supervisor审批，decision为APPROVE或REJECT|
|/api/workflows/{id}/execute|POST idempotency_key|原子核验并仅模拟执行|
|/api/simulation/account|GET|当前主体模拟账户|
|/api/audit-logs|GET limit,cursor,workflow_id,actor_id,permission_level,status|结构化审计，权限过滤|
|/api/audit-stream|GET cursor,workflow_id|SSE audit_event|
|/api/workflows/{id}/stream|GET cursor|持久化工作流事件流|
|/api/stream/{task_id}|GET|Agent/DAG校验进度|

允许对象：transfer.simulate→demo-recipient；wealth.subscribe→P01/P02/P03；card.freeze→demo-card；subscription.cancel→S01/S02/S03/S04。真实transfer.execute禁止。

状态：SANDBOX_PASSED→AWAITING_MAKER_MFA→APPROVED（小额）或PENDING_HUMAN_REVIEW→AWAITING_CHECKER→APPROVED/REJECTED。最终COMPLETED仅表示模拟完成。策略变化→POLICY_STALE，重新创建交易，不在原工作流恢复。

403授权拒绝；409状态/快照/幂等冲突；422字段错误；503审计不可用或生产IdP未配置。拒绝不得产生资金分录。HTTP证据见 evidence/policy-http，未包含登录口令或Bearer令牌。

SSE审计数据含event_id/timestamp/action/actor_id/permission_level/status/duration_ms/workflow_id。task节点事件是SCHEMA_POLICY_VALIDATION，不是execution_started。RED ALLOW也是局部策略判定，不能直接视为最终交易许可。
