import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import styles from "./GeneratedBusinessCard.module.css";

const money = (value) => new Intl.NumberFormat("zh-CN", {
  style: "currency", currency: "CNY", maximumFractionDigits: 0,
}).format(Number(value || 0));

const permissionLabel = {
  GREEN: "GREEN · 只读 / 计算",
  YELLOW: "YELLOW · 用户确认",
  RED: "RED · 独立 MFA",
};

function CardHeader({ card }) {
  const level = card.permission_level || "GREEN";
  return (
    <div className={styles.header}>
      <div className={styles.headerTitle}>{card.title}</div>
      <span className={`${styles.permission} ${styles[level.toLowerCase()]}`}>
        {permissionLabel[level] || level}
      </span>
    </div>
  );
}

function BillChart({ data }) {
  const items = Array.isArray(data.items) ? data.items : [];
  const total = Number(data.total ?? items.reduce((sum, item) => sum + Number(item.value || 0), 0));
  const option = useMemo(() => ({
    animation: true,
    animationDuration: 650,
    tooltip: { trigger: "item", formatter: (p) => `${p.name}<br/>${money(p.value)} · ${p.percent}%` },
    legend: { bottom: 0, left: "center", itemWidth: 8, itemHeight: 8, textStyle: { color: "#7d94a8", fontSize: 10 } },
    series: [{
      name: "消费结构", type: "pie", radius: ["48%", "72%"], center: ["50%", "44%"],
      itemStyle: { borderColor: "rgba(255,255,255,.95)", borderWidth: 3, borderRadius: 7 },
      label: { show: false },
      emphasis: { scale: true, scaleSize: 6, label: { show: true, formatter: "{b}\n{d}%", color: "#31516b", fontWeight: 800 } },
      data: items.map((item) => ({ name: item.name, value: Number(item.value || 0), itemStyle: { color: item.color || "#83b8d6" } })),
    }],
    graphic: [{ type: "text", left: "center", top: "34%", style: { text: money(total), fill: "#24435e", font: "800 17px sans-serif", textAlign: "center" } },
      { type: "text", left: "center", top: "45%", style: { text: "本期模拟支出", fill: "#8da5b7", font: "10px sans-serif", textAlign: "center" } }],
  }), [items, total]);

  return (
    <div className={styles.billLayout}>
      <div className={styles.chartWrap}>
        <ReactECharts option={option} notMerge lazyUpdate style={{ width: "100%", height: 245 }} />
      </div>
      <div className={styles.billMeta}>
        <div className={styles.total}>{money(total)}</div>
        <div className={styles.muted}>{data.period || "当前账期"} · {data.transaction_count ?? "—"} 笔演示流水</div>
        <div className={styles.itemList}>
          {items.map((item) => (
            <div className={styles.itemRow} key={item.name}>
              <span className={styles.itemName}><i style={{ background: item.color || "#83b8d6" }} />{item.name}</span>
              <b>{money(item.value)}</b>
            </div>
          ))}
        </div>
        <div className={styles.disclaimer}>{data.source_label || "本地模拟数据"}，不代表真实账户流水。</div>
      </div>
    </div>
  );
}

function TransferForm({ data, onAction, card }) {
  return (
    <div className={styles.transferBody}>
      <div className={styles.recipientRow}>
        <div className={styles.recipientAvatar}>{data.recipient_avatar || "收"}</div>
        <div className={styles.recipientInfo}>
          <b>{data.recipient_name || "待核验收款方"}</b>
          <span>{data.recipient_masked || "账户信息已脱敏"}</span>
        </div>
        <span className={styles.blockedBadge}>已拦截</span>
      </div>
      <div className={styles.amountBlock}>
        <span>转账请求金额（模拟）</span>
        <strong>{money(data.amount)}</strong>
      </div>
      <div className={styles.tagRow}>
        {(data.risk_tags || []).map((tag) => <span className={styles.riskTag} key={tag}>{tag}</span>)}
      </div>
      <div className={styles.riskReason}>{data.reason}</div>
      <button className={`${styles.actionButton} ${styles.dangerButton}`} type="button" onClick={() => onAction?.("transfer.verify", card)}>
        {data.action_label || "申请身份核验"}
      </button>
      <p className={styles.disclaimer}>{data.disclaimer || "不会执行真实资金转移。"}</p>
    </div>
  );
}

function CardFreeze({ data, onAction, card }) {
  const frozen = data.status === "FROZEN";
  return (
    <div className={styles.cardBody}>
      <div className={`${styles.virtualCard} ${frozen ? styles.frozenCard : ""}`}>
        <div className={styles.cardTop}><span>ZHIYINTONG · DEBIT</span><b>智银通</b></div>
        <div className={styles.cardNumber}>{data.masked_number || "••••  ••••  ••••  4826"}</div>
        <div className={styles.cardBottom}><span>{data.cardholder || "DEMO USER"}</span><b>VISA</b></div>
        {frozen && <span className={styles.freezeStamp}>已冻结</span>}
      </div>
      <div className={styles.cardStatusRow}>
        <span>当前状态</span>
        <b className={frozen ? styles.statusRed : styles.statusGreen}>{frozen ? "已模拟冻结" : "正常 · 待操作"}</b>
      </div>
      <button className={`${styles.actionButton} ${styles.primaryButton}`} type="button" disabled={frozen} onClick={() => onAction?.("card.freeze", card)}>
        {frozen ? "已完成模拟保护" : (data.action_label || "发起挂失保护")}
      </button>
      <p className={styles.disclaimer}>{data.note || "仅改变本地模拟状态，不连接真实银行。"}</p>
    </div>
  );
}

function WealthProducts({ data, onAction, card }) {
  return (
    <div className={styles.productList}>
      <div className={styles.profileLine}>风险画像：<b>{data.risk_profile || "稳健型（演示）"}</b><span>预评估 · GREEN</span></div>
      {(data.products || []).map((product) => (
        <div className={styles.productRow} key={product.id}>
          <div className={styles.productInfo}><b>{product.name}</b><span>{product.term} · {product.note}</span></div>
          <span className={styles.productRisk}>{product.risk} · {product.risk_text}</span>
          <button type="button" className={styles.smallAction} onClick={() => onAction?.("wealth.buy", { ...card, product })}>评估</button>
        </div>
      ))}
      <p className={styles.disclaimer}>演示产品不构成投资建议；申购必须单独授权并完成 MFA。</p>
    </div>
  );
}

function SubscriptionList({ data, onAction, card }) {
  return (
    <div className={styles.subscriptionBody}>
      <div className={styles.subscriptionTotal}>预计月度扣费 <b>{money(data.monthly_total)}</b></div>
      {(data.items || []).map((item) => (
        <div className={styles.subscriptionRow} key={item.id}>
          <div className={styles.subscriptionInfo}><b>{item.name}</b><span>{item.vendor} · {item.cycle} · 下次 {item.next}</span></div>
          <b className={styles.subscriptionAmount}>{money(item.amount)}</b>
          <button type="button" className={styles.smallAction} onClick={() => onAction?.("subscription.cancel", { ...card, item })}>管理</button>
        </div>
      ))}
      <p className={styles.disclaimer}>{data.note || "操作仅更新本地模拟清单。"}</p>
    </div>
  );
}

function TravelSandbox({ data }) {
  const s = data.sandbox || {};
  const values = [
    ["模拟余额", s.current_balance], ["房贷预留", s.mortgage_reserve],
    ["日常开销", s.daily_expense_reserve], ["最低流动性", s.minimum_liquidity_reserve],
    ["安全旅游预算", s.safe_travel_budget], ["剩余可评估资金", s.investable_surplus],
  ];
  return (
    <div className={styles.metricsGrid}>
      {values.map(([label, value]) => <div className={styles.metric} key={label}><span>{label}</span><b>{money(value)}</b></div>)}
      <p className={styles.disclaimer}>{data.note}</p>
    </div>
  );
}

function SecurityAlert({ data }) {
  const high = data.severity === "HIGH" || data.status === "BLOCKED";
  return (
    <div className={`${styles.securityBody} ${high ? styles.securityHigh : ""}`}>
      <div className={styles.securityIcon}>{high ? "!" : "i"}</div>
      <div className={styles.securityCopy}>
        <b>{data.status === "BLOCKED" ? "请求已被安全网关拦截" : "检测到待核查事项"}</b>
        <p>{data.reason || data.message}</p>
        {data.message && data.reason && <small>{data.message}</small>}
      </div>
    </div>
  );
}

function SummaryCard({ data }) {
  return <div className={styles.summaryBody}><span>AI 任务摘要</span><p>{data.message || "任务已完成。"}</p><small>{data.source_label || "智银通金融智能体"}</small></div>;
}

export default function GeneratedBusinessCard({ card, onAction }) {
  if (!card || !card.card_type) return null;
  const data = card.data || {};
  const supported=["transfer_form","bill_chart","card_freeze","wealth_products","subscription_list","travel_sandbox","security_alert","summary_card"].includes(card.card_type);
  return (
    <section className={`${styles.card} ${card.permission_level === "RED" ? styles.cardRed : ""}`} data-card-type={card.card_type}>
      <CardHeader card={card} />
      {!supported && <p role="status">暂不支持此业务卡片类型。已安全降级为只读提示，不执行任何动作。</p>}
      {card.card_type === "transfer_form" && <TransferForm data={data} card={card} onAction={onAction} />}
      {card.card_type === "bill_chart" && <BillChart data={data} />}
      {card.card_type === "card_freeze" && <CardFreeze data={data} card={card} onAction={onAction} />}
      {card.card_type === "wealth_products" && <WealthProducts data={data} card={card} onAction={onAction} />}
      {card.card_type === "subscription_list" && <SubscriptionList data={data} card={card} onAction={onAction} />}
      {card.card_type === "travel_sandbox" && <TravelSandbox data={data} />}
      {card.card_type === "security_alert" && <SecurityAlert data={data} />}
      {card.card_type === "summary_card" && <SummaryCard data={data} />}
    </section>
  );
}
