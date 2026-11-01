import {AssistantInsights,TwinPanel,FraudPanel,TracePanel} from '../components/IntelligencePanels';
import AuditConsole from "../components/AuditConsole";
import CheckerApprovalModal from "../components/CheckerApprovalModal";
import DevelopmentLogin from "../components/DevelopmentLogin";
import { bankingRequest, getToken, AuthenticatedEventSource } from "../components/bankingClient";
import Head from "next/head";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import ReactECharts from "echarts-for-react";
import GeneratedBusinessCard from "../components/GeneratedBusinessCard";
import spiritDockStyles from "../components/SpiritCompanions.module.css";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  BadgeCheck,
  Banknote,
  Bot,
  Check,
  ChevronRight,
  CircleCheck,
  ClipboardList,
  CreditCard,
  LayoutDashboard,
  LockKeyhole,
  MessageCircle,
  PieChart,
  PiggyBank,
  Plane,
  Plus,
  Receipt,
  Repeat,
  ScanFace,
  Search,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Wallet,
  X,
} from "lucide-react";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const api = axios.create({
  baseURL: API_BASE,
  timeout: 45000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use(config => { config.headers.Authorization = `Bearer ${getToken()}`; return config; });

const money = (value) =>
  new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));

const permissionMeta = {
  GREEN: {
    label: "GREEN · 只读 / 计算",
    className: "permission-green",
    color: "#72b99a",
    fill: "#eaf7f0",
    text: "#34775e",
  },
  YELLOW: {
    label: "YELLOW · 二次确认",
    className: "permission-yellow",
    color: "#dfb45f",
    fill: "#fff6e4",
    text: "#8c6828",
  },
  RED: {
    label: "RED · MFA 强验证",
    className: "permission-red",
    color: "#df8490",
    fill: "#fff0f1",
    text: "#a84b58",
  },
};

const SCENARIOS = [
  {
    key: "travel",
    icon: <Plane size={19} />,
    number: "01",
    title: "跨场景资金规划",
    subtitle: "旅游 + 理财",
    description: "先保障房贷与日常支出，再推演旅游预算和剩余资金安排。",
    tone: "blue",
    prompt: "下个月我要出去旅游，帮我规划一下资金，保证房贷和日常开销不受影响，剩余资金再考虑理财。",
  },
  {
    key: "transfer",
    icon: <ShieldAlert size={19} />,
    number: "02",
    title: "智能转账防诈",
    subtitle: "陌生账户 · 大额风险",
    description: "识别陌生收款方与异常金额，触发风险拦截和独立身份核验。",
    tone: "rose",
    prompt: "检测到陌生账户大额转账请求，请启动智能转账防诈。",
  },
  {
    key: "bills",
    icon: <PieChart size={19} />,
    number: "03",
    title: "消费账单分析",
    subtitle: "分类洞察 · 现金流",
    description: "按消费类别拆解模拟流水，快速识别主要支出结构。",
    tone: "violet",
    prompt: "请分析我的消费账单，展示各类支出占比。",
  },
  {
    key: "wealth",
    icon: <PiggyBank size={19} />,
    number: "04",
    title: "稳健理财申购",
    subtitle: "风险测评 · 独立授权",
    description: "查看演示产品与风险画像，申购动作必须经过 RED MFA。",
    tone: "amber",
    prompt: "根据稳健型风险偏好，查看适合进一步评估的理财产品。",
  },
  {
    key: "card",
    icon: <CreditCard size={19} />,
    number: "05",
    title: "卡片安全管理",
    subtitle: "虚拟卡片 · 挂失保护",
    description: "查看虚拟银行卡状态，体验一键挂失后的保护状态变化。",
    tone: "cyan",
    prompt: "请检查我的银行卡状态，并演示卡片挂失保护。",
  },
  {
    key: "subscriptions",
    icon: <Repeat size={19} />,
    number: "06",
    title: "订阅扣费管家",
    subtitle: "周期扣费 · 订阅管理",
    description: "集中查看周期性订阅服务，模拟取消不再需要的扣费项目。",
    tone: "green",
    prompt: "请检查我的订阅服务，并帮我管理不需要的周期扣费。",
  },
];

const BILL_DATA = [
  { name: "房贷", value: 3000, itemStyle: { color: "#6f91c9" } },
  { name: "餐饮", value: 1800, itemStyle: { color: "#83bca5" } },
  { name: "购物", value: 1200, itemStyle: { color: "#b6a6d8" } },
  { name: "出行", value: 900, itemStyle: { color: "#e4c27e" } },
  { name: "日常缴费", value: 800, itemStyle: { color: "#8fb7d7" } },
  { name: "其他", value: 500, itemStyle: { color: "#c5cdd7" } },
];

const WEALTH_PRODUCTS = [
  {
    id: "P01",
    name: "安心现金管理",
    type: "现金管理类 · 演示产品",
    risk: "R1",
    riskText: "低风险",
    term: "灵活期限",
    note: "侧重流动性管理，适合短期资金观察。",
  },
  {
    id: "P02",
    name: "稳健固收组合",
    type: "固定收益类 · 演示产品",
    risk: "R2",
    riskText: "中低风险",
    term: "90 天示例期限",
    note: "以稳健配置为目标，仍存在净值波动可能。",
  },
  {
    id: "P03",
    name: "短期债券精选",
    type: "债券策略类 · 演示产品",
    risk: "R2",
    riskText: "中低风险",
    term: "180 天示例期限",
    note: "用于展示风险匹配流程，不代表实际可购买产品。",
  },
];

const INITIAL_SUBSCRIPTIONS = [
  { id: "S01", name: "影音会员", vendor: "星河视频", amount: 25, cycle: "每月 08 日", next: "11 月 08 日", icon: "▶" },
  { id: "S02", name: "云空间服务", vendor: "云端存储", amount: 18, cycle: "每月 12 日", next: "11 月 12 日", icon: "☁" },
  { id: "S03", name: "音乐会员", vendor: "声波音乐", amount: 15, cycle: "每月 18 日", next: "11 月 18 日", icon: "♫" },
  { id: "S04", name: "健身服务", vendor: "悦动健身", amount: 99, cycle: "每月 26 日", next: "11 月 26 日", icon: "✦" },
];

function buildExpandedTravelDag(sandbox, backendNodes = [], backendEdges = [], workflow = null) {
  // 节点位置由前端视觉模板管理；节点名称、权限、card_type 和依赖关系优先采用后端 Financial IR。
  const nodes = [
    ["N01", "解析金融意图", "GREEN", 0, 3, "识别旅游、预算、固定支出与理财目标"],
    ["N02", "查询账户余额", "GREEN", 1, 0, "读取演示账户可用余额"],
    ["N03", "查询房贷计划", "GREEN", 1, 1, "读取下月房贷计划并标记保护资金"],
    ["N04", "分析日常开销", "GREEN", 1, 2, "统计基础生活支出"],
    ["N05", "提取旅游目标", "GREEN", 1, 3, "提取出行时间与预算意图"],
    ["N06", "扫描周期扣费", "GREEN", 1, 4, "识别订阅和固定扣款"],
    ["N07", "读取待支付账单", "GREEN", 1, 5, "检查未来账单与到期义务"],
    ["N08", "构建现金流时间线", "GREEN", 2, 3, "汇总账户、支出、账单与目标"],
    ["N09", "运行动态资金沙盘", "GREEN", 3, 3, "执行基准与压力情景推演"],
    ["N10", "预测固定支出", "GREEN", 4, 1, "优先覆盖房贷与周期性扣款"],
    ["N11", "校验最低流动性", "GREEN", 4, 2, "保留最低可用现金储备"],
    ["N12", "计算安全旅游预算", "GREEN", 4, 3, "在保护性约束后计算可用预算"],
    ["N13", "压力情景测试", "GREEN", 4, 4, "评估额外支出下的现金流韧性"],
    ["N14", "生成规划方案", "GREEN", 5, 3, "生成可解释的资金分配建议"],
    ["N15", "理财适配预评估", "GREEN", 6, 3, "只做产品风险与资金适配检查"],
    ["N16", "用户确认规划", "YELLOW", 7, 3, "需要用户明确确认规划内容"],
    ["N17", "单独发起申购", "RED", 8, 3, "高风险交易请求进入强验证"],
    ["N18", "独立 MFA 验证", "RED", 9, 3, "模拟人脸或短信二次认证"],
    ["N19", "模拟提交申购", "RED", 10, 3, "仅更新本地模拟执行状态"],
    ["N20", "生成审计回执", "GREEN", 11, 3, "记录模拟结果与授权链路"],
  ].map(([id, name, permission, col, row, detail]) => {
    const serverNode = (backendNodes || []).find((item) => (item.task_id || item.id) === id);
    return {
      id,
      name: serverNode?.name || name,
      permission: serverNode?.permission_level || serverNode?.permission || permission,
      cardType: serverNode?.card_type || "summary_card",
      col,
      row,
      detail: serverNode?.detail || serverNode?.description || detail,
    };
  });

  const edges = backendEdges?.length
    ? backendEdges.map((edge) => ({ source: edge.source, target: edge.target }))
    : [
    ...["N02", "N03", "N04", "N05", "N06", "N07"].map((target) => ({ source: "N01", target })),
    ...["N02", "N03", "N04", "N05", "N06", "N07"].map((source) => ({ source, target: "N08" })),
    { source: "N08", target: "N09" },
    ...["N10", "N11", "N12", "N13"].map((target) => ({ source: "N09", target })),
    ...["N10", "N11", "N12", "N13"].map((source) => ({ source, target: "N14" })),
    { source: "N14", target: "N15" },
    { source: "N15", target: "N16" },
    { source: "N16", target: "N17" },
    { source: "N17", target: "N18" },
    { source: "N18", target: "N19" },
    { source: "N19", target: "N20" },
  ];

  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  const chartWidth = 2520;
  const chartHeight = 720;
  const data = nodes.map((node) => {
    const meta = permissionMeta[node.permission];
    const x = 100 + node.col * 210;
    const y = 90 + node.row * 105;
    let detail = node.detail;
    if (workflow && ['N17','N18','N19','N20'].includes(node.id)) detail += ` · 服务端状态：${workflow.state}`;
    if (node.id === "N02" && sandbox) detail = `模拟余额 ${money(sandbox.current_balance)} · ${detail}`;
    if (node.id === "N03" && sandbox) detail = `房贷预留 ${money(sandbox.mortgage_reserve)} · ${detail}`;
    if (node.id === "N04" && sandbox) detail = `日常预留 ${money(sandbox.daily_expense_reserve)} · ${detail}`;
    if (node.id === "N12" && sandbox) detail = `安全预算 ${money(sandbox.safe_travel_budget)} · ${detail}`;
    return {
      id: node.id,
      name: node.name,
      permission: node.permission,
      cardType: node.cardType,
      detail,
      x,
      y,
      symbol: "roundRect",
      symbolSize: [166, 66],
      itemStyle: {
        color: meta.fill,
        borderColor: meta.color,
        borderWidth: 1.5,
        shadowBlur: 20,
        shadowColor: `${meta.color}70`,
      },
      label: {
        show: true,
        position: "inside",
        formatter: `${node.id}  ${node.name}\n${node.permission} · ${node.permission === "GREEN" ? "只读/计算" : node.permission === "YELLOW" ? "用户确认" : "MFA 强验证"}`,
        color: meta.text,
        fontSize: 10,
        fontWeight: 750,
        lineHeight: 17,
        align: "center",
      },
    };
  });

  const links = edges.map((edge) => {
    const target = nodeMap.get(edge.target);
    const meta = permissionMeta[target?.permission || "GREEN"];
    return {
      source: edge.source,
      target: edge.target,
      lineStyle: {
        color: meta.color,
        width: 1.7,
        curveness: 0.24,
        opacity: 0.8,
        shadowBlur: 5,
        shadowColor: `${meta.color}55`,
      },
    };
  });

  return {
    width: chartWidth,
    height: chartHeight,
    nodeCount: nodes.length,
    option: {
      animation: true,
      animationDuration: 950,
      animationEasing: "cubicOut",
      backgroundColor: "transparent",
      tooltip: {
        trigger: "item",
        confine: true,
        backgroundColor: "rgba(255,255,255,.98)",
        borderColor: "#e5ebf2",
        borderWidth: 1,
        padding: 12,
        textStyle: { color: "#34445b", fontSize: 11 },
        formatter: (params) => {
          if (params.dataType !== "node") return "任务依赖关系";
          const node = params.data;
          return `<b>${node.id} · ${node.name}</b><br/>权限：${node.permission}<br/>卡片：${node.cardType || "summary_card"}<br/>${node.detail}`;
        },
      },
      graphic: [
        { type: "text", left: 28, top: 16, style: { text: "INTENT", fill: "#9aa9bc", font: "700 10px sans-serif" } },
        { type: "text", left: 245, top: 16, style: { text: "PARALLEL DATA", fill: "#9aa9bc", font: "700 10px sans-serif" } },
        { type: "text", left: 675, top: 16, style: { text: "CASHFLOW SANDBOX", fill: "#9aa9bc", font: "700 10px sans-serif" } },
        { type: "text", left: 1090, top: 16, style: { text: "RISK & BUDGET", fill: "#9aa9bc", font: "700 10px sans-serif" } },
        { type: "text", left: 1510, top: 16, style: { text: "PLAN", fill: "#9aa9bc", font: "700 10px sans-serif" } },
        { type: "text", left: 1940, top: 16, style: { text: "AUTHORIZATION", fill: "#9aa9bc", font: "700 10px sans-serif" } },
        { type: "text", left: 2370, top: 16, style: { text: "AUDIT", fill: "#9aa9bc", font: "700 10px sans-serif" } },
      ],
      series: [
        {
          type: "graph",
          layout: "none",
          data,
          links,
          roam: true,
          draggable: false,
          edgeSymbol: ["none", "arrow"],
          edgeSymbolSize: [4, 8],
          lineStyle: { color: "#b9c8d9", width: 1.5, curveness: 0.24 },
          emphasis: {
            focus: "adjacency",
            lineStyle: { width: 2.8, opacity: 1 },
            itemStyle: { shadowBlur: 30 },
          },
          scaleLimit: { min: 0.45, max: 1.5 },
        },
      ],
    },
  };
}

function buildBillOption() {
  return {
    animation: true,
    animationDuration: 900,
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      formatter: (params) => `${params.name}<br/>${money(params.value)} · ${params.percent}%`,
      backgroundColor: "#fff",
      borderColor: "#e8edf4",
      textStyle: { color: "#34445b", fontSize: 11 },
    },
    legend: {
      orient: "vertical",
      right: 8,
      top: "middle",
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 13,
      textStyle: { color: "#8492a5", fontSize: 10 },
    },
    series: [
      {
        name: "消费结构",
        type: "pie",
        radius: ["53%", "76%"],
        center: ["34%", "50%"],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: "#fff", borderWidth: 4, borderRadius: 8 },
        label: { show: false },
        emphasis: {
          scale: true,
          scaleSize: 8,
          label: { show: true, fontSize: 12, fontWeight: 800, color: "#33445b", formatter: "{b}\n{d}%" },
        },
        data: BILL_DATA,
      },
    ],
    graphic: [
      {
        type: "text",
        left: "24%",
        top: "43%",
        style: { text: money(BILL_DATA.reduce((sum, item) => sum + item.value, 0)), fill: "#26384f", font: "800 18px sans-serif", textAlign: "center" },
      },
      {
        type: "text",
        left: "24%",
        top: "53%",
        style: { text: "模拟总支出", fill: "#9aa6b5", font: "10px sans-serif", textAlign: "center" },
      },
    ],
  };
}


function buildOverviewOption(sandbox) {
  const mortgage = Number(sandbox?.mortgage_reserve ?? 3000);
  const daily = Number(sandbox?.daily_expense_reserve ?? 2000);
  const liquidity = Number(sandbox?.minimum_liquidity_reserve ?? 1000);
  const travel = Number(sandbox?.safe_travel_budget ?? 3000);
  const investable = Number(sandbox?.investable_surplus ?? 1000);
  const totalBalance = Number(sandbox?.current_balance ?? (mortgage + daily + liquidity + travel + investable));
  return {
    animation: true,
    animationDuration: 900,
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      formatter: (params) => `${params.name}<br/>${money(params.value)} · ${params.percent}%`,
      backgroundColor: "rgba(255,255,255,.98)",
      borderColor: "#dcebf6",
      textStyle: { color: "#29415b", fontSize: 11 },
    },
    series: [{
      name: "资金分布",
      type: "pie",
      radius: ["67%", "84%"],
      center: ["50%", "50%"],
      startAngle: 90,
      clockwise: true,
      avoidLabelOverlap: true,
      label: { show: false },
      itemStyle: { borderColor: "#ffffff", borderWidth: 3, borderRadius: 8 },
      emphasis: { scale: true, scaleSize: 5, itemStyle: { shadowBlur: 18, shadowColor: "rgba(45,137,204,.22)" } },
      data: [
        { name: "固定保障资金", value: mortgage + daily + liquidity, itemStyle: { color: "#47a7df" } },
        { name: "旅游目标预算", value: travel, itemStyle: { color: "#f1c36d" } },
        { name: "灵活评估资金", value: investable, itemStyle: { color: "#e78b91" } },
      ],
    }],
    graphic: [
      { type: "text", left: "center", top: "39%", style: { text: money(totalBalance), fill: "#203b59", font: "800 14px -apple-system,BlinkMacSystemFont,sans-serif", textAlign: "center" } },
      { type: "text", left: "center", top: "54%", style: { text: "资金结构", fill: "#91a4b8", font: "10px -apple-system,BlinkMacSystemFont,sans-serif", textAlign: "center" } },
    ],
  };
}

function CityscapeBackdrop() {
  const buildings = [
    [10, 286, 34, 112], [52, 250, 42, 148], [102, 300, 30, 98],
    [142, 224, 48, 174], [198, 270, 36, 128], [245, 310, 28, 88],
    [300, 260, 40, 138], [350, 292, 30, 106], [402, 238, 48, 160],
    [462, 280, 34, 118], [520, 305, 30, 93], [572, 246, 42, 152],
    [630, 276, 34, 122], [682, 220, 48, 178], [742, 292, 34, 106],
    [800, 258, 42, 140], [854, 302, 30, 96], [906, 236, 48, 162],
    [968, 278, 34, 120], [1020, 304, 30, 94], [1070, 252, 42, 146],
    [1124, 286, 34, 112], [1176, 228, 48, 170], [1236, 278, 34, 120],
    [1288, 300, 30, 98], [1340, 250, 44, 148], [1398, 280, 34, 118],
    [1450, 236, 48, 162], [1510, 288, 34, 110],
  ];
  return (
    <div className="city-backdrop" aria-hidden="true">
      <svg viewBox="0 0 1600 480" preserveAspectRatio="xMidYMax slice">
        <defs>
          <linearGradient id="city-haze" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#effaff" stopOpacity="0" />
            <stop offset="48%" stopColor="#d9f2ff" stopOpacity=".32" />
            <stop offset="100%" stopColor="#7dc9ef" stopOpacity=".55" />
          </linearGradient>
          <linearGradient id="city-tower" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#d8f3ff" stopOpacity=".9" />
            <stop offset="100%" stopColor="#70b9e4" stopOpacity=".42" />
          </linearGradient>
          <linearGradient id="city-water" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#72c5ef" stopOpacity=".24" />
            <stop offset="100%" stopColor="#278cc7" stopOpacity=".16" />
          </linearGradient>
        </defs>
        <rect width="1600" height="480" fill="url(#city-haze)" />
        <path d="M0 390 C210 365 320 402 520 380 S900 365 1100 390 S1400 370 1600 385 V480 H0Z" fill="url(#city-water)" />
        <g fill="url(#city-tower)" stroke="#8cc9e9" strokeOpacity=".55" strokeWidth="1.2">
          {buildings.map(([x, y, w, h], i) => (
            <g key={i}>
              <rect x={x} y={y} width={w} height={h} rx="2" />
              {i % 3 === 0 && <path d={`M${x + w / 2} ${y - 18} v18`} stroke="#8bc9e9" strokeWidth="2" />}
              {Array.from({ length: Math.max(2, Math.floor(h / 24)) }).map((_, j) => (
                <path key={j} d={`M${x + 7} ${y + 15 + j * 22} h${Math.max(8, w - 14)}`} stroke="#ffffff" strokeOpacity=".42" strokeWidth="1.2" />
              ))}
            </g>
          ))}
        </g>
        <g fill="none" stroke="#ffffff" strokeOpacity=".72">
          <path d="M0 398 C220 385 350 415 570 398 S930 385 1130 402 S1430 386 1600 398" strokeWidth="2" />
          <path d="M0 425 C220 412 350 442 570 425 S930 412 1130 429 S1430 413 1600 425" strokeWidth="1.4" />
          <path d="M0 452 C220 439 350 469 570 452 S930 439 1130 456 S1430 440 1600 452" strokeWidth="1" />
        </g>
        <g fill="none" stroke="#4fa9dd" strokeOpacity=".38" strokeWidth="1.2">
          <path d="M0 410 L240 400 L430 420 L650 405 L870 424 L1080 405 L1290 420 L1600 405" />
          <path d="M0 444 L220 433 L420 450 L620 438 L850 456 L1070 438 L1300 453 L1600 440" />
        </g>
        <path d="M0 390 Q220 335 430 386 T860 382 T1290 382 T1600 376" fill="none" stroke="#ffffff" strokeOpacity=".82" strokeWidth="3" />
      </svg>
    </div>
  );
}

function ResponsiveEChart({ option, height = 320, width = "100%", className = "" }) {
  const chartRef = useRef(null);
  const hostRef = useRef(null);

  useEffect(() => {
    const resize = () => {
      try {
        chartRef.current?.getEchartsInstance?.()?.resize({ animation: { duration: 140 } });
      } catch (_) {
        // 图表卸载过程中的 resize 失败不影响页面交互。
      }
    };

    const host = hostRef.current;
    let observer = null;
    if (host && typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver(() => resize());
      observer.observe(host);
    }
    window.addEventListener("resize", resize, { passive: true });
    const frame = window.requestAnimationFrame(resize);

    return () => {
      window.cancelAnimationFrame(frame);
      observer?.disconnect();
      window.removeEventListener("resize", resize);
    };
  }, [option]);

  return (
    <div ref={hostRef} className={`echart-host ${className}`} style={{ width: "100%", minWidth: width === "100%" ? 0 : width }}>
      <ReactECharts
        ref={chartRef}
        option={option}
        notMerge
        lazyUpdate
        autoResize
        style={{ height: `${height}px`, width }}
      />
    </div>
  );
}

function FaceGraphic() {
  return (
    <div className="face-scanner" aria-hidden="true">
      <div className="face-grid" />
      <svg viewBox="0 0 120 160" fill="none">
        <path d="M60 13C39 13 26 30 27 55L29 91C30 117 42 139 60 145C78 139 90 117 91 91L93 55C94 30 81 13 60 13Z" stroke="#719BD4" strokeWidth="1.7" fill="rgba(115,157,218,.06)" />
        <path d="M39 66C45 61 51 61 56 66M64 66C69 61 75 61 81 66" stroke="#6D9EDB" strokeWidth="2" strokeLinecap="round" />
        <path d="M60 69L55 91L63 94" stroke="#6D9EDB" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M47 111C54 117 67 117 74 111" stroke="#48AD91" strokeWidth="1.8" strokeLinecap="round" />
        <path d="M21 47V31H37M99 47V31H83M21 111V127H37M99 111V127H83" stroke="#48AD91" strokeWidth="1.2" />
      </svg>
      <div className="scan-corners"><i /><i /><i /><i /></div>
      <div className="scan-caption">BIOMETRIC SCAN · SIMULATION ONLY</div>
    </div>
  );
}

function MfaModal({ context, busy, onClose, onVerify }) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKey = (event) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKey);
    };
  }, [busy, onClose]);

  const isTransfer = context?.kind === "transfer";
  return (
    <div className="modal-backdrop" role="presentation">
      <div
        className="mfa-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mfa-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <span className="permission-pill permission-red">RED PERMISSION · HIGH RISK</span>
          <button className="modal-close" type="button" onClick={onClose} disabled={busy} aria-label="关闭验证弹窗">
            <X size={17} />
          </button>
        </div>
        <div className="mt-5 text-center">
          <div className="text-[9px] font-extrabold tracking-[.17em] text-rose-500">INDEPENDENT AUTHORIZATION</div>
          <h2 id="mfa-title" className="mt-2 text-xl font-extrabold tracking-apple text-slate-800">
            {context?.title || "请完成独立身份验证"}
          </h2>
          <p className="mx-auto mt-2 max-w-xs text-[11px] leading-6 text-slate-400">
            {context?.detail || "高风险操作已暂停，需要用户单独授权并完成模拟多因子验证。"}
          </p>
        </div>
        <FaceGraphic />
        <div className="mb-4 text-center text-[9px] text-slate-400">
          <span className="status-dot" />等待模拟活体识别
        </div>
        <div className={`rounded-xl border p-3 text-[10px] leading-5 ${isTransfer ? "border-rose-100 bg-rose-50/80 text-rose-700" : "border-amber-100 bg-amber-50/70 text-amber-800"}`}>
          {isTransfer
            ? "安全提示：身份核验不会自动解除反诈拦截。陌生收款方及大额转账仍需独立核实，本演示不会放行该笔转账。"
            : "当前为演示验证：不会调用摄像头、短信服务或真实身份认证服务，也不会发生真实资金交易。"}
        </div>
        <button className="primary-button mt-4 w-full" disabled={busy} onClick={onVerify} type="button">
          {busy ? "正在验证…" : <><ScanFace size={15} /> 模拟人脸识别通过</>}
        </button>
        <button className="secondary-button mt-2 w-full" disabled={busy} onClick={onClose} type="button">暂不验证</button>
      </div>
    </div>
  );
}

function Metric({ label, value, foot, accent = false, icon }) {
  return (
    <div className="metric-card">
      <div className="flex items-center justify-between gap-2">
        <div className="metric-label">{label}</div>
        {icon && <span className="metric-icon">{icon}</span>}
      </div>
      <div className={`metric-value ${accent ? "text-emerald-700" : ""}`}>{value}</div>
      <div className="metric-foot">{foot}</div>
    </div>
  );
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-3">
      <div className="text-[8px] text-slate-400">{label}</div>
      <div className="mt-1 text-[11px] font-extrabold text-slate-700">{value}</div>
    </div>
  );
}

function SecurityLine({ color, title, description }) {
  return (
    <div className="security-line">
      <span className={`status-led ${String(title).toLowerCase()}`} />
      <div className="min-w-0">
        <div className="security-level">{title}</div>
        <div className="security-description">{description}</div>
      </div>
      <span className="security-state">ACTIVE</span>
    </div>
  );
}

function PermissionCard({ level, title, description, count }) {
  const meta = permissionMeta[level];
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-3">
      <span className={`permission-pill ${meta.className}`}>{level}</span>
      <div className="mt-2 text-[10px] font-extrabold text-slate-700">{title}</div>
      <p className="mt-1 min-h-[34px] text-[9px] leading-5 text-slate-400">{description}</p>
      <div className="mt-2 text-[16px] font-extrabold text-slate-700">{count}<span className="ml-1 text-[8px] font-medium text-slate-400">个节点</span></div>
    </div>
  );
}

function TravelPanel({
  result,
  graphModel,
  planConfirmed,
  investmentRequested,
  execution,
  onConfirmPlan,
  onRequestInvestment,
  busy,
}) {
  const sandbox = result?.sandbox || {};
  const balance = Number(sandbox.current_balance ?? 10000);
  const mortgage = Number(sandbox.mortgage_reserve ?? 3000);
  const daily = Number(sandbox.daily_expense_reserve ?? 2000);
  const liquidity = Number(sandbox.minimum_liquidity_reserve ?? 1000);
  const travel = Number(sandbox.safe_travel_budget ?? 3000);
  const investable = Number(sandbox.investable_surplus ?? 1000);
  const safe = sandbox.cashflow_safe !== false;
  const parts = [mortgage, daily, liquidity, travel, investable];
  const partColors = ["#8cb5e9", "#a8cdbb", "#d9c28f", "#79bda4", "#b9a9d8"];

  return (
    <div id="sandbox-panel" className="mt-5 space-y-4 scenario-panel">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="section-title">动态资金沙盘</div>
          <div className="section-caption">现金流约束推演 · 固定支出优先 · 最低流动资金保护</div>
        </div>
        <span className={`permission-pill ${safe ? "permission-green" : "permission-red"}`}>
          <BadgeCheck size={11} />{safe ? "约束校验完成" : "现金流风险"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Metric label="模拟账户余额" value={money(balance)} foot="演示账户总额" icon={<Wallet size={14} />} />
        <Metric label="房贷优先预留" value={money(mortgage)} foot="受保护资金" icon={<LandmarkIcon />} />
        <Metric label="日常开销预留" value={money(daily)} foot="基本生活支出" icon={<Receipt size={14} />} />
        <Metric label="安全旅游预算" value={money(travel)} foot="沙盘推演结果" accent icon={<Plane size={14} />} />
      </div>

      <div className="surface p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-[11px] font-extrabold text-slate-700">资金分配与保护约束</div>
            <div className="mt-1 text-[9px] text-slate-400">先保护固定支出与最低流动资金，再分配目标资金</div>
          </div>
          <span className={`permission-pill ${safe ? "permission-green" : "permission-red"}`}>{safe ? "现金流可覆盖" : "现金流风险"}</span>
        </div>
        <div className="progress-track mt-4">
          {parts.map((part, index) => (
            <span key={index} style={{ width: `${balance ? Math.max(0, (part / balance) * 100) : 0}%`, background: partColors[index] }} />
          ))}
        </div>
        <div className="mt-2 flex flex-wrap justify-between gap-2 text-[8px] text-slate-400">
          <span>房贷 {money(mortgage)}</span>
          <span>日常 {money(daily)}</span>
          <span>流动储备 {money(liquidity)}</span>
          <span>旅游 {money(travel)}</span>
          <span>理财评估 {money(investable)}</span>
        </div>
      </div>

      {graphModel && (
        <div className="surface overflow-hidden p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="section-title">金融任务 DAG · 20 节点细化编排视图</div>
              <div className="section-caption">并行数据采集 → 现金流沙盘 → 规划确认 → 独立 MFA → 模拟回执</div>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="permission-pill permission-green">GREEN</span>
              <span className="permission-pill permission-yellow">YELLOW</span>
              <span className="permission-pill permission-red">RED</span>
            </div>
          </div>
          <div className="dag-scroll mt-3">
            <div className="dag-chart-inner" style={{ width: `${graphModel.width}px` }}>
              <ResponsiveEChart option={graphModel.option} height={graphModel.height} width={`${graphModel.width}px`} />
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[9px] text-slate-400">
            <span>可拖拽缩放节点图；悬停节点查看任务说明与权限边界。</span>
            <span>前端细化演示视图 · 实际执行仍以服务端 Financial IR 为准</span>
          </div>
        </div>
      )}

      <div className="surface p-4">
        <div className="section-title">授权与执行边界</div>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <PermissionCard level="GREEN" title="自动只读 / 计算" description="账户查询、数据分析、现金流沙盘与预算计算。" count={result.nodes?.filter((node) => node.permission_level === "GREEN").length || 10} />
          <PermissionCard level="YELLOW" title="用户二次确认" description="规划方案必须由用户明确确认，不代表交易授权。" count={result.nodes?.filter((node) => node.permission_level === "YELLOW").length || 1} />
          <PermissionCard level="RED" title="独立 MFA 强验证" description="申购等高风险动作必须单独发起并完成验证。" count={result.nodes?.filter((node) => node.permission_level === "RED").length || 3} />
        </div>
        <div className="soft-note mt-4">
          <b className="text-slate-600">执行边界：</b>
          规划确认（YELLOW）只确认资金分配方案；理财申购（RED）必须再次由用户主动发起，并完成独立 MFA。模型输出不能提升权限，也不能绕过本地安全策略。
        </div>
        {!planConfirmed && (
          <button className="warning-button mt-4 w-full" onClick={onConfirmPlan} disabled={busy} type="button">
            <Check size={14} />确认规划方案
          </button>
        )}
        {planConfirmed && !execution && (
          <>
            <div className="mt-4 rounded-xl border border-amber-100 bg-amber-50/70 p-3 text-[10px] leading-5 text-amber-800">
              规划方案已确认。该操作没有产生交易授权；如需申购，必须单独发起 RED 权限请求。
            </div>
            {!investmentRequested && (
              <button className="danger-button mt-3 w-full" onClick={onRequestInvestment} disabled={busy} type="button">
                <CreditCard size={14} />申请购买剩余理财（{money(investable)}）
              </button>
            )}
          </>
        )}
        {execution?.status === "SIMULATED_SUCCESS" && (
          <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50/70 p-4">
            <div className="flex items-center gap-2 text-[13px] font-extrabold text-emerald-700"><Check size={16} />模拟交易执行成功</div>
            <p className="mt-2 text-[10px] leading-6 text-emerald-800/70">RED 权限模拟 MFA 已通过，模拟申购流程完成。未调用真实银行交易接口，未发生真实资金交易。</p>
          </div>
        )}
      </div>
    </div>
  );
}

function LandmarkIcon() {
  return <Banknote size={14} />;
}

function TransferPanel({ verified }) {
  return (
    <div className="surface scenario-panel mt-5 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2"><ShieldAlert size={18} className="text-rose-500" /><div className="section-title">智能转账防诈 · 风险处置</div></div>
        <span className="permission-pill permission-red">RED · 强拦截</span>
      </div>
      <div className="risk-banner mt-4">
        <div className="risk-pulse"><AlertTriangle size={22} /></div>
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-extrabold text-rose-700">检测到陌生账户大额转账，触发强拦截</div>
          <p className="mt-1 text-[10px] leading-5 text-rose-700/70">收款方不在常用名单，金额与历史行为偏离。系统暂停交易请求，不自动放行。</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <MiniStat label="收款方" value="陌生账户 · 未验证" />
        <MiniStat label="请求金额" value="¥ 8,800（模拟）" />
        <MiniStat label="风险标签" value="新收款方 / 大额" />
        <MiniStat label="处置状态" value={verified ? "身份已核验，交易仍拦截" : "等待独立核验"} />
      </div>
      <div className="soft-note mt-4">身份核验与交易放行是两项独立决策。即使模拟 MFA 通过，陌生账户大额转账仍需通过银行正式反诈流程核实。</div>
      {verified && <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50 p-3 text-[10px] font-semibold text-emerald-700"><CircleCheck size={13} className="mr-1 inline" />模拟本人核验已完成；本笔高风险转账仍保持拦截，未执行资金转移。</div>}
    </div>
  );
}

function BillsPanel({ billOption }) {
  const total = BILL_DATA.reduce((sum, item) => sum + item.value, 0);
  const top = [...BILL_DATA].sort((a, b) => b.value - a.value)[0];
  return (
    <div className="surface scenario-panel mt-5 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><div className="section-title">消费账单分析</div><div className="section-caption">分类支出结构 · 28 笔本地模拟流水</div></div>
        <span className="permission-pill permission-green"><Activity size={11} />分析完成</span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">
        <Metric label="模拟总支出" value={money(total)} foot="本期统计金额" />
        <Metric label="最大支出类别" value={top.name} foot={`${money(top.value)} · ${Math.round(top.value / total * 100)}%`} />
        <Metric label="扫描流水" value="28 笔" foot="本地固定演示样本" />
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(220px,.8fr)]">
        <div className="rounded-2xl border border-slate-100 bg-white p-3"><ResponsiveEChart option={billOption} height={320} /></div>
        <div className="rounded-2xl border border-slate-100 bg-slate-50/70 p-4">
          <div className="text-[11px] font-extrabold text-slate-700">支出分类明细</div>
          <div className="mt-3 space-y-3">
            {BILL_DATA.map((item) => (
              <div key={item.name}>
                <div className="mb-1 flex items-center justify-between text-[9px]"><span className="text-slate-500">{item.name}</span><b className="text-slate-700">{money(item.value)}</b></div>
                <div className="h-1.5 overflow-hidden rounded-full bg-white"><span className="block h-full rounded-full" style={{ width: `${item.value / total * 100}%`, background: item.itemStyle.color }} /></div>
              </div>
            ))}
          </div>
          <div className="soft-note mt-4">账单为固定模拟数据，仅用于展示分类分析能力，不代表真实账户流水。</div>
        </div>
      </div>
    </div>
  );
}

function WealthPanel({ onBuy, selectedProduct, execution }) {
  return (
    <div className="surface scenario-panel mt-5 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><div className="section-title">稳健理财申购</div><div className="section-caption">风险画像展示 · 产品预评估 · RED 独立授权</div></div>
        <span className="permission-pill permission-yellow">适当性预评估</span>
      </div>
      <div className="investor-profile mt-4">
        <div className="investor-avatar"><span>演</span><i><BadgeCheck size={11} /></i></div>
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-extrabold text-slate-700">模拟投资者风险画像</div>
          <div className="mt-1 text-[9px] text-slate-400">风险偏好：稳健型 · 演示测评结果</div>
          <div className="mt-2 flex items-center gap-2"><span className="risk-level">R2 · 稳健</span><span className="text-[8px] text-slate-400">画像完整度 82%（模拟）</span></div>
        </div>
        <div className="profile-score"><b>82</b><span>PROFILE</span></div>
      </div>
      <div className="mt-4 space-y-3">
        {WEALTH_PRODUCTS.map((product) => (
          <div className={`product-row ${selectedProduct?.id === product.id ? "product-row-selected" : ""}`} key={product.id}>
            <div className="product-symbol"><PiggyBank size={17} /></div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2"><b className="text-[11px] text-slate-700">{product.name}</b><span className={`product-risk ${product.risk === "R1" ? "risk-r1" : "risk-r2"}`}>{product.risk} · {product.riskText}</span></div>
              <div className="mt-1 text-[9px] text-slate-400">{product.type} · {product.term}</div>
              <p className="mt-1 text-[9px] leading-5 text-slate-500">{product.note}</p>
            </div>
            <button className="product-buy" type="button" onClick={() => onBuy(product)}>{selectedProduct?.id === product.id ? "重新验证" : "申购演示"}<ChevronRight size={12} /></button>
          </div>
        ))}
      </div>
      {execution?.status === "SIMULATED_SUCCESS" && (
        <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50/80 p-3 text-[10px] leading-5 text-emerald-700">
          <CircleCheck size={14} className="mr-1 inline" />模拟 MFA 已通过，演示申购流程完成；没有提交真实订单，也没有发生真实资金交易。
        </div>
      )}
      <div className="soft-note mt-4">产品名称与风险画像均为演示内容，不构成投资建议或真实产品推荐。真实申购须完成适当性评估、产品信息披露及银行正式授权。</div>
    </div>
  );
}

function CardPanel({ cardLost, onFreeze }) {
  return (
    <div className="surface scenario-panel mt-5 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><div className="section-title">卡片安全管理</div><div className="section-caption">虚拟银行卡状态 · 挂失保护模拟</div></div><span className={`permission-pill ${cardLost ? "permission-red" : "permission-green"}`}>{cardLost ? "已模拟挂失" : "卡片状态正常"}</span></div>
      <div className="card-stage mt-5">
        <div className={`virtual-bank-card ${cardLost ? "card-is-lost" : ""}`}>
          <div className="card-glow" />
          <div className="flex items-start justify-between"><div><div className="text-[9px] font-semibold tracking-[.16em] text-white/65">ZHIYINTONG · DEBIT</div><div className="mt-1 text-[16px] font-extrabold tracking-[.08em] text-white">智银通</div></div><div className="card-chip"><span /><span /><span /><span /></div></div>
          <div className="mt-8 text-[16px] font-semibold tracking-[.18em] text-white/90">••••　••••　••••　4826</div>
          <div className="mt-5 flex items-end justify-between"><div><div className="text-[7px] tracking-[.15em] text-white/55">CARD HOLDER</div><div className="mt-1 text-[10px] font-bold tracking-[.12em] text-white/90">ZHANG · DEMO USER</div></div><div className="text-[13px] font-black italic text-white/90">VISA</div></div>
          {cardLost && <div className="lost-stamp">已挂失</div>}
          <div className="card-sheen" />
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-[9px] leading-5 text-slate-400">卡号已脱敏 · 仅展示虚拟卡片 · 不连接真实账户</div>
        <button className={cardLost ? "secondary-button" : "danger-button"} type="button" onClick={onFreeze} disabled={cardLost}>{cardLost ? <><Check size={13} />已完成模拟挂失</> : <><LockKeyhole size={13} />一键挂失</>}</button>
      </div>
      {cardLost && <div className="mt-4 rounded-xl border border-rose-100 bg-rose-50 p-3 text-[10px] text-rose-700"><ShieldCheck size={13} className="mr-1 inline" />演示卡片已进入挂失状态，卡面已灰化并加盖挂失标记。真实银行卡挂失必须通过银行认证渠道办理。</div>}
    </div>
  );
}

function SubscriptionsPanel({ subscriptions, onCancel }) {
  const total = subscriptions.reduce((sum, item) => sum + item.amount, 0);
  return (
    <div className="surface scenario-panel mt-5 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><div className="section-title">订阅扣费管家</div><div className="section-caption">周期扣费清单 · 用户主动管理 · 本地状态模拟</div></div><span className="permission-pill permission-green"><Repeat size={11} />订阅扫描完成</span></div>
      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3"><Metric label="当前订阅项目" value={`${subscriptions.length} 项`} foot="演示订阅服务" /><Metric label="预计月度扣费" value={money(total)} foot="剩余项目合计" accent /><Metric label="已取消项目" value={`${INITIAL_SUBSCRIPTIONS.length - subscriptions.length} 项`} foot="本次会话模拟操作" /></div>
      {subscriptions.length ? (
        <div className="mt-4 space-y-2">
          {subscriptions.map((item) => (
            <div className="subscription-row" key={item.id}>
              <div className="subscription-icon">{item.icon}</div>
              <div className="min-w-0 flex-1"><div className="text-[10px] font-extrabold text-slate-700">{item.name}</div><div className="mt-1 text-[8px] text-slate-400">{item.vendor} · {item.cycle} · 下次扣费 {item.next}</div></div>
              <div className="mr-2 text-right"><div className="text-[11px] font-extrabold text-slate-700">{money(item.amount)}</div><div className="text-[8px] text-slate-400">/月</div></div>
              <button className="subscription-cancel" type="button" onClick={() => onCancel(item)}>一键取消</button>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-subscriptions"><CircleCheck size={24} /><b>当前演示清单已清空</b><span>本地模拟订阅均已移除。</span></div>
      )}
      <div className="soft-note mt-4">取消操作仅更新本地演示列表，不会联系商户或真实扣款渠道。真实订阅取消需以服务商确认结果为准。</div>
    </div>
  );
}


const COMPANION_DIALOGUE = {
  fraud: {girl:"已切换本地人工核查提示；请核对风险并按需要提交复核。",boy:"资金隔离：风险评估不执行交易，网关继续阻止未授权操作。",girlTag:"客服介入提示",boyTag:"资金隔离"},
  sandbox: {girl:"正在核对交易路径与风险约束...",boy:"🔒 沙箱校验中，资金已隔离",girlTag:"沙箱校验",boyTag:"模拟账本"},
  hitl: {girl:"👩‍💻 已进入人工复核流程，请稍候...",boy:"🔒 交易保持隔离，等待人工审批",girlTag:"人工复核",boyTag:"等待审批"},
  checker: {girl:"双人授权是资金安全的最后一道防线。",boy:"主管复核中，尚未获得执行权限。",girlTag:"双人复核",boyTag:"独立认证"},
  idle: {
    girl: "Hi！我是小银，您的专属金融精灵哦~ (◍•ᴗ•◍)",
    boy: "我是安全护航员，系统正常。",
    girlTag: "在线陪伴",
    boyTag: "安全守护",
  },
  thinking: {
    girl: "正在为您构建 Financial DAG... 🧠",
    boy: "沙盘推演中，正在校验资金安全边界...",
    girlTag: "正在思考",
    boyTag: "任务运行中",
  },
  alert: {
    girl: "哎呀，遇到高风险交易啦！(⊙_⊙)",
    boy: "🚨 危险！已触发防御机制，请进行身份核验！",
    girlTag: "风险提醒",
    boyTag: "安全拦截",
  },
  success: {
    girl: "任务完成，全部授权流程已核验。",
    boy: "审计回执已生成。",
    girlTag: "任务完成",
    boyTag: "审计已记录",
  },
};

function SpiritCompanions({ mood = "idle" }) {
  const [blinkTick, setBlinkTick] = useState(0);
  const [nodTick, setNodTick] = useState(0);
  const [open, setOpen] = useState(false);
  const dialogue = COMPANION_DIALOGUE[mood] || COMPANION_DIALOGUE.idle;

  useEffect(() => {
    if (["alert","fraud","thinking","sandbox","hitl","checker"].includes(mood)) setOpen(true);
  }, [mood]);

  // 小银每 3 秒眨眼一次；只更新眨眼覆盖层，不重建整个人物图片。
  useEffect(() => {
    const timer = window.setInterval(() => {
      setBlinkTick((tick) => tick + 1);
    }, 3000);
    return () => window.clearInterval(timer);
  }, []);

  // 安全护航员约每 7.2 秒轻点一次头，交替 class 让 CSS 动画自然重播。
  useEffect(() => {
    const timer = window.setInterval(() => {
      setNodTick((tick) => tick + 1);
    }, 7200);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className={spiritDockStyles.root}>
      <button
        type="button"
        className={`${spiritDockStyles.orb} ${["alert","fraud"].includes(mood) ? spiritDockStyles.alertOrb : ""}`}
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "收起双数字精灵" : "召唤双数字精灵"}
        aria-expanded={open}
      >
        <span className={spiritDockStyles.orbGlyph}>✦</span>
      </button>
      <section className={`${spiritDockStyles.panel} ${open ? spiritDockStyles.open : ""} ${["alert","fraud"].includes(mood) ? spiritDockStyles.alertPanel : ""}`} aria-hidden={!open}>
        <button type="button" className={spiritDockStyles.close} onClick={() => setOpen(false)} aria-label="关闭精灵面板">×</button>
        <div
          className={`spirit-dock mood-${mood==='fraud'?'alert':mood} ${spiritDockStyles.dockContent}`}
          data-mood={mood}
          aria-live="polite"
          aria-label="智银通双数字精灵"
        >
      <div className="spirit-bubble spirit-bubble-girl" key={`girl-bubble-${mood}`}>
        <div className="spirit-bubble-heading">
          <span className="spirit-bubble-name">
            <i className="spirit-name-dot" />
            小银 · 金融精灵
          </span>
          <span className="spirit-bubble-tag">{dialogue.girlTag}</span>
        </div>
        <p>{dialogue.girl}</p>
        {mood === "thinking" && (
          <span className="spirit-thinking-dots" aria-label="正在思考">
            <i /><i /><i />
          </span>
        )}
      </div>

      <div className="spirit-bubble spirit-bubble-guardian" key={`guardian-bubble-${mood}`}>
        <div className="spirit-bubble-heading">
          <span className="spirit-bubble-name">安全护航员</span>
          <span className="spirit-bubble-tag">{dialogue.boyTag}</span>
        </div>
        <p>{dialogue.boy}</p>
        {mood === "thinking" && (
          <span className="spirit-thinking-dots guardian-dots" aria-label="正在校验">
            <i /><i /><i />
          </span>
        )}
      </div>

      <div className="spirit-character spirit-girl" aria-label="小银，活泼的金融精灵">
        <span className="spirit-wing-glow" aria-hidden="true" />
        <span className="spirit-girl-motion">
          <img
            className="spirit-character-image"
            src="/girl-new.png?v=20261101-agentic"
            alt="小银，白蓝配色的金融精灵女孩立绘"
            draggable="false"
          />
        </span>
        <span className="spirit-eye-blink" key={blinkTick} aria-hidden="true">
          <i /><i />
        </span>
        {mood === "success" && (
          <span className="spirit-stars" aria-hidden="true">
            <i /><i /><i /><i />
          </span>
        )}
      </div>

      <div
        className={`spirit-character spirit-guardian spirit-nod-${nodTick % 2 === 0 ? "a" : "b"}`}
        aria-label="安全护航员，沉稳的男性数字管家"
      >
        <span className="spirit-radar-ring" aria-hidden="true" />
        <span className="spirit-guardian-motion">
          <img
            className="spirit-character-image"
            src="/boy-new.png?v=20261101-agentic"
            alt="安全护航员，深蓝制服的男性数字管家立绘"
            draggable="false"
          />
        </span>
        <span className="spirit-badge-scan" aria-hidden="true" />
        <span className="spirit-alert-eyes" aria-hidden="true" />
        <span className="spirit-warning-lines" aria-hidden="true"><i /><i /></span>
      </div>
        </div>
      </section>
    </div>
  );
}

function App() {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState([]);
  const [result, setResult] = useState(null);
  const [activeScenario, setActiveScenario] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [typingId, setTypingId] = useState(null);
  const [typingCount, setTypingCount] = useState(0);
  const [planConfirmed, setPlanConfirmed] = useState(false);
  const [investmentRequested, setInvestmentRequested] = useState(false);
  const [showMfa, setShowMfa] = useState(false);
  const [mfaBusy, setMfaBusy] = useState(false);
  const [mfaContext, setMfaContext] = useState(null);
  const [mfaPendingAfterTyping, setMfaPendingAfterTyping] = useState(false);
  const [transferVerified, setTransferVerified] = useState(false);
  const [execution, setExecution] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [cardLost, setCardLost] = useState(false);
  const [subscriptions, setSubscriptions] = useState(INITIAL_SUBSCRIPTIONS);
  const [toast, setToast] = useState("");
  const [secureWorkflow,setSecureWorkflow] = useState(null);
  const [ledgerAccount,setLedgerAccount] = useState(null);
  const [showChecker,setShowChecker] = useState(false);
  const [transactionAmount,setTransactionAmount] = useState("1000");
  const pendingTransaction = useRef(null);
  const [inspectWorkflowId,setInspectWorkflowId]=useState('');
  useEffect(()=>{if(result?.workflow_id){setInspectWorkflowId(result.workflow_id);sessionStorage.setItem('banking-analysis',result.workflow_id);}},[result?.workflow_id]);
  useEffect(()=>{if(secureWorkflow?.workflow_id)setInspectWorkflowId(secureWorkflow.workflow_id);},[secureWorkflow?.workflow_id]);
  useEffect(()=>{const restoreAnalysis=()=>{const id=sessionStorage.getItem('banking-analysis');if(id)bankingRequest(`/api/workflows/${id}`).then(w=>{if(w.analysis_result){setResult(w.analysis_result);setGeneratedCards(w.analysis_result.ui_cards||[]);setActiveScenario(w.analysis_result.scenario_key);}}).catch(()=>{});};restoreAnalysis();window.addEventListener('banking-auth-changed',restoreAnalysis);return()=>window.removeEventListener('banking-auth-changed',restoreAnalysis);},[]);
  useEffect(() => {
    const restore = () => {
      const id=sessionStorage.getItem('banking-workflow');
      if(id) bankingRequest(`/api/workflows/${id}`).then(setSecureWorkflow).catch(()=>{});
    };
    restore();window.addEventListener('banking-auth-changed',restore);
    return()=>window.removeEventListener('banking-auth-changed',restore);
  },[]);
  useEffect(() => {
    if(!secureWorkflow?.workflow_id)return;
    sessionStorage.setItem('banking-workflow',secureWorkflow.workflow_id);
    const source=new AuthenticatedEventSource(`${API_BASE}/api/workflows/${secureWorkflow.workflow_id}/stream`);
    const moods={sandbox_started:'sandbox',sandbox_completed:'sandbox',sandbox_rejected:'alert',mfa_required:'alert',
      hitl_required:'hitl',maker_checker_required:'checker',execution_blocked:'alert',execution_completed:'success'};
    const names=[...Object.keys(moods),'human_review_completed'];
    names.forEach(name=>source.addEventListener(name,async event=>{
      const payload=JSON.parse(event.data);
      setCompanionMood(name==='human_review_completed' ? (payload.status==='REJECT'?'alert':'checker') : moods[name]);
      try {
        const next=await bankingRequest(`/api/workflows/${secureWorkflow.workflow_id}`);setSecureWorkflow(next);
        if(next.state==='AWAITING_MAKER_MFA') {setMfaContext({kind:'secure',title:'独立 Maker MFA',detail:'服务端沙箱通过；仅验证本次绑定计划。'});setShowMfa(true);}
        if(['PENDING_HUMAN_REVIEW','AWAITING_CHECKER','REJECTED'].includes(next.state))setShowChecker(true);
      } catch(e){setError(e.message);}
    }));
    return()=>source.close();
  },[secureWorkflow?.workflow_id]);
  const [apiHealth, setApiHealth] = useState("checking");
  const [companionMood, setCompanionMood] = useState("idle");
  const [generatedCards, setGeneratedCards] = useState([]);
  const [agentEvents, setAgentEvents] = useState([]);
  const [taskId, setTaskId] = useState(null);
  const [securityBlocked, setSecurityBlocked] = useState(false);
  const eventSourceRef = useRef(null);
  const chatEndRef = useRef(null);

  // Transaction moods are driven by authenticated backend SSE events.
  useEffect(() => () => {
    eventSourceRef.current?.close?.();
  }, []);

  useEffect(() => {
    let active = true;
    api.get("/health")
      .then(() => active && setApiHealth("online"))
      .catch(() => active && setApiHealth("offline"));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!typingId) return undefined;
    const current = messages.find((message) => message.id === typingId);
    if (!current) return undefined;
    if (typingCount >= current.content.length) {
      setTypingId(null);
      return undefined;
    }
    const timer = window.setTimeout(() => setTypingCount((count) => Math.min(count + 2, current.content.length)), 13);
    return () => window.clearTimeout(timer);
  }, [typingId, typingCount, messages]);

  useEffect(() => {
    if (mfaPendingAfterTyping && !typingId && !loading) {
      setShowMfa(true);
      setMfaPendingAfterTyping(false);
    }
  }, [mfaPendingAfterTyping, typingId, loading]);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      chatEndRef.current?.scrollIntoView({ behavior: typingId ? "auto" : "smooth", block: "end" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [messages, result, activeScenario, typingCount, loading]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 2800);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const graphModel = useMemo(
    () => activeScenario === "travel" && result?.status === "ok" ? buildExpandedTravelDag(result.sandbox, result.nodes, result.dag_edges, secureWorkflow?.workflow_id === result.workflow_id ? secureWorkflow : null) : null,
    [activeScenario, result, secureWorkflow]
  );
  const billOption = useMemo(() => buildBillOption(), []);

  const appendMessage = useCallback((role, content) => {
    const id = `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setMessages((previous) => [...previous, { id, role, content }]);
    if (role === "assistant") {
      setTypingId(id);
      setTypingCount(0);
    }
    return id;
  }, []);

  // Legacy call sites emit no audit: AuditConsole's sole source is the backend.
  const addAudit = useCallback(() => {}, []);

  const resetScenarioState = () => {
    eventSourceRef.current?.close?.();
    eventSourceRef.current = null;
    setTaskId(null);
    setGeneratedCards([]);
    setAgentEvents([]);
    setSecurityBlocked(false);
    setResult(null);
    setError("");
    setPlanConfirmed(false);
    setInvestmentRequested(false);
    setExecution(null);
    setSelectedProduct(null);
    setTransferVerified(false);
    setShowMfa(false);
    setMfaPendingAfterTyping(false);
    setMfaContext(null);
  };

  const localTravelResult = (promptText) => ({
    workflow_id: null,
    status: "ok",
    analysis_type: "travel_planning",
    mode: "mock-local",
    intent: promptText,
    assistant_message: "本地演示模式已启用。已完成金融意图结构化、保护性资金约束计算与现金流沙盘推演。规划确认与理财申购授权相互独立。",
    sandbox: {
      current_balance: 10000,
      mortgage_reserve: 3000,
      daily_expense_reserve: 2000,
      minimum_liquidity_reserve: 1000,
      available_after_protected_reserves: 4000,
      safe_travel_budget: 3000,
      investable_surplus: 1000,
      cashflow_safe: true,
      risk_level: "LOW",
    },
    nodes: [],
    dag_edges: [],
    requires_mfa: true,
    security: { blocked: false },
    audit_id: `LOCAL-${Date.now()}`,
  });

  const runLocalScenarioFallback = (key) => {
    if (key === "transfer") {
      appendMessage("assistant", "后端暂不可用，已进入本地演示模式。陌生账户大额转账保持 RED 强拦截；模拟 MFA 不会解除反诈拦截。");
      setMfaContext({ kind: "transfer", title: "高风险转账 · 身份核验", detail: "本地演示模式：请完成模拟本人核验，交易仍保持拦截。" });
      setMfaPendingAfterTyping(true);
      addAudit("本地模拟转账强拦截", "后端不可达，未创建资金执行任务", "RED");
    } else if (key === "bills") {
      appendMessage("assistant", "后端暂不可用，已使用本地演示账单数据。统计不代表真实账户流水。");
      addAudit("本地账单演示已载入", "固定模拟流水，仅用于图表展示", "YELLOW");
    } else if (key === "wealth") {
      appendMessage("assistant", "后端暂不可用，已载入本地演示产品。任何申购都需要单独完成 RED MFA。");
      addAudit("本地理财演示已载入", "未发起申购", "YELLOW");
    } else if (key === "card") {
      appendMessage("assistant", "后端暂不可用，已载入本地虚拟银行卡。挂失仅改变本地演示状态。");
      addAudit("本地虚拟卡片已载入", "未连接真实银行卡", "YELLOW");
    } else if (key === "subscriptions") {
      appendMessage("assistant", "后端暂不可用，已载入本地模拟订阅清单。取消仅更新本地列表。");
      addAudit("本地订阅演示已载入", "固定模拟订阅数据", "YELLOW");
    } else if (key === "anomaly") {
      appendMessage("assistant", "后端暂不可用。当前没有读取真实流水，无法给出真实异常检测结论。");
      addAudit("异常检测降级", "没有真实流水数据，未生成风险结论", "YELLOW");
    }
  };

  const startTaskStream = (streamTaskId, scenarioKey) => new Promise((resolve, reject) => {
    eventSourceRef.current?.close?.();
    const source = new AuthenticatedEventSource(`${API_BASE}/api/stream/${encodeURIComponent(streamTaskId)}`);
    eventSourceRef.current = source;
    let settled = false;
    const close = () => {
      source.close();
      if (eventSourceRef.current === source) eventSourceRef.current = null;
    };
    const parse = (event) => {
      try { return JSON.parse(event.data || "{}"); } catch (_) { return {}; }
    };

    source.addEventListener("agent_progress", (event) => {
      const payload = parse(event);
      setCompanionMood("thinking");
      setAgentEvents((previous) => [...previous, { ...payload, eventName: "agent_progress", id: `${Date.now()}-${Math.random()}` }].slice(-10));
    });

    source.addEventListener("dag_snapshot", (event) => {
      const payload = parse(event);
      setAgentEvents((previous) => [...previous, { stage: "dag", status: "completed", message: `Financial DAG 已校验：${payload.nodes?.length || 0} 个节点、${payload.dag_edges?.length || 0} 条依赖边。`, id: `${Date.now()}-dag` }].slice(-10));
    });

    source.addEventListener("risk_intercept", (event) => {
      const payload = parse(event);
      setSecurityBlocked(true);
      setCompanionMood("alert");
      setAgentEvents((previous) => [...previous, { stage: "risk", status: "blocked", message: payload.message || "RED 风控拦截已触发。", id: `${Date.now()}-risk` }].slice(-10));
      addAudit("TrustEngine 触发 RED 风控拦截", payload.reason || "Agent 不得自动执行资金写操作", "RED");
    });

    source.addEventListener("ui_card", (event) => {
      const payload = parse(event);
      if (!payload.card) return;
      setGeneratedCards((previous) => {
        const filtered = previous.filter((item) => item.card_id !== payload.card.card_id);
        return [...filtered, payload.card];
      });
    });

    source.addEventListener("security_blocked", (event) => {
      const payload = parse(event);
      setSecurityBlocked(true);
      setCompanionMood("alert");
      setAgentEvents((previous) => [...previous, { stage: "security", status: "blocked", message: "SecurityGuardrail 已在任务编译前拦截请求；未调用连接器或资金写操作。", id: `${Date.now()}-security` }].slice(-10));
      setGeneratedCards(payload.card ? [payload.card] : []);
      setResult({
        status: "blocked", scenario_key: scenarioKey, analysis_type: "general",
        security: { blocked: true, reason: payload.reason },
        assistant_message: payload.assistant_message || "安全网关已拦截该请求。",
      });
      setLoading(false);
      addAudit("SecurityGuardrail 拦截不可信输入", payload.reason || "请求未进入 Agent 编排", "RED");
      appendMessage("assistant", payload.assistant_message || "安全网关已拦截该请求。未调用任何工具或资金写操作。");
      if (!settled) { settled = true; close(); resolve({ blocked: true }); }
    });

    source.addEventListener("task_completed", (event) => {
      const payload = parse(event);
      const data = payload.result || payload;
      setResult(data);
      setGeneratedCards(data.ui_cards || []);
      setActiveScenario(data.scenario_key || scenarioKey);
      setSecurityBlocked(data.scenario_key === "transfer" && (data.ui_cards || []).some((card) => card.card_type === "transfer_form" && card.permission_level === "RED"));
      setLoading(false);
      setApiHealth("online");
      addAudit("多智能体任务编排完成", `${data.nodes?.length || 0} 个 DAG 节点 · ${(data.ui_cards || []).length} 张动态业务卡片`, "GREEN");
      appendMessage("assistant", data.assistant_message || "金融任务已完成。");
      if (!settled) { settled = true; close(); resolve(data); }
    });

    source.addEventListener("task_error", (event) => {
      const payload = parse(event);
      setLoading(false);
      setError(payload.message || "Agent 任务失败，请重试。");
      if (!settled) { settled = true; close(); reject(new Error(payload.message || "Agent task failed")); }
    });

    source.onerror = () => {
      if (settled) return;
      settled = true;
      close();
      reject(new Error("SSE 连接中断或任务流不可用。"));
    };
  });

  const runAgentScenario = async (key, promptText) => {
    if (loading) return;
    setActiveScenario(key);
    resetScenarioState();
    appendMessage("user", promptText);
    appendMessage("assistant", "任务已接收，正在启动主控 Agent 与领域技能协作…");
    setLoading(true);
    setError("");
    try {
      // Explicit security preflight; the /api/analyze middleware repeats this check.
      await api.post("/api/security-check", { prompt: promptText, session_id: "zhiyintong-web-demo" });
      const response = await api.post("/api/analyze", {
        prompt: promptText,
        session_id: "zhiyintong-web-demo",
        scenario_key: key,
      });
      const data = response.data || {};
      if (!data.task_id) throw new Error("后端未返回 task_id，无法建立 SSE 任务流。");
      setTaskId(data.task_id);
      setResult(data);
      setGeneratedCards(data.ui_cards || []);
      setApiHealth("online");
      await startTaskStream(data.task_id, key);
    } catch (err) {
      const blockedTaskId = err.response?.status === 403 ? err.response?.data?.task_id : null;
      if (blockedTaskId) {
        setTaskId(blockedTaskId);
        setSecurityBlocked(true);
      setCompanionMood("alert");
        setLoading(true);
        try { await startTaskStream(blockedTaskId, key); }
        catch (_) {
          setSecurityBlocked(true);
      setCompanionMood("alert");
          setLoading(false);
          addAudit("安全网关拦截不可信输入", err.response?.data?.detail || "疑似提示词注入", "RED");
        }
        return;
      }
      setApiHealth("offline");
      setTaskId(null);
      setGeneratedCards([]);
      setAgentEvents([]);
      if (key === "travel") {
        const fallback = localTravelResult(promptText);
        setResult(fallback);
        appendMessage("assistant", `后端或 SSE 暂不可用，已切换本地演示模式。${fallback.assistant_message}`);
        addAudit("本地资金沙盘降级启用", "使用固定模拟账户数据；未连接银行", "YELLOW");
      } else {
        setResult(null);
        runLocalScenarioFallback(key);
      }
    } finally {
      setLoading(false);
    }
  };

  const runScenario = (key, customPrompt) => {
    if (loading) return;
    const scenario = SCENARIOS.find((item) => item.key === key);
    if (!scenario) return;
    const promptText = customPrompt || scenario.prompt;
    setPrompt("");
    setError("");
    runAgentScenario(key, promptText);
  };

  const submitPrompt = (value) => {
    const clean = value.trim();
    if (!clean || loading) return;
    if (/(旅游|旅行|旅游预算|出行资金|资金规划)/.test(clean)) return runScenario("travel", clean);
    if (/(异常交易|可疑交易|陌生账户|大额转账|转账防诈|反诈)/.test(clean)) return runScenario("transfer", clean);
    if (/(账单|消费分析|消费结构|支出占比)/.test(clean)) return runScenario("bills", clean);
    if (/(理财|申购|稳健产品)/.test(clean)) return runScenario("wealth", clean);
    if (/(挂失|银行卡|卡片安全)/.test(clean)) return runScenario("card", clean);
    if (/(订阅|周期扣费|取消扣费)/.test(clean)) return runScenario("subscriptions", clean);
    return runScenario("general", clean);
  };


  const refreshSimulation = async () => {
    const data=await bankingRequest('/api/simulation/account');
    setLedgerAccount(data.account);
    const objects=data.objects || [];
    const frozen=objects.some(x=>x.object_id==='demo-card'&&x.status==='FROZEN');setCardLost(frozen);
    const cancelled=new Set(objects.filter(x=>x.status==='CANCELLED').map(x=>x.object_id));
    setSubscriptions(INITIAL_SUBSCRIPTIONS.filter(x=>!cancelled.has(x.id)));
    setGeneratedCards(previous=>previous.map(card=>{
      if(card.card_type==='card_freeze')return {...card,data:{...card.data,status:frozen?'FROZEN':'NORMAL'}};
      if(card.card_type==='subscription_list'){
        const items=(card.data.items||[]).filter(x=>!cancelled.has(x.id));
        return {...card,data:{...card.data,items,monthly_total:items.reduce((n,x)=>n+x.amount,0)}};
      }return card;
    }));
  };
  const executeSecure = async (w=secureWorkflow) => {
    if(!w)throw new Error('没有服务端工作流');
    const next=await bankingRequest(`/api/workflows/${w.workflow_id}/execute`,{idempotency_key:w.idempotency_key});
    setSecureWorkflow(next);setExecution(next);setShowMfa(false);setShowChecker(false);
    await refreshSimulation();appendMessage('assistant',next.message);
  };
  const startSecure = async (action,amount,recipient) => {
    try {
      const fingerprint=JSON.stringify({action,amount:String(amount),recipient});
      if(!pendingTransaction.current || pendingTransaction.current.fingerprint!==fingerprint) {
        const saved=JSON.parse(sessionStorage.getItem('banking-pending-request')||'null');
        pendingTransaction.current=saved?.fingerprint===fingerprint ? saved : {fingerprint,idempotency_key:crypto.randomUUID()};
        sessionStorage.setItem('banking-pending-request',JSON.stringify(pendingTransaction.current));
      }
      let w=await bankingRequest('/api/transactions',{action,amount:String(amount),recipient,idempotency_key:pendingTransaction.current.idempotency_key});
      setSecureWorkflow(w);
      if(w.state==='FAILED')throw new Error('沙箱校验拒绝：请检查独立模拟账本余额、保护性预留和交易对象。');
      if(w.state==='SANDBOX_PASSED')w=await bankingRequest(`/api/workflows/${w.workflow_id}/maker-confirm`,{confirmed:true});
      setSecureWorkflow(w);
      if(w.permission_level==='YELLOW'&&w.state==='APPROVED')await executeSecure(w);
      if(w.state==='COMPLETED'){setExecution(w);await refreshSimulation();}
    } catch(e){setError(e.message);}
  };
  const handleGeneratedAction = async (action,payload) => {
    if(action==='transfer.verify') {
      try {const response=await api.post('/api/actions/authorize',{action_type:'transfer.execute',user_confirmed:true,mfa_verified:false,risk_flags:['new_recipient','large_amount'],simulation_only:true});
        setError(response.data.reason);setSecurityBlocked(true);
      } catch(e){setError(e.message);}return;
    }
    if(action==='card.freeze')return startSecure('card.freeze','0','demo-card');
    if(action==='wealth.buy')return startSecure('wealth.subscribe',transactionAmount,payload.product.id);
    if(action==='subscription.cancel' && window.confirm(`确认取消模拟订阅「${payload.item.name}」？`))return startSecure('subscription.cancel','0',payload.item.id);
  };
  const confirmPlan = async () => {
    try {
      if(!result?.workflow_id)throw new Error('后端不可用；不能授权本地演示结果。');
      const response=await api.post(`/api/workflows/${result.workflow_id}/confirm`,{confirmed:true});
      setPlanConfirmed(response.data.plan_confirmed);
      appendMessage('assistant',response.data.message);
    } catch(e){setError(e.response?.data?.detail||e.message);}
  };
  const requestInvestment = async () => {
    try {
      if(!result?.workflow_id)throw new Error('需要服务端工作流');
      const storageKey=`investment-${result.workflow_id}`;
      let key=sessionStorage.getItem(storageKey);if(!key){key=crypto.randomUUID();sessionStorage.setItem(storageKey,key);}
      const w=await bankingRequest(`/api/workflows/${result.workflow_id}/request-investment`,{idempotency_key:key});
      setSecureWorkflow(w);setInvestmentRequested(true);
    } catch(e){setError(e.message);}
  };
  const verifyMfa = async () => {
    setMfaBusy(true);
    try {
      if(!secureWorkflow)throw new Error('没有通过服务端沙箱的交易；禁止本地模拟放行。');
      const w=await bankingRequest(`/api/workflows/${secureWorkflow.workflow_id}/mfa/verify`,{method:'simulated_face',consent:true});
      setSecureWorkflow(w);setShowMfa(false);
      if(w.state==='APPROVED')await executeSecure(w);
      else if(w.state==='PENDING_HUMAN_REVIEW')setShowChecker(true);
    } catch(e){setError(e.message);}finally{setMfaBusy(false);}
  };
  const buyProduct = product => startSecure('wealth.subscribe',transactionAmount,product.id);
  const freezeCard = () => startSecure('card.freeze','0','demo-card');
  const cancelSubscription = item => handleGeneratedAction('subscription.cancel',{item});

  useEffect(() => {
    const refresh=()=>refreshSimulation().catch(()=>{});
    refresh();window.addEventListener('banking-auth-changed',refresh);
    return()=>window.removeEventListener('banking-auth-changed',refresh);
  },[result?.status,activeScenario]);

  const newConversation = () => {
    eventSourceRef.current?.close?.();
    eventSourceRef.current = null;
    setTaskId(null);
    setGeneratedCards([]);
    setAgentEvents([]);
    setSecurityBlocked(false);
    setMessages([]);
    setResult(null);
    setActiveScenario(null);
    setError("");
    setExecution(null);

    setPlanConfirmed(false);
    setInvestmentRequested(false);
    setSelectedProduct(null);
    setTransferVerified(false);
    setShowMfa(false);
    setMfaPendingAfterTyping(false);
    setMfaContext(null);
    setTypingId(null);
    setTypingCount(0);
  };

  const sandbox = result?.sandbox;
  const isTravel = activeScenario === "travel" && result?.status === "ok";
  const overviewOption = useMemo(() => buildOverviewOption(sandbox), [sandbox]);

  return (
    <>
      <Head>
        <title>智银通 · 可信自主银行智能体</title>
        <meta name="description" content="智银通：面向复杂金融事务的可信自主银行智能体。" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#eaf7ff" />
      </Head>

      <div className="app-shell">
        <aside className="sidebar">
          <div className="brand-lockup">
            <div className="brand-mark"><Banknote size={20} /></div>
            <div className="brand-copy">
              <div className="brand-name">智银通</div>
              <div className="brand-caption">TRUSTED FINANCIAL AGENT</div>
            </div>
          </div>

          <div className="nav-kicker">工作空间 <span>WORKSPACE</span></div>
          <nav className="sidebar-nav">
            <button className="nav-item active" type="button" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
              <MessageCircle size={16} />智能助手<span className="nav-active-dot" />
            </button>
            <button className="nav-item" type="button" onClick={() => document.getElementById("scenario-grid")?.scrollIntoView({ behavior: "smooth", block: "start" })}>
              <LayoutDashboard size={16} />六大业务场景
            </button>
            <button className="nav-item" type="button" onClick={() => document.getElementById("digital-twin-panel")?.scrollIntoView({ behavior: "smooth", block: "start" })}>
              <Wallet size={16} />动态资金沙盘
            </button>
            <button className="nav-item" type="button" onClick={() => document.getElementById("security-panel")?.scrollIntoView({ behavior: "smooth", block: "start" })}>
              <ShieldCheck size={16} />安全网关
            </button>
            <button className="nav-item" type="button" onClick={() => document.getElementById("audit-panel")?.scrollIntoView({ behavior: "smooth", block: "start" })}>
              <ClipboardList size={16} />操作审计
            </button>
          </nav>

          <div className="sidebar-status">
            <div className="sidebar-status-icon"><Bot size={17} /></div>
            <div className="sidebar-status-copy">
              <b>智能体已就绪</b>
              <span>本地演示环境 · Financial OS</span>
            </div>
            <span className={`api-led ${apiHealth}`} />
            <div className="sidebar-api-row">
              <span>API 服务</span>
              <b className={apiHealth === "online" ? "text-emerald-600" : apiHealth === "offline" ? "text-rose-500" : "text-amber-600"}>
                {apiHealth === "online" ? "已连接" : apiHealth === "offline" ? "本地降级" : "检测中"}
              </b>
            </div>
          </div>

          <div className="sidebar-bottom">
            <div className="sidebar-secure-icon"><LockKeyhole size={14} /></div>
            <div>
              <b>安全演示模式</b>
              <p>不连接真实银行账户。高风险操作仅模拟授权流程。</p>
            </div>
          </div>
        </aside>

        <main className="main-area">
          <CityscapeBackdrop />
          <div className="main-content">
            <header className="topbar">
              <div>
                <div className="topbar-eyebrow">PERSONAL FINANCIAL INTELLIGENCE</div>
                <h1>智能助手</h1>
                <p>让复杂金融事务变得清晰、可推演、可控执行。</p>
              </div>
              <div className="topbar-status">
                <span className="topbar-live-dot" />
                <span>TRUSTED AGENT</span>
                <i />
                <b>6 CORE SCENARIOS</b>
              </div>
            </header>

            <div className="workspace-grid">
              <section className="center-column">
                <DevelopmentLogin />
                <section className="hero-panel">
                  <div className="hero-topline">
                    <div className="hero-eyebrow"><Sparkles size={13} /> YOUR FINANCIAL CO-PILOT</div>
                    <span className="hero-safe-badge"><ShieldCheck size={12} />可信执行 · 全程可审计</span>
                  </div>
                  <h2 className="hero-heading">把复杂金融事务，<span>交给清晰、可控的智能协作。</span></h2>
                  <p className="hero-subheading">描述目标即可生成金融任务建议；资金规划与交易授权始终分离。</p>

                  <form className="hero-composer" onSubmit={(event) => { event.preventDefault(); submitPrompt(prompt); }}>
                    <Search size={19} className="hero-search-icon" />
                    <input
                      className="hero-input"
                      value={prompt}
                      onChange={(event) => setPrompt(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && !event.shiftKey) {
                          event.preventDefault();
                          submitPrompt(prompt);
                        }
                      }}
                      placeholder="输入你的金融问题，例如：帮我检查可疑订阅"
                      aria-label="输入金融问题"
                    />
                    <button className="generate-button" type="submit" disabled={!prompt.trim() || loading}>
                      {loading ? "分析中…" : "生成建议"} <ChevronRight size={15} />
                    </button>
                  </form>

                  <div className="hero-bubble-row">
                    <button className="prompt-bubble" type="button" onClick={() => submitPrompt("本月有异常交易吗？")} disabled={loading}>
                      <Activity size={14} />本月有异常交易吗？
                    </button>
                    <button className="prompt-bubble" type="button" onClick={() => submitPrompt("帮我检查可疑订阅")} disabled={loading}>
                      <Repeat size={14} />帮我检查可疑订阅
                    </button>
                  </div>

                  {!messages.length && (
                    <div className="hero-sample-response">
                      <span className="sample-ai-mark"><Sparkles size={12} /></span>
                      <span><b>AI：</b>已准备好分析你的资金安排、交易风险与周期扣费。</span>
                      <span className="sample-response-check"><BadgeCheck size={14} /></span>
                    </div>
                  )}
                </section>

                <section id="scenario-grid" className="scenario-library">
                  <div className="section-heading-row">
                    <div>
                      <div className="section-title">六大核心业务场景</div>
                      <div className="section-caption">从日常资金管理到高风险操作保护，覆盖关键银行任务链路</div>
                    </div>
                    <span className="scenario-count"><span /> 06 CORE SCENARIOS</span>
                  </div>

                  <div className="scenario-grid">
                    {SCENARIOS.map((card) => (
                      <button
                        key={card.key}
                        type="button"
                        className={`quick-card scenario-card tone-${card.tone} ${activeScenario === card.key ? "scenario-card-active" : ""}`}
                        onClick={() => runScenario(card.key)}
                        disabled={loading}
                      >
                        <span className="scenario-card-top">
                          <span className="quick-icon">{card.icon}</span>
                          <span className="scenario-number">{card.number}</span>
                        </span>
                        <span className="quick-title">{card.title}</span>
                        <span className="scenario-subtitle">{card.subtitle}</span>
                        <span className="quick-copy">{card.description}</span>
                        <span className="scenario-card-action">开始体验 <ChevronRight size={13} /></span>
                      </button>
                    ))}
                  </div>
                </section>

                {!!messages.length && (
                  <div className="surface chat-panel" id="chat-panel">
                    <div className="chat-panel-heading">
                      <div>
                        <div className="section-title">智能任务对话</div>
                        <div className="section-caption">意图识别 · Financial IR · 任务执行回执</div>
                      </div>
                      <button className="secondary-button" type="button" onClick={newConversation}><Plus size={13} />新建会话</button>
                    </div>
                    {!!agentEvents.length && (
                      <div className="mx-4 mt-3 rounded-xl border border-sky-100 bg-sky-50/65 p-3">
                        <div className="mb-2 flex items-center justify-between text-[9px] font-extrabold tracking-wide text-sky-700">
                          <span>AGENT LIVE TRACE · 多智能体实时进度</span>
                          <span>{loading ? "RUNNING" : "UPDATED"}</span>
                        </div>
                        <div className="space-y-2">
                          {agentEvents.map((item, index) => (
                            <div className="flex items-start gap-2 text-[9px] leading-5 text-slate-500" key={item.id || index}>
                              <span className={`mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full ${item.status === "completed" ? "bg-emerald-400" : "bg-sky-400"}`} />
                              <span>{item.message}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="chat-list">
                      {messages.map((message) => {
                        const isTyping = message.id === typingId;
                        const content = isTyping ? message.content.slice(0, typingCount) : message.content;
                        return (
                          <div key={message.id} className={`chat-row ${message.role === "user" ? "user" : ""}`}>
                            <div className="chat-avatar">{message.role === "user" ? <span>我</span> : <Bot size={15} />}</div>
                            <div className={`chat-bubble ${isTyping ? "typing-cursor" : ""}`}>{content}</div>
                          </div>
                        );
                      })}
                      {loading && <div className="chat-row"><div className="chat-avatar"><Bot size={15} /></div><div className="chat-bubble text-slate-400"><span className="inline-flex items-center gap-2"><span className="status-dot" />正在与金融任务引擎协作…</span></div></div>}
                      <div ref={chatEndRef} />
                    </div>
                  </div>
                )}

                {error && <div className="error-banner">{error}</div>}

                {result?.status === "blocked" && (
                  <div className="surface blocked-panel">
                    <span className="permission-pill permission-red">RED · BLOCKED</span>
                    <div className="blocked-title">安全网关已拦截不可信指令</div>
                    <p>{result.security?.reason}</p>
                  </div>
                )}

                <label className="soft-note">解释 / 回放工作流 <select aria-label="解释回放工作流" value={inspectWorkflowId} onChange={e=>setInspectWorkflowId(e.target.value)}><option value="">请选择任务</option>{result?.workflow_id&&<option value={result.workflow_id}>当前 Agent 分析</option>}{secureWorkflow?.workflow_id&&secureWorkflow.workflow_id!==result?.workflow_id&&<option value={secureWorkflow.workflow_id}>当前模拟交易</option>}</select></label>
                <AssistantInsights workflowId={inspectWorkflowId} />
                {isTravel && (
                  <TravelPanel
                    result={result}
                    graphModel={graphModel}
                    planConfirmed={planConfirmed}
                    investmentRequested={investmentRequested}
                    execution={execution}
                    onConfirmPlan={confirmPlan}
                    onRequestInvestment={requestInvestment}
                    busy={loading}
                  />
                )}
                {['wealth','transfer'].includes(activeScenario) && <div className="surface p-4 mt-4">
                  <div className="section-title">独立模拟交易 · 3.0 授权链</div>
                  <label className="text-[11px]">金额（元） <input type="number" min="0.01" step="0.01" value={transactionAmount} onChange={e=>{setTransactionAmount(e.target.value);pendingTransaction.current=null;}} /></label>
                  <button className="secondary-button" onClick={()=>startSecure(activeScenario==='wealth'?'wealth.subscribe':'transfer.simulate',transactionAmount,activeScenario==='wealth'?'P01':'demo-recipient')}>提交模拟交易</button>
                  <p className="section-caption">仅白名单演示对象；保留原陌生账户防诈拦截。大于 50,000 元须独立主管复核，余额不足仍拒绝。</p>
                  <button className="secondary-button" onClick={()=>{pendingTransaction.current=null;sessionStorage.removeItem('banking-pending-request');setSecureWorkflow(null);}}>新建交易</button>
                </div>}
                {ledgerAccount && <div className="soft-note mt-3">独立模拟账本当前余额：{money(ledgerAccount.balance_cents/100)} · 保护性预留：{money(ledgerAccount.reserved_cents/100)}（资金沙盘保留分析时快照）</div>}
                {secureWorkflow && <div className="soft-note mt-3">服务端交易状态：{secureWorkflow.state} · {secureWorkflow.workflow_id}
                  {secureWorkflow.state==='AWAITING_MAKER_MFA' && <button className="secondary-button" onClick={()=>setShowMfa(true)}>继续 MFA</button>}
                  {['PENDING_HUMAN_REVIEW','AWAITING_CHECKER','REJECTED'].includes(secureWorkflow.state) && <button className="secondary-button" onClick={()=>setShowChecker(true)}>查看人工复核</button>}
                  {secureWorkflow.state==='APPROVED' && <button className="primary-button" onClick={()=>executeSecure().catch(e=>setError(e.message))}>执行已授权模拟交易</button>}
                </div>}
                {generatedCards.length > 0 && (
                  <div className="generated-card-stack">
                    {generatedCards.filter((card) => activeScenario !== "travel" || card.card_type !== "travel_sandbox").map((card) => (
                      <GeneratedBusinessCard key={card.card_id} card={card} onAction={handleGeneratedAction} />
                    ))}
                  </div>
                )}
                {activeScenario === "transfer" && generatedCards.length === 0 && !loading && <TransferPanel verified={transferVerified} />}
                {activeScenario === "bills" && generatedCards.length === 0 && !loading && <BillsPanel billOption={billOption} />}
                {activeScenario === "wealth" && generatedCards.length === 0 && !loading && <WealthPanel onBuy={buyProduct} selectedProduct={selectedProduct} execution={execution} />}
                {activeScenario === "card" && generatedCards.length === 0 && !loading && <CardPanel cardLost={cardLost} onFreeze={freezeCard} />}
                {activeScenario === "subscriptions" && generatedCards.length === 0 && !loading && <SubscriptionsPanel subscriptions={subscriptions} onCancel={cancelSubscription} />}

                <TwinPanel />
                <div className="center-disclaimer">智银通为金融科技演示原型。余额、沙盘结果、产品与交易状态均为模拟数据。</div>
              </section>

              <aside className="right-rail">
                <div className="surface overview-card">
                  <div className="rail-panel-heading">
                    <div><div className="section-title">资金概览</div><div className="section-caption">FINANCIAL OVERVIEW</div></div>
                    <span className="rail-icon"><Wallet size={15} /></span>
                  </div>
                  <div className="overview-main">
                    <div className="balance-copy">
                      <span>模拟账户余额</span>
                      <strong>{money(sandbox?.current_balance ?? 10000)}</strong>
                      <small><span className="balance-trend">↗</span> 资金状态正常</small>
                    </div>
                    <div className="overview-ring">
                      <ResponsiveEChart option={overviewOption} height={142} />
                    </div>
                  </div>
                  <div className="overview-stats">
                    <MiniStat label="房贷预留" value={money(sandbox?.mortgage_reserve ?? 3000)} />
                    <MiniStat label="日常开销" value={money(sandbox?.daily_expense_reserve ?? 2000)} />
                    <MiniStat label="旅游预算" value={money(sandbox?.safe_travel_budget ?? 3000)} />
                    <MiniStat label="理财评估" value={money(sandbox?.investable_surplus ?? 1000)} />
                  </div>
                  <div className="overview-legend">
                    <span><i className="legend-blue" />保障资金</span>
                    <span><i className="legend-amber" />目标预算</span>
                    <span><i className="legend-rose" />灵活资金</span>
                  </div>
                </div>

                <div id="security-panel" className="surface security-card">
                  <div className="rail-panel-heading">
                    <div><div className="section-title">安全网关</div><div className="section-caption">ADAPTIVE TRUST ENGINE</div></div>
                    <span className="rail-icon secure"><ShieldCheck size={15} /></span>
                  </div>
                  <div className="security-list">
                    <SecurityLine title="GREEN" description="只读查询与内部计算" />
                    <SecurityLine title="YELLOW" description="规划确认与用户授权" />
                    <SecurityLine title="RED" description="高风险动作与独立 MFA" />
                  </div>
                  <div className="security-footnote">权限由本地策略复核，不直接信任模型输出。</div>
                </div>

                <FraudPanel workflow={secureWorkflow?.action==='transfer.simulate'?secureWorkflow:null} onRisk={()=>setCompanionMood('fraud')} />
                <TracePanel workflowId={inspectWorkflowId} />
                <AuditConsole workflowId={secureWorkflow?.workflow_id || result?.workflow_id} />

                <div className="capability-card">
                  <div className="capability-title"><Sparkles size={13} />智银通核心能力</div>
                  <div className="capability-list">
                    <span><BadgeCheck size={12} />多智能体任务编排</span>
                    <span><Activity size={12} />动态资金沙盘与 Financial DAG</span>
                    <span><LockKeyhole size={12} />TrustEngine 安全护栏</span>
                    <span><ArrowUpRight size={12} />MCP 工具连接器</span>
                    <span><Sparkles size={12} />声明式 Generative UI</span>
                    <span><Activity size={12} />SSE 实时任务事件流</span>
                  </div>
                </div>
              </aside>
            </div>

            <div className="main-footer-note">ZHIYINTONG FINANCIAL AGENT · SIMULATED ENVIRONMENT · NO REAL BANK TRANSACTIONS</div>
          </div>
        </main>
      </div>

      <SpiritCompanions mood={companionMood} />

      {showChecker && secureWorkflow && <CheckerApprovalModal workflow={secureWorkflow} onUpdate={setSecureWorkflow} onClose={()=>setShowChecker(false)} onExecute={()=>executeSecure().catch(e=>setError(e.message))} />}
      {showMfa && <MfaModal context={mfaContext} busy={mfaBusy} onClose={() => setShowMfa(false)} onVerify={verifyMfa} />}
      {toast && <div className="toast-message"><CircleCheck size={15} />{toast}</div>}
    </>
  );
}

export default App;
