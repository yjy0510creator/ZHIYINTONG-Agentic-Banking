from __future__ import annotations

import asyncio
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Permission = Literal["GREEN", "YELLOW", "RED"]
Scenario = Literal["travel", "transfer", "bills", "wealth", "card", "subscriptions", "anomaly", "general"]
CardType = Literal[
    "travel_sandbox", "transfer_form", "bill_chart", "wealth_products",
    "card_freeze", "subscription_list", "security_alert", "summary_card"
]


class SandboxCardMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    currency: str = "CNY"
    current_balance: float
    mortgage_reserve: float
    daily_expense_reserve: float
    minimum_liquidity_reserve: float
    available_after_protected_reserves: float
    safe_travel_budget: float
    investable_surplus: float
    cashflow_safe: bool
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    calculation_note: str | None = None


class TransferFormData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipient_name: str
    recipient_masked: str
    recipient_avatar: str = "收"
    amount: float = Field(ge=0)
    currency: str = "CNY"
    risk_tags: list[str] = Field(default_factory=list)
    status: Literal["BLOCKED", "PENDING"] = "BLOCKED"
    status_text: str
    reason: str
    action_label: str
    disclaimer: str


class BillChartItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    value: float = Field(ge=0)
    color: str | None = None


class BillChartData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period: str
    items: list[BillChartItem]
    total: float = Field(ge=0)
    transaction_count: int = Field(ge=0)
    source_label: str


class CardFreezeData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    brand: str
    masked_number: str
    status: Literal["NORMAL", "FROZEN"]
    cardholder: str
    action_label: str
    note: str


class WealthProduct(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    risk: str
    risk_text: str
    term: str
    note: str


class WealthProductsData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    risk_profile: str
    products: list[WealthProduct]
    action_label: str


class SubscriptionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    vendor: str
    amount: float = Field(ge=0)
    cycle: str
    next: str


class SubscriptionListData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[SubscriptionItem]
    monthly_total: float = Field(ge=0)
    note: str


class TravelSandboxData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sandbox: SandboxCardMetrics
    note: str


class SecurityAlertData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["BLOCKED", "REVIEW"]
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    reason: str
    message: str
    action_label: str | None = None


class SummaryCardData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str
    source_label: str


class UIBusinessCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    card_id: str = Field(min_length=1, max_length=64)
    card_type: CardType
    title: str = Field(min_length=1, max_length=100)
    permission_level: Permission
    data: dict[str, Any]

    @field_validator("data")
    @classmethod
    def validate_card_payload(cls, value: dict[str, Any], info):
        card_type = info.data.get("card_type")
        models = {
            "travel_sandbox": TravelSandboxData,
            "transfer_form": TransferFormData,
            "bill_chart": BillChartData,
            "wealth_products": WealthProductsData,
            "card_freeze": CardFreezeData,
            "subscription_list": SubscriptionListData,
            "security_alert": SecurityAlertData,
            "summary_card": SummaryCardData,
        }
        model = models.get(card_type)
        if model is None:
            raise ValueError("Unsupported card_type")
        return model.model_validate(value).model_dump()


class AuthorizationContext(BaseModel):
    """Three-principal delegation context: human -> agent -> connector."""
    human_subject: str = "demo-user"
    agent_subject: str = "zhiyintong-master-agent"
    connector_subject: str = "zhiyintong-mock-bank-connector"
    session_id: str = "zhiyintong-web-demo"
    delegated_scopes: list[str] = Field(default_factory=lambda: [
        "account.read", "bills.read", "cards.read", "transfer.preview", "wealth.read",
        "plan.confirm", "subscription.cancel", "card.freeze", "wealth.subscribe", "transfer.simulate",
    ])


class TrustDecision(BaseModel):
    decision: Literal["ALLOW", "REQUIRE_CONFIRMATION", "REQUIRE_MFA", "BLOCK"]
    permission_level: Permission
    reason: str
    simulated_only: bool = True
    policy_version: str = "trust-engine-3.0"


class TrustEngine:
    """Deterministic runtime gate. LLM output never determines permissions."""

    ACTION_LEVELS: dict[str, Permission] = {
        "account.read": "GREEN",
        "bills.read": "GREEN",
        "cards.read": "GREEN",
        "transfer.preview": "GREEN",
        "wealth.read": "GREEN",
        "plan.confirm": "YELLOW",
        "subscription.cancel": "YELLOW",
        "card.freeze": "RED",
        "wealth.subscribe": "RED",
        "transfer.execute": "RED",
        "transfer.simulate": "RED",
    }

    ALLOWED_CONNECTORS = {"zhiyintong-mock-bank-connector"}

    def authorize(self, action, context=None, **kwargs):
        from services.auth_service import current_actor
        actor = current_actor.get()
        ctx = context or AuthorizationContext()
        if actor:
            ctx = ctx.model_copy(update={"human_subject": actor.actor_id, "session_id": actor.session_id})
        started = time.perf_counter()
        decision = self._authorize(action, ctx, **kwargs)
        if actor:
            from services.api_v3 import audit
            from services.intelligence import trace_workflow
            audit.append(actor, "trust_decision", workflow_id=trace_workflow.get(), permission_level=decision.permission_level,
                         status=decision.decision, reason=decision.reason,
                         duration_ms=(time.perf_counter()-started)*1000,
                         metadata={"action": action, "connector": ctx.connector_subject,
                                   "decision_scope": "TRUST_POLICY_ONLY",
                                   "execution_authorized": False,
                                   "note": "局部策略判断，不代表通过沙箱/双人审批；执行许可仅由 ExecutionGateway 最终判定。"})
        return decision

    def _authorize(
        self,
        action: str,
        context: AuthorizationContext | None = None,
        *,
        user_confirmed: bool = False,
        mfa_verified: bool = False,
        risk_flags: list[str] | None = None,
        simulation_only: bool = True,
    ) -> TrustDecision:
        ctx = context or AuthorizationContext()
        level = self.ACTION_LEVELS.get(action)
        if level is None:
            return TrustDecision(decision="BLOCK", permission_level="RED", reason="工具动作不在白名单中。")
        if not ctx.human_subject or not ctx.session_id:
            return TrustDecision(decision="BLOCK", permission_level=level, reason="缺少发起用户或会话主体。")
        if ctx.agent_subject != "zhiyintong-master-agent":
            return TrustDecision(decision="BLOCK", permission_level=level, reason="Agent 身份不受信任。")
        if ctx.connector_subject not in self.ALLOWED_CONNECTORS:
            return TrustDecision(decision="BLOCK", permission_level=level, reason="连接器身份不在白名单中。")
        flags = set(risk_flags or [])
        if action == "transfer.execute":
            reason = "本演示环境不开放任何真实转账写操作；当前转账任务只允许预览与风控拦截。"
            if {"new_recipient", "large_amount"}.issubset(flags):
                reason = "陌生收款方与大额交易风险同时命中；即使 MFA 通过，本演示策略仍保持 RED 拦截。"
            return TrustDecision(decision="BLOCK", permission_level="RED", reason=reason)
        if action not in ctx.delegated_scopes:
            return TrustDecision(decision="BLOCK", permission_level=level, reason="当前用户会话未委托该项能力。")
        if level == "GREEN":
            return TrustDecision(decision="ALLOW", permission_level=level, reason="只读或确定性计算动作通过。")
        if not user_confirmed:
            return TrustDecision(decision="REQUIRE_CONFIRMATION", permission_level=level, reason="需要用户对本次具体动作进行明确确认。")
        if level == "RED" and not mfa_verified:
            return TrustDecision(decision="REQUIRE_MFA", permission_level=level, reason="RED 动作必须完成独立 MFA。")
        if not simulation_only:
            return TrustDecision(decision="BLOCK", permission_level=level, reason="当前系统仅允许模拟连接器，不允许真实资金写操作。")
        return TrustDecision(decision="ALLOW", permission_level=level, reason="授权条件满足；仅允许更新本地模拟状态。")


class SecurityGuardrail:
    """Five-plane guardrail support: input, identity, network, endpoint and data."""

    INJECTION_PATTERNS = [
        r"忽略.{0,12}(之前|以上|先前|所有).{0,12}(规则|指令|系统提示)",
        r"绕过.{0,8}(安全|权限|网关|mfa|验证|审批)",
        r"泄露.{0,10}(系统提示词|system prompt|api.?key|密钥|secret)",
        r"越权转账",
        r"ignore\s+(all\s+)?(previous|prior)\s+(rules|instructions)",
        r"reveal\s+(the\s+)?(system prompt|api key|secret)",
        r"bypass\s+(security|authorization|mfa|approval)",
    ]

    @classmethod
    def inspect_prompt(cls, prompt: str) -> str | None:
        normalized = unicodedata.normalize("NFKC", prompt or "")
        normalized = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", normalized)
        normalized = normalized[:4000]
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, normalized, flags=re.IGNORECASE | re.DOTALL):
                return "检测到疑似提示词注入、越权授权或安全边界绕过请求。"
        return None

    @classmethod
    def mask_pii(cls, value: Any) -> Any:
        if isinstance(value, str):
            text = value
            text = re.sub(r"(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)", r"\1****\2", text)
            text = re.sub(r"(?<!\d)(\d{6})\d{8}(\d{3}[\dXx])(?!\d)", r"\1********\2", text)
            text = re.sub(r"(?<!\d)(\d{6})\d{6,9}(\d{4})(?!\d)", r"\1 **** **** \2", text)
            return text
        if isinstance(value, list):
            return [cls.mask_pii(item) for item in value]
        if isinstance(value, dict):
            return {key: cls.mask_pii(item) for key, item in value.items()}
        return value


@dataclass
class _TaskStream:
    events: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    created_at: float = field(default_factory=time.time)


class TaskEventBus:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._tasks: dict[str, _TaskStream] = {}
        self._lock = asyncio.Lock()

    async def create(self, task_id: str | None = None) -> str:
        task_id = task_id or uuid.uuid4().hex
        async with self._lock:
            self._cleanup_locked()
            self._tasks[task_id] = _TaskStream()
        return task_id

    def _cleanup_locked(self) -> None:
        now = time.time()
        for key in [k for k, v in self._tasks.items() if now - v.created_at > self.ttl_seconds]:
            self._tasks.pop(key, None)

    def exists(self, task_id: str) -> bool:
        state = self._tasks.get(task_id)
        return bool(state and time.time() - state.created_at <= self.ttl_seconds)

    async def publish(self, task_id: str, event_name: str, data: dict[str, Any]) -> None:
        state = self._tasks.get(task_id)
        if state is None:
            await self.create(task_id)
            state = self._tasks[task_id]
        safe_data = SecurityGuardrail.mask_pii(data)
        from services.intelligence import persist_bus_event
        persist_bus_event(task_id,event_name,safe_data)
        async with state.condition:
            state.events.append({"id": len(state.events) + 1, "event": event_name, "data": safe_data})
            state.condition.notify_all()

    async def finish(self, task_id: str) -> None:
        state = self._tasks.get(task_id)
        if not state:
            return
        async with state.condition:
            state.done = True
            state.condition.notify_all()

    async def stream(self, task_id: str, last_event_id: int = 0):
        state = self._tasks.get(task_id)
        if state is None or time.time() - state.created_at > self.ttl_seconds:
            raise KeyError(task_id)
        cursor = max(0, int(last_event_id or 0))
        while True:
            batch: list[dict[str, Any]] = []
            heartbeat = False
            async with state.condition:
                if cursor >= len(state.events) and not state.done:
                    try:
                        await asyncio.wait_for(state.condition.wait(), timeout=15)
                    except asyncio.TimeoutError:
                        heartbeat = True
                batch = state.events[cursor:]
                cursor += len(batch)
                finished = state.done and cursor >= len(state.events)
            if heartbeat and not batch:
                yield None
            for event in batch:
                yield event
            if finished:
                break


event_bus = TaskEventBus()
trust_engine = TrustEngine()
security_guardrail = SecurityGuardrail()


class MasterOrchestrator:
    SCENARIO_MAP = {
        "travel": "travel_planning",
        "transfer": "transfer_security",
        "bills": "bill_analysis",
        "wealth": "wealth_management",
        "card": "card_management",
        "subscriptions": "subscription_management",
        "anomaly": "anomaly_detection",
        "general": "general",
    }

    @classmethod
    def classify(cls, prompt: str, scenario_key: str | None = None) -> Scenario:
        if scenario_key in cls.SCENARIO_MAP:
            return scenario_key  # type: ignore[return-value]
        text = (prompt or "").lower()
        if any(k in text for k in ("旅游", "旅行", "出行资金", "旅游预算", "资金规划")):
            return "travel"
        if any(k in text for k in ("转账", "陌生账户", "收款方", "反诈", "转账防诈")):
            return "transfer"
        if any(k in text for k in ("账单", "消费", "支出占比", "流水分析")):
            return "bills"
        if any(k in text for k in ("理财", "申购", "投资产品")):
            return "wealth"
        if any(k in text for k in ("挂失", "银行卡", "卡片", "冻结")):
            return "card"
        if any(k in text for k in ("订阅", "周期扣费", "自动扣费")):
            return "subscriptions"
        if any(k in text for k in ("异常交易", "重复扣款", "可疑消费")):
            return "anomaly"
        return "general"

    @classmethod
    def analysis_type(cls, scenario: Scenario) -> str:
        return cls.SCENARIO_MAP[scenario]


class MockBankConnector:
    """MCP-facing connector. All records are synthetic; no bank network is contacted."""

    def __init__(self):
        self.account = {
            "currency": "CNY", "current_balance": 10000,
            "mortgage_reserve": 3000, "daily_expense_reserve": 2000,
            "minimum_liquidity_reserve": 1000, "account_label": "演示账户"
        }
        self.card = {"brand": "ZHIYINTONG", "masked_number": "6222 **** **** 4826", "status": "NORMAL"}

    def account_overview(self) -> dict[str, Any]:
        return dict(self.account)

    def spending_summary(self) -> list[dict[str, Any]]:
        return [
            {"name": "房贷", "value": 3000, "color": "#6f91c9"},
            {"name": "餐饮", "value": 1800, "color": "#83bca5"},
            {"name": "购物", "value": 1200, "color": "#b6a6d8"},
            {"name": "出行", "value": 900, "color": "#e4c27e"},
            {"name": "日常缴费", "value": 800, "color": "#8fb7d7"},
            {"name": "其他", "value": 500, "color": "#c5cdd7"},
        ]

    def card_status(self) -> dict[str, Any]:
        return dict(self.card)

    def wealth_products(self) -> list[dict[str, Any]]:
        return [
            {"id": "P01", "name": "安心现金管理", "risk": "R1", "risk_text": "低风险", "term": "灵活期限", "note": "侧重流动性管理，仅用于演示。"},
            {"id": "P02", "name": "稳健固收组合", "risk": "R2", "risk_text": "中低风险", "term": "90 天示例期限", "note": "仍存在净值波动可能。"},
            {"id": "P03", "name": "短期债券精选", "risk": "R2", "risk_text": "中低风险", "term": "180 天示例期限", "note": "不代表真实可购买产品。"},
        ]


mock_bank_connector = MockBankConnector()


class MCPConnectorGateway:
    """In-process adapter for the same MCP tool contracts exposed at /mcp/."""
    READ_TOOLS = {
        "account.get_overview": ("account.read", mock_bank_connector.account_overview),
        "bills.get_spending_summary": ("bills.read", mock_bank_connector.spending_summary),
        "cards.get_status": ("cards.read", mock_bank_connector.card_status),
        "wealth.list_products": ("wealth.read", mock_bank_connector.wealth_products),
    }

    TOOL_MANIFEST = [
        {"name": "account.get_overview", "description": "读取脱敏演示账户概览", "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
        {"name": "bills.get_spending_summary", "description": "读取分类模拟消费数据", "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
        {"name": "cards.get_status", "description": "读取脱敏虚拟卡片状态", "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
        {"name": "wealth.list_products", "description": "读取演示理财产品目录", "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    ]

    def call_read_tool(self, name: str, context: AuthorizationContext | None = None) -> Any:
        entry = self.READ_TOOLS.get(name)
        if entry is None:
            raise PermissionError("MCP read tool is not in the allowlist")
        action, handler = entry
        decision = trust_engine.authorize(action, context or AuthorizationContext())
        if decision.decision != "ALLOW":
            raise PermissionError(decision.reason)
        from services.intelligence import trace
        trace("mcp_tool_called", {"tool":name,"read_only":True})
        return handler()


mcp_connector_gateway = MCPConnectorGateway()


def build_security_card(reason: str) -> dict[str, Any]:
    return UIBusinessCard(
        card_id="security-defense",
        card_type="security_alert",
        title="安全网关 · 防御拦截",
        permission_level="RED",
        data={
            "status": "BLOCKED",
            "severity": "HIGH",
            "reason": reason,
            "message": "该请求未进入金融任务编译器，未调用任何银行连接器或资金写操作。",
            "action_label": "查看安全审计",
        },
    ).model_dump()


def build_business_cards(scenario: Scenario, metrics: dict[str, Any]) -> list[dict[str, Any]]:
    if scenario == "travel":
        return [UIBusinessCard(
            card_id="travel-sandbox",
            card_type="travel_sandbox",
            title="跨场景资金沙盘",
            permission_level="GREEN",
            data={"sandbox": metrics, "note": "先保护固定支出与最低流动性，再计算可用旅游预算。"},
        ).model_dump()]
    if scenario == "transfer":
        return [UIBusinessCard(
            card_id="transfer-risk-form",
            card_type="transfer_form",
            title="转账风险确认单",
            permission_level="RED",
            data={
                "recipient_name": "陌生收款方（演示）",
                "recipient_masked": "6222 **** **** 8261",
                "recipient_avatar": "陌",
                "amount": 8800,
                "currency": "CNY",
                "risk_tags": ["新收款方", "金额偏离", "高风险交易"],
                "status": "BLOCKED",
                "status_text": "已暂停 · 等待独立核验",
                "reason": "收款方不在常用名单，且本次金额高于演示风险阈值。",
                "action_label": "申请身份核验（仍保持拦截）",
                "disclaimer": "身份核验不代表转账放行；本系统不会执行真实资金转移。",
            },
        ).model_dump()]
    if scenario == "bills":
        items = mcp_connector_gateway.call_read_tool("bills.get_spending_summary")
        total = sum(item["value"] for item in items)
        return [UIBusinessCard(
            card_id="monthly-bill-chart",
            card_type="bill_chart",
            title="消费账单 · 分类洞察",
            permission_level="GREEN",
            data={"period": "本期演示账期", "items": items, "total": total, "transaction_count": 28, "source_label": "本地固定模拟流水"},
        ).model_dump()]
    if scenario == "wealth":
        products = mcp_connector_gateway.call_read_tool("wealth.list_products")
        return [UIBusinessCard(card_id="wealth-products", card_type="wealth_products", title="稳健理财 · 产品预评估", permission_level="GREEN", data={"risk_profile": "稳健型（演示）", "products": products, "action_label": "选择产品并发起独立 MFA"}).model_dump()]
    if scenario == "card":
        card = mcp_connector_gateway.call_read_tool("cards.get_status")
        return [UIBusinessCard(card_id="virtual-card-control", card_type="card_freeze", title="虚拟银行卡 · 安全管理", permission_level="RED", data={**card, "cardholder": "DEMO USER", "action_label": "发起挂失保护", "note": "仅改变本地模拟状态，不连接真实银行。"}).model_dump()]
    if scenario == "subscriptions":
        items = [
            {"id": "S01", "name": "影音会员", "vendor": "星河视频", "amount": 25, "cycle": "每月 08 日", "next": "11 月 08 日"},
            {"id": "S02", "name": "云空间服务", "vendor": "云端存储", "amount": 18, "cycle": "每月 12 日", "next": "11 月 12 日"},
            {"id": "S03", "name": "音乐会员", "vendor": "声波音乐", "amount": 15, "cycle": "每月 18 日", "next": "11 月 18 日"},
            {"id": "S04", "name": "健身服务", "vendor": "悦动健身", "amount": 99, "cycle": "每月 26 日", "next": "11 月 26 日"},
        ]
        return [UIBusinessCard(card_id="subscription-list", card_type="subscription_list", title="订阅扣费 · 周期管理", permission_level="YELLOW", data={"items": items, "monthly_total": sum(x["amount"] for x in items), "note": "取消仅更新本地演示清单，不会联系真实商户。"}).model_dump()]
    if scenario == "anomaly":
        return [UIBusinessCard(card_id="anomaly-alert", card_type="security_alert", title="消费异常 · 待核查提醒", permission_level="YELLOW", data={"status": "REVIEW", "severity": "LOW", "reason": "固定演示样本中发现 1 项低风险待核查候选。", "message": "系统仅生成提醒，不自动冻结账户或发起拒付。"}).model_dump()]
    return [UIBusinessCard(card_id="assistant-summary", card_type="summary_card", title="金融助手分析建议", permission_level="GREEN", data={"message": "请描述资金规划、账单、卡片或订阅方面的具体目标。", "source_label": "智银通演示智能体"}).model_dump()]


def build_domain_nodes(scenario: Scenario, metrics: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if scenario == "travel":
        specs = [
            ("N01", "解析金融意图", "parse_intent", "GREEN", 0, "summary_card"),
            ("N02", "查询账户余额", "query_balance", "GREEN", 1, "summary_card"),
            ("N03", "查询房贷计划", "query_mortgage", "GREEN", 1, "summary_card"),
            ("N04", "分析日常开销", "analyze_daily_expenses", "GREEN", 1, "bill_chart"),
            ("N05", "提取旅游目标", "extract_travel_parameters", "GREEN", 1, "travel_sandbox"),
            ("N06", "扫描周期扣费", "scan_subscriptions", "GREEN", 1, "subscription_list"),
            ("N07", "读取待支付账单", "query_upcoming_bills", "GREEN", 1, "bill_chart"),
            ("N08", "构建现金流时间线", "build_cashflow_timeline", "GREEN", 2, "travel_sandbox"),
            ("N09", "运行动态资金沙盘", "simulate_cashflow", "GREEN", 3, "travel_sandbox"),
            ("N10", "预测固定支出", "forecast_fixed_costs", "GREEN", 4, "travel_sandbox"),
            ("N11", "校验最低流动性", "check_min_liquidity", "GREEN", 4, "travel_sandbox"),
            ("N12", "计算安全旅游预算", "calculate_safe_budget", "GREEN", 4, "travel_sandbox"),
            ("N13", "压力情景测试", "stress_test_cashflow", "GREEN", 4, "travel_sandbox"),
            ("N14", "生成规划方案", "generate_plan", "GREEN", 5, "travel_sandbox"),
            ("N15", "理财适配预评估", "wealth_suitability_preview", "GREEN", 6, "wealth_products"),
            ("N16", "用户确认规划", "confirm_plan", "YELLOW", 7, "travel_sandbox"),
            ("N17", "单独发起申购", "request_wealth_subscription", "RED", 8, "wealth_products"),
            ("N18", "独立 MFA 验证", "mfa_verify", "RED", 9, "security_alert"),
            ("N19", "模拟提交申购", "simulate_wealth_subscription", "RED", 10, "summary_card"),
            ("N20", "生成审计回执", "write_audit_receipt", "GREEN", 11, "summary_card"),
        ]
        nodes = []
        for task_id, name, action, permission, stage, card_type in specs:
            nodes.append({"task_id": task_id, "name": name, "action_type": action, "amount": None, "dependencies": [], "parameters": {"stage": stage, "simulation_only": True}, "permission_level": permission, "pre_conditions": [], "post_conditions": [], "card_type": card_type})
        edges = []
        for target in ["N02", "N03", "N04", "N05", "N06", "N07"]: edges.append({"source": "N01", "target": target})
        for source in ["N02", "N03", "N04", "N05", "N06", "N07"]: edges.append({"source": source, "target": "N08"})
        edges.append({"source": "N08", "target": "N09"})
        for target in ["N10", "N11", "N12", "N13"]: edges.append({"source": "N09", "target": target})
        for source in ["N10", "N11", "N12", "N13"]: edges.append({"source": source, "target": "N14"})
        for source, target in [("N14", "N15"), ("N15", "N16"), ("N16", "N17"), ("N17", "N18"), ("N18", "N19"), ("N19", "N20")]: edges.append({"source": source, "target": target})
        return nodes, edges

    stage_specs: dict[str, list[tuple[str, str, Permission, str]]] = {
        "transfer": [
            ("解析转账意图", "parse_transfer_intent", "GREEN", "summary_card"),
            ("查询收款方关系", "resolve_recipient", "GREEN", "transfer_form"),
            ("检测金额与行为风险", "score_transfer_risk", "GREEN", "transfer_form"),
            ("TrustEngine 强制拦截", "trust_gate_transfer", "RED", "security_alert"),
            ("等待独立身份核验", "request_mfa", "RED", "security_alert"),
            ("记录反诈审计回执", "write_security_audit", "GREEN", "summary_card"),
        ],
        "bills": [
            ("解析账单分析意图", "parse_bill_intent", "GREEN", "summary_card"),
            ("读取模拟流水", "read_demo_transactions", "GREEN", "bill_chart"),
            ("计算分类统计", "aggregate_categories", "GREEN", "bill_chart"),
            ("识别主要支出", "rank_spending_categories", "GREEN", "bill_chart"),
            ("生成可视化账单卡", "render_bill_chart", "GREEN", "bill_chart"),
        ],
        "wealth": [
            ("解析理财意图", "parse_wealth_intent", "GREEN", "summary_card"),
            ("读取演示风险画像", "read_demo_risk_profile", "GREEN", "wealth_products"),
            ("检索演示产品", "list_demo_products", "GREEN", "wealth_products"),
            ("执行适当性预评估", "suitability_preview", "GREEN", "wealth_products"),
            ("等待用户选择与确认", "confirm_product_selection", "YELLOW", "wealth_products"),
            ("独立 MFA 授权", "mfa_verify", "RED", "security_alert"),
        ],
        "card": [
            ("解析卡片管理意图", "parse_card_intent", "GREEN", "summary_card"),
            ("读取脱敏卡片状态", "read_masked_card", "GREEN", "card_freeze"),
            ("评估卡片保护动作", "evaluate_card_protection", "GREEN", "card_freeze"),
            ("等待用户发起挂失", "request_card_freeze", "RED", "card_freeze"),
            ("独立 MFA 与模拟挂失", "mfa_and_simulated_freeze", "RED", "security_alert"),
        ],
        "subscriptions": [
            ("解析订阅管理意图", "parse_subscription_intent", "GREEN", "summary_card"),
            ("扫描周期扣费", "scan_demo_subscriptions", "GREEN", "subscription_list"),
            ("计算月度扣费", "aggregate_subscription_cost", "GREEN", "subscription_list"),
            ("展示订阅管理卡", "render_subscription_list", "GREEN", "subscription_list"),
            ("等待用户确认取消", "confirm_subscription_cancel", "YELLOW", "subscription_list"),
        ],
        "anomaly": [
            ("解析异常检测意图", "parse_anomaly_intent", "GREEN", "summary_card"),
            ("扫描模拟流水", "scan_demo_transactions", "GREEN", "bill_chart"),
            ("评估异常候选", "score_anomaly_candidates", "GREEN", "security_alert"),
            ("生成待核查提醒", "create_review_alert", "YELLOW", "security_alert"),
        ],
        "general": [
            ("解析用户请求", "parse_general_intent", "GREEN", "summary_card"),
            ("匹配可用业务技能", "match_available_skills", "GREEN", "summary_card"),
            ("生成下一步建议", "generate_next_step", "GREEN", "summary_card"),
        ],
    }
    specs = stage_specs.get(scenario, stage_specs["general"])
    nodes = []
    edges = []
    for idx, (name, action, permission, card_type) in enumerate(specs, start=1):
        task_id = f"N{idx:02d}"
        nodes.append({"task_id": task_id, "name": name, "action_type": action, "amount": None, "dependencies": [f"N{idx-1:02d}"] if idx > 1 else [], "parameters": {"simulation_only": True}, "permission_level": permission, "pre_conditions": [], "post_conditions": [], "card_type": card_type})
        if idx > 1:
            edges.append({"source": f"N{idx-1:02d}", "target": task_id})
    return nodes, edges


class DomainNodeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str
    name: str
    action_type: str
    amount: float | None = None
    dependencies: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    permission_level: Permission
    pre_conditions: list[str] = Field(default_factory=list)
    post_conditions: list[str] = Field(default_factory=list)
    card_type: CardType


class DomainEdgeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    target: str


class DomainAgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_name: str
    nodes: list[DomainNodeSpec]
    edges: list[DomainEdgeSpec]
    cards: list[UIBusinessCard]


@dataclass(frozen=True)
class DomainAgent:
    key: Scenario
    name: str

    def run(self, metrics: dict[str, Any]) -> DomainAgentResult:
        node_payloads, edge_payloads = build_domain_nodes(self.key, metrics)
        card_payloads = build_business_cards(self.key, metrics)
        return DomainAgentResult(
            agent_name=self.name,
            nodes=[DomainNodeSpec.model_validate(item) for item in node_payloads],
            edges=[DomainEdgeSpec.model_validate(item) for item in edge_payloads],
            cards=[UIBusinessCard.model_validate(item) for item in card_payloads],
        )


DOMAIN_AGENT_REGISTRY: dict[Scenario, DomainAgent] = {
    "travel": DomainAgent("travel", "TravelCashflowAgent"),
    "transfer": DomainAgent("transfer", "TransferRiskAgent"),
    "bills": DomainAgent("bills", "BillInsightAgent"),
    "wealth": DomainAgent("wealth", "WealthSuitabilityAgent"),
    "card": DomainAgent("card", "CardProtectionAgent"),
    "subscriptions": DomainAgent("subscriptions", "SubscriptionManagerAgent"),
    "anomaly": DomainAgent("anomaly", "TransactionAnomalyAgent"),
    "general": DomainAgent("general", "GeneralFinancialAssistantAgent"),
}


def dispatch_domain_agent(scenario: Scenario, metrics: dict[str, Any]) -> DomainAgentResult:
    """Typed skill dispatch called only by the master orchestrator."""
    agent = DOMAIN_AGENT_REGISTRY.get(scenario) or DOMAIN_AGENT_REGISTRY["general"]
    return agent.run(metrics)
