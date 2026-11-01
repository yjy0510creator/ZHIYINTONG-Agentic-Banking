# V3.1 架构
React/Next.js → FastAPI → MasterOrchestrator → DomainAgent → Financial IR/DAG/业务卡片。
独立写操作 → ExecutionGateway → 策略快照/TrustEngine → Idempotency → Sandbox → Maker/MFA → Checker（金额>50000）→ 模拟账本与审计原子提交。

主控以场景与关键词路由；六个主要领域技能为旅游、转账、账单、理财、卡片和订阅，另有异常/通用回退。不是多个LLM自由协商。

SQLite 表：workflows、sessions、simulated_accounts、simulated_entries、simulated_objects、idempotency_records、audit_events、decision_documents、financial_scenarios、active_policy、authorization_snapshots。确切DDL见 backend/services/database.py、audit_service.py、idempotency_service.py、intelligence.py、policy_service.py。

策略快照封装交易、Maker、幂等键摘要、版本、指纹、代次和沙箱结果。所有授权绑定同一摘要；变化后 POLICY_STALE 不能恢复。BEGIN IMMEDIATE 使策略激活与资金提交共享写锁。当前无公开策略更新HTTP接口，部署激活属于服务端内部控制。

任务 EventBus 在内存中；审计及决策回放持久化。SSE不能提供生产级跨节点消息持久性。银行连接仅Mock/模拟，真实 transfer.execute 被阻断。
