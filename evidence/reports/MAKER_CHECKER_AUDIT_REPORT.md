# V3.1 Maker-Checker 审计报告

结论：PASS（开发身份与独立模拟账本范围）。

金额严格大于50000元强制 PENDING_HUMAN_REVIEW → AWAITING_CHECKER；50001元属于该范围。Maker确认、模拟MFA、提交、独立supervisor审批、最终执行均重新验证同一授权快照。

Checker持久化 checker_id、checker_role、approved_authorization_digest、approved_policy_version、approved_policy_fingerprint、approved_plan_hash、approved_at。执行时逐一比较，不能仅凭 approved=true 或 plan_hash 放行。Maker与Checker必须是不同主体；角色来自服务端 AuthService 会话，非客户端字段。

兼容既有UI：审批请求继续提交plan_hash；它包含workflow_id、交易内容和策略身份，服务端将其解析到该工作流唯一且不可更新的快照，再保存完整approved_authorization_digest及版本/指纹。客户端不能选择另一沙箱结果或替换快照；execute仍只接受原幂等键，最终授权依据来自服务端持久化记录。

证据覆盖：原基础测试自批/普通用户/独立主管/拒绝终态，原最终审计 test_09 独立令牌与伪造头/字段，新 test_maker_self_approval、test_checker_different_transaction、test_old_approval_digest、test_expired_mfa；版本变化后重批、重新确认、旧幂等键重放均拒绝。具体 HTTP 及审计 ID 见 [负向测试报告](NEGATIVE_SECURITY_TEST_REPORT.md)。

源码：backend/services/auth_service.py（未修改），[backend/services/execution_gateway.py:104](backend/services/execution_gateway.py#L104)，backend/services/execution_gateway.py 的 maker_binding 和 APPROVE/REJECT 分支。

限制：不同的服务端开发账户/凭据/会话已验证；不能据此证明两个自然人或真实组织岗位隔离。真实生产 IdP、真实生物识别、真实银行资金交易均不在本次范围，NOT VERIFIED。生产未配置 IdP 时继续拒绝，开发 MFA 仍明确标为模拟。
