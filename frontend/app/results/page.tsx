"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

/* ─── Types ─────────────────────────────────────────────── */
interface Category {
  name: string;
  amount: number;
  count: number;
  pct: number;
}

interface Transaction {
  date: string;
  merchant: string;
  category: string;
  amount: number;
  type: "debit" | "credit";
}

interface DowEntry {
  day: string;
  amount: number;
}

interface InsightCard {
  icon: string;
  title: string;
  body: string;
}

interface PersonalityTrait {
  id: string;
  label: string;
  description: string;
}

interface BehaviorPattern {
  type: string;
  icon: string;
  title: string;
  detail: string;
}

interface Leakage {
  type: string;
  icon: string;
  title: string;
  detail: string;
  amount: number;
}

interface Suggestion {
  icon: string;
  text: string;
}

interface SpendingScore {
  score: number;
  label: string;
}

interface BiggestLeak {
  merchant: string;
  amount: number;
  count: number;
  pct: number;
}

interface LlmReport {
  narrative: string;
  fun_facts: string[];
}

/* ─── Graph types ────────────────────────────────────────── */
interface GraphNodeData {
  id: string;
  total: number;
  count: number;
  category: string;
  community: number;
  centrality: number;
}

interface GraphEdgeData {
  source: string;
  target: string;
  weight: number;
}

interface GraphData {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
  stats: {
    total_merchants: number;
    total_connections: number;
    num_communities: number;
    top_by_spend: string[];
    most_connected: string[];
    communities: Array<{ id: number; members: string[] }>;
  };
  nlp_ready: boolean;
}

interface Result {
  total_spent: number;
  total_received: number;
  savings: number;
  savings_rate: number;
  debit_count: number;
  credit_count: number;
  categories: Category[];
  top_merchant: { name: string; amount: number };
  biggest_spending_day: { date: string; amount: number };
  weekend_vs_weekday: { weekend: number; weekday: number };
  spend_by_dow: DowEntry[];
  insights: InsightCard[];
  transactions: Transaction[];
  llm_report: LlmReport | null;
  personality: PersonalityTrait[];
  behavior_patterns: BehaviorPattern[];
  leakage: Leakage[];
  suggestions: Suggestion[];
  spending_score?: SpendingScore;
  smart_alert?: string | null;
  biggest_leak?: BiggestLeak | null;
  bank_name?: string;
  graph?: GraphData;
}

/* ─── Helpers ────────────────────────────────────────────── */
const COLORS = [
  "#7c6af7", "#a59bff", "#4ade80", "#fbbf24",
  "#f87171", "#60a5fa", "#34d399", "#fb923c",
];

const PERSONALITY_COLORS: Record<string, string> = {
  food_heavy:           "#fb923c",
  shopping_enthusiast:  "#60a5fa",
  subscription_drifter: "#a78bfa",
  weekend_spender:      "#fbbf24",
  impulse_spender:      "#f87171",
  transfer_heavy:       "#34d399",
  controlled_spender:   "#4ade80",
};

function fmt(n: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/* ─── Score color ────────────────────────────────────────── */
function scoreColor(score: number) {
  if (score >= 8.5) return "#4ade80";
  if (score >= 7)   return "#a3e635";
  if (score >= 5.5) return "#fbbf24";
  return "#f87171";
}

/* ─── Section heading ────────────────────────────────────── */
function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2
      className="text-xs font-semibold uppercase tracking-wider mb-3"
      style={{ color: "#8888aa" }}
    >
      {children}
    </h2>
  );
}

/* ─── Stat card ──────────────────────────────────────────── */
function StatCard({
  label, value, sub, accent,
}: {
  label: string; value: string; sub?: string; accent?: string;
}) {
  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-1"
      style={{ background: "#1a1a24", border: "1px solid #2e2e3e" }}
    >
      <p className="text-xs font-medium uppercase tracking-wider" style={{ color: "#8888aa" }}>
        {label}
      </p>
      <p className="text-2xl font-bold" style={{ color: accent ?? "#e8e8f0" }}>
        {value}
      </p>
      {sub && <p className="text-xs" style={{ color: "#8888aa" }}>{sub}</p>}
    </div>
  );
}

/* ─── Smart Alert ────────────────────────────────────────── */
function SmartAlert({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div
      className="rounded-2xl px-5 py-3.5 mb-6 flex items-center justify-between gap-3"
      style={{ background: "#fbbf2415", border: "1px solid #fbbf2440" }}
    >
      <div className="flex items-center gap-2.5">
        <span className="text-lg">🔔</span>
        <p className="text-sm" style={{ color: "#fde68a" }}>{message}</p>
      </div>
      <button onClick={onDismiss} className="flex-shrink-0 text-xs opacity-50 hover:opacity-100" style={{ color: "#fde68a" }}>
        ✕
      </button>
    </div>
  );
}

/* ─── Savings Banner ─────────────────────────────────────── */
function SavingsBanner({ earned, spent, savings, savingsRate }: {
  earned: number; spent: number; savings: number; savingsRate: number;
}) {
  const isPositive = savings >= 0;
  return (
    <div
      className="rounded-2xl p-5 mb-8 flex flex-col sm:flex-row sm:items-center gap-4"
      style={{ background: "#1a1a24", border: "1px solid #2e2e3e" }}
    >
      <div className="flex-1">
        <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "#8888aa" }}>
          Income vs Expenses
        </p>
        <p className="text-sm leading-relaxed" style={{ color: "#c8c8e0" }}>
          You earned{" "}
          <span className="font-bold" style={{ color: "#4ade80" }}>{fmt(earned)}</span>
          {" "}and spent{" "}
          <span className="font-bold" style={{ color: "#f87171" }}>{fmt(spent)}</span>
          {" "}→ {isPositive ? "saved" : "overspent by"}{" "}
          <span className="font-bold" style={{ color: isPositive ? "#4ade80" : "#f87171" }}>
            {fmt(Math.abs(savings))}
          </span>
          {isPositive && (
            <span style={{ color: "#8888aa" }}> ({savingsRate}%)</span>
          )}
        </p>
      </div>
      <div className="flex gap-6">
        <div className="text-center">
          <p className="text-xs mb-1" style={{ color: "#8888aa" }}>Earned</p>
          <p className="text-lg font-bold" style={{ color: "#4ade80" }}>{fmt(earned)}</p>
        </div>
        <div className="text-center">
          <p className="text-xs mb-1" style={{ color: "#8888aa" }}>Spent</p>
          <p className="text-lg font-bold" style={{ color: "#f87171" }}>{fmt(spent)}</p>
        </div>
        <div className="text-center">
          <p className="text-xs mb-1" style={{ color: "#8888aa" }}>{isPositive ? "Saved" : "Over"}</p>
          <p className="text-lg font-bold" style={{ color: isPositive ? "#4ade80" : "#f87171" }}>
            {fmt(Math.abs(savings))}
          </p>
        </div>
      </div>
    </div>
  );
}

/* ─── Biggest Leak ───────────────────────────────────────── */
function BiggestLeakCard({ leak }: { leak: BiggestLeak }) {
  return (
    <div
      className="rounded-2xl p-5 mb-8 flex items-center gap-4"
      style={{ background: "#1a1a24", border: "1px solid #f8717130" }}
    >
      <span className="text-3xl flex-shrink-0">🔥</span>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: "#f87171" }}>
          Biggest Money Drain
        </p>
        <p className="text-base font-bold" style={{ color: "#e8e8f0" }}>
          {leak.merchant}{" "}
          <span style={{ color: "#f87171" }}>{fmt(leak.amount)}</span>
          <span className="text-sm font-normal ml-2" style={{ color: "#8888aa" }}>
            across {leak.count} transactions ({leak.pct}%)
          </span>
        </p>
      </div>
    </div>
  );
}

/* ─── Spending Score ─────────────────────────────────────── */
function SpendingScoreBadge({ score, label }: SpendingScore) {
  const color = scoreColor(score);
  return (
    <div className="flex items-center gap-2 flex-shrink-0">
      <div
        className="flex flex-col items-center justify-center rounded-2xl px-4 py-2"
        style={{ background: color + "15", border: `1px solid ${color}40` }}
      >
        <span className="text-2xl font-bold leading-none" style={{ color }}>
          {score}
        </span>
        <span className="text-xs mt-0.5" style={{ color: color + "cc" }}>/10</span>
      </div>
      <div>
        <p className="text-xs font-semibold" style={{ color }}>{label}</p>
        <p className="text-xs" style={{ color: "#8888aa" }}>Spending Score</p>
      </div>
    </div>
  );
}

/* ─── Personality banner ─────────────────────────────────── */
function PersonalityBanner({ traits }: { traits: PersonalityTrait[] }) {
  if (!traits.length) return null;
  return (
    <div
      className="rounded-2xl p-6 mb-8"
      style={{ background: "#1a1a24", border: "1px solid #2e2e3e" }}
    >
      <SectionHeading>Your Spending Personality</SectionHeading>
      <div className="flex flex-wrap gap-3">
        {traits.map((t) => {
          const color = PERSONALITY_COLORS[t.id] ?? "#7c6af7";
          return (
            <div key={t.id} className="flex-1 min-w-[200px]">
              <div
                className="inline-block text-xs font-bold px-3 py-1 rounded-full mb-2"
                style={{ background: color + "22", color, border: `1px solid ${color}55` }}
              >
                {t.label}
              </div>
              <p className="text-sm" style={{ color: "#c8c8e0" }}>{t.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Behavior + Leakage grid ────────────────────────────── */
function BehaviorCard({ item }: { item: BehaviorPattern | Leakage }) {
  return (
    <div
      className="rounded-2xl p-4 flex gap-3 items-start"
      style={{ background: "#1a1a24", border: "1px solid #2e2e3e" }}
    >
      <span className="text-xl flex-shrink-0">{item.icon}</span>
      <div>
        <p className="text-sm font-semibold mb-0.5" style={{ color: "#e8e8f0" }}>
          {item.title}
        </p>
        <p className="text-xs leading-relaxed" style={{ color: "#8888aa" }}>
          {item.detail}
        </p>
      </div>
    </div>
  );
}

/* ─── Suggestions ────────────────────────────────────────── */
function SuggestionsBlock({ suggestions }: { suggestions: Suggestion[] }) {
  if (!suggestions.length) return null;
  return (
    <div
      className="rounded-2xl p-6 mb-8"
      style={{ background: "#1a1a24", border: "1px solid #2e2e3e" }}
    >
      <SectionHeading>Actionable Suggestions</SectionHeading>
      <ul className="flex flex-col gap-3">
        {suggestions.map((s, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className="text-lg flex-shrink-0">{s.icon}</span>
            <p className="text-sm leading-relaxed" style={{ color: "#c8c8e0" }}>{s.text}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ─── AI Report ──────────────────────────────────────────── */
function AiReport({ report }: { report: LlmReport }) {
  return (
    <div
      className="rounded-2xl p-6 mb-8"
      style={{ background: "#1a1a24", border: "1px solid #2e2e3e" }}
    >
      <div className="flex items-center gap-2 mb-4">
        <span className="text-lg">✨</span>
        <SectionHeading>AI Analysis</SectionHeading>
        <span
          className="ml-auto text-xs px-2 py-0.5 rounded-full"
          style={{ background: "#7c6af720", color: "#a59bff", border: "1px solid #7c6af740" }}
        >
          AI
        </span>
      </div>
      <p className="text-sm leading-relaxed mb-5" style={{ color: "#c8c8e0" }}>
        {report.narrative}
      </p>
      {report.fun_facts.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "#8888aa" }}>
            Observations
          </p>
          <ul className="flex flex-col gap-2">
            {report.fun_facts.map((fact, i) => (
              <li key={i} className="flex items-start gap-2">
                <span
                  className="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold"
                  style={{ background: "#7c6af730", color: "#a59bff" }}
                >
                  {i + 1}
                </span>
                <span className="text-sm leading-relaxed" style={{ color: "#c8c8e0" }}>
                  {fact}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/* ─── Custom pie tooltip ─────────────────────────────────── */
const PieTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number }> }) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-xl px-3 py-2 text-sm shadow-lg"
      style={{ background: "#22222e", border: "1px solid #2e2e3e", color: "#e8e8f0" }}
    >
      <p className="font-medium">{payload[0].name}</p>
      <p style={{ color: "#a59bff" }}>{fmt(payload[0].value)}</p>
    </div>
  );
};

/* ─── Merchant Knowledge Graph ───────────────────────────── */
const COMMUNITY_COLORS = [
  "#7c6af7", "#f87171", "#4ade80", "#fbbf24",
  "#60a5fa", "#fb923c", "#34d399", "#a78bfa",
  "#f472b6", "#2dd4bf",
];

interface SimNode extends GraphNodeData {
  x: number; y: number;
  vx: number; vy: number;
  r: number;
}

function MerchantGraph({ graph }: { graph: GraphData }) {
  const frameRef = useRef<number>(0);
  const simRef = useRef<SimNode[]>([]);
  const nodeMapRef = useRef<Map<string, SimNode>>(new Map());
  const [nodes, setNodes] = useState<SimNode[]>([]);
  const [tooltip, setTooltip] = useState<{ node: SimNode; x: number; y: number } | null>(null);

  const W = 700, H = 400;

  useEffect(() => {
    if (!graph.nodes.length) return;
    const maxTotal = Math.max(...graph.nodes.map((n) => n.total), 1);

    const sim: SimNode[] = graph.nodes.map((n) => ({
      ...n,
      x: W / 2 + (Math.random() - 0.5) * 200,
      y: H / 2 + (Math.random() - 0.5) * 200,
      vx: 0, vy: 0,
      r: Math.max(14, Math.min(42, (n.total / maxTotal) * 42)),
    }));
    simRef.current = sim;
    const nm = new Map(sim.map((n) => [n.id, n]));
    nodeMapRef.current = nm;

    const tick = () => {
      const ns = simRef.current;
      const damping = 0.82, repulsion = 4000, springLen = 130, springK = 0.018, centerK = 0.006;
      ns.forEach((n) => { n.vx *= damping; n.vy *= damping; });
      ns.forEach((n) => { n.vx += (W / 2 - n.x) * centerK; n.vy += (H / 2 - n.y) * centerK; });
      for (let i = 0; i < ns.length; i++) {
        for (let j = i + 1; j < ns.length; j++) {
          const a = ns[i], b = ns[j];
          const dx = b.x - a.x || 0.01, dy = b.y - a.y || 0.01;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const f = repulsion / (dist * dist);
          a.vx -= (dx / dist) * f; a.vy -= (dy / dist) * f;
          b.vx += (dx / dist) * f; b.vy += (dy / dist) * f;
        }
      }
      graph.edges.forEach((e) => {
        const a = nm.get(e.source), b = nm.get(e.target);
        if (!a || !b) return;
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const f = (dist - springLen) * springK * Math.min(e.weight, 3);
        a.vx += (dx / dist) * f; a.vy += (dy / dist) * f;
        b.vx -= (dx / dist) * f; b.vy -= (dy / dist) * f;
      });
      ns.forEach((n) => {
        n.x = Math.max(n.r + 8, Math.min(W - n.r - 8, n.x + n.vx));
        n.y = Math.max(n.r + 8, Math.min(H - n.r - 8, n.y + n.vy));
      });
      setNodes([...ns]);
      frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
    const stop = setTimeout(() => cancelAnimationFrame(frameRef.current), 4000);
    return () => { cancelAnimationFrame(frameRef.current); clearTimeout(stop); };
  }, [graph]);

  if (!graph.nodes.length) return null;
  const nm = nodeMapRef.current;

  return (
    <div className="rounded-2xl p-5 mb-8" style={{ background: "#1a1a24", border: "1px solid #2e2e3e" }}>
      <div className="flex items-center gap-2 mb-1">
        <SectionHeading>Merchant Knowledge Graph</SectionHeading>
        <span
          className="ml-auto text-xs px-2 py-0.5 rounded-full mb-3"
          style={{ background: "#4ade8020", color: "#4ade80", border: "1px solid #4ade8040" }}
        >
          GraphNLP
        </span>
      </div>
      <p className="text-xs mb-4" style={{ color: "#8888aa" }}>
        Merchants used on the same day are connected · node size = spend · color = detected cluster
      </p>

      {/* Stats strip */}
      <div className="flex gap-6 mb-4">
        {[
          { label: "Merchants", value: graph.stats.total_merchants },
          { label: "Connections", value: graph.stats.total_connections },
          { label: "Clusters", value: graph.stats.num_communities },
          { label: "Hub", value: graph.stats.most_connected[0] ?? "—" },
        ].map((s) => (
          <div key={s.label}>
            <p className="text-base font-bold" style={{ color: "#e8e8f0" }}>{s.value}</p>
            <p className="text-xs" style={{ color: "#8888aa" }}>{s.label}</p>
          </div>
        ))}
      </div>

      {/* Force-directed graph */}
      <div className="relative overflow-hidden rounded-xl" style={{ background: "#0f0f13" }}>
        <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
          {graph.edges.map((e, i) => {
            const a = nm.get(e.source), b = nm.get(e.target);
            if (!a || !b) return null;
            return (
              <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke="#2e2e3e" strokeWidth={Math.min(3, e.weight)} strokeOpacity={0.7} />
            );
          })}
          {nodes.map((n) => {
            const color = COMMUNITY_COLORS[n.community % COMMUNITY_COLORS.length];
            return (
              <g key={n.id} style={{ cursor: "pointer" }}
                onMouseEnter={(ev) => setTooltip({ node: n, x: ev.clientX, y: ev.clientY })}
                onMouseLeave={() => setTooltip(null)}
              >
                <circle cx={n.x} cy={n.y} r={n.r} fill={color + "28"} stroke={color} strokeWidth={1.5} />
                {n.r >= 18 && (
                  <text x={n.x} y={n.y} textAnchor="middle" dominantBaseline="middle"
                    style={{ fontSize: Math.min(10, n.r * 0.45), fill: color, userSelect: "none", pointerEvents: "none" }}>
                    {n.id.length > 11 ? n.id.slice(0, 10) + "…" : n.id}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {tooltip && (
          <div className="fixed z-50 rounded-xl px-3 py-2 text-xs shadow-xl pointer-events-none"
            style={{ left: tooltip.x + 14, top: tooltip.y - 12,
              background: "#22222e", border: "1px solid #2e2e3e", color: "#e8e8f0" }}>
            <p className="font-semibold mb-0.5">{tooltip.node.id}</p>
            <p style={{ color: "#8888aa" }}>{tooltip.node.category}</p>
            <p style={{ color: "#a59bff" }}>{fmt(tooltip.node.total)} · {tooltip.node.count} txns</p>
            <p style={{ color: "#8888aa" }}>Centrality: {(tooltip.node.centrality * 100).toFixed(0)}%</p>
          </div>
        )}
      </div>

      {/* Cluster pills */}
      {graph.stats.communities?.length > 1 && (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "#8888aa" }}>
            Detected Clusters
          </p>
          <div className="flex flex-wrap gap-2">
            {graph.stats.communities.slice(0, 6).map((c) => {
              const color = COMMUNITY_COLORS[c.id % COMMUNITY_COLORS.length];
              return (
                <div key={c.id} className="flex items-center gap-1.5 rounded-full px-3 py-1 text-xs"
                  style={{ background: color + "18", border: `1px solid ${color}40`, color }}>
                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
                  {c.members.slice(0, 3).join(", ")}
                  {c.members.length > 3 && <span style={{ opacity: 0.6 }}> +{c.members.length - 3}</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Page ───────────────────────────────────────────────── */
async function downloadPdf(el: HTMLElement, filename: string) {
  const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
    import("jspdf"),
    import("html2canvas"),
  ]);

  const canvas = await html2canvas(el, {
    scale: 2,
    useCORS: true,
    backgroundColor: "#0f0f13",
  });

  const pdf = new jsPDF("p", "mm", "a4");
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  const imgW = pageW;
  const imgH = (canvas.height * pageW) / canvas.width;

  let remaining = imgH;
  let offset = 0;

  pdf.addImage(canvas.toDataURL("image/png"), "PNG", 0, offset, imgW, imgH);
  remaining -= pageH;

  while (remaining > 0) {
    offset -= pageH;
    pdf.addPage();
    pdf.addImage(canvas.toDataURL("image/png"), "PNG", 0, offset, imgW, imgH);
    remaining -= pageH;
  }

  pdf.save(filename);
}

export default function ResultsPage() {
  const [result, setResult] = useState<Result | null>(null);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [alertDismissed, setAlertDismissed] = useState(false);
  const [timelineView, setTimelineView] = useState(false);
  const reportRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  async function handleDownload() {
    if (!reportRef.current || !result) return;
    setDownloading(true);
    try {
      await downloadPdf(reportRef.current, "smart-spend-report.pdf");
    } finally {
      setDownloading(false);
    }
  }

  useEffect(() => {
    const raw = sessionStorage.getItem("smart-spend-result");
    if (!raw) { router.replace("/"); return; }
    setResult(JSON.parse(raw));
  }, [router]);

  if (!result) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ background: "#0f0f13", color: "#8888aa" }}>
        Loading…
      </div>
    );
  }

  const filteredTxns = result.transactions.filter((t) => {
    const matchesSearch =
      !search ||
      t.merchant.toLowerCase().includes(search.toLowerCase()) ||
      t.category.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = !activeCategory || t.category === activeCategory;
    return matchesSearch && matchesCategory;
  });

  const dowData = result.spend_by_dow.map((d) => ({ day: d.day.slice(0, 3), amount: d.amount }));

  return (
    <main className="flex-1 min-h-screen px-4 py-10" style={{ background: "#0f0f13" }}>
      <div className="max-w-5xl mx-auto" ref={reportRef}>

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: "#e8e8f0" }}>
              Your Spending Behavior
            </h1>
            <p className="text-sm mt-0.5" style={{ color: "#8888aa" }}>
              {result.transactions.length} transactions analysed
              {result.bank_name && ` · ${result.bank_name}`}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {result.spending_score && (
              <SpendingScoreBadge {...result.spending_score} />
            )}
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="rounded-xl px-4 py-2 text-sm font-medium flex items-center gap-2 transition-colors"
              style={{
                background: downloading ? "#2e2e3e" : "#7c6af7",
                color: downloading ? "#8888aa" : "#fff",
                cursor: downloading ? "not-allowed" : "pointer",
              }}
            >
              {downloading ? (
                "Generating…"
              ) : (
                <>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                    <path d="M12 16l-6-6h4V4h4v6h4l-6 6zM4 20h16v-2H4v2z" fill="currentColor"/>
                  </svg>
                  Download PDF
                </>
              )}
            </button>
            <button
              onClick={() => router.push("/")}
              className="rounded-xl px-4 py-2 text-sm font-medium"
              style={{ background: "#1a1a24", border: "1px solid #2e2e3e", color: "#8888aa" }}
            >
              ← New upload
            </button>
          </div>
        </div>

        {/* Smart Alert */}
        {result.smart_alert && !alertDismissed && (
          <SmartAlert message={result.smart_alert} onDismiss={() => setAlertDismissed(true)} />
        )}

        {/* Savings Banner */}
        {result.total_received > 0 && (
          <SavingsBanner
            earned={result.total_received}
            spent={result.total_spent}
            savings={result.savings}
            savingsRate={result.savings_rate}
          />
        )}

        {/* Biggest Leak */}
        {result.biggest_leak && (
          <BiggestLeakCard leak={result.biggest_leak} />
        )}

        {/* Spending Personality */}
        {result.personality?.length > 0 && (
          <PersonalityBanner traits={result.personality} />
        )}

        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          <StatCard
            label="Total Spent" value={fmt(result.total_spent)}
            sub={`${result.debit_count} transactions`} accent="#f87171"
          />
          <StatCard
            label="Total Received" value={fmt(result.total_received)}
            sub={`${result.credit_count} transactions`} accent="#4ade80"
          />
          <StatCard
            label="Top Merchant" value={result.top_merchant.name}
            sub={fmt(result.top_merchant.amount)}
          />
          <StatCard
            label="Biggest Day" value={fmt(result.biggest_spending_day.amount)}
            sub={fmtDate(result.biggest_spending_day.date)} accent="#fbbf24"
          />
        </div>

        {/* Behavior Patterns + Money Leakage */}
        {(result.behavior_patterns?.length > 0 || result.leakage?.length > 0) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            {result.behavior_patterns?.length > 0 && (
              <div>
                <SectionHeading>Behavior Patterns</SectionHeading>
                <div className="flex flex-col gap-3">
                  {result.behavior_patterns.map((p, i) => (
                    <BehaviorCard key={i} item={p} />
                  ))}
                </div>
              </div>
            )}
            {result.leakage?.length > 0 && (
              <div>
                <SectionHeading>Money Leakage</SectionHeading>
                <div className="flex flex-col gap-3">
                  {result.leakage.map((l, i) => (
                    <BehaviorCard key={i} item={l} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Actionable Suggestions */}
        {result.suggestions?.length > 0 && (
          <SuggestionsBlock suggestions={result.suggestions} />
        )}

        {/* Charts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {/* Pie chart */}
          <div
            className="rounded-2xl p-5"
            style={{ background: "#1a1a24", border: "1px solid #2e2e3e" }}
          >
            <SectionHeading>Spending by Category</SectionHeading>
            <div className="flex gap-4 items-center">
              <ResponsiveContainer width={160} height={160}>
                <PieChart>
                  <Pie
                    data={result.categories} dataKey="amount" nameKey="name"
                    cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={2}
                  >
                    {result.categories.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<PieTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-col gap-1.5 flex-1 min-w-0">
                {result.categories.slice(0, 6).map((c, i) => (
                  <button
                    key={c.name}
                    onClick={() => setActiveCategory(activeCategory === c.name ? null : c.name)}
                    className="flex items-center gap-2 text-xs w-full text-left rounded-lg px-2 py-1 transition-colors"
                    style={{ background: activeCategory === c.name ? "#22222e" : "transparent" }}
                  >
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                    <span className="truncate flex-1" style={{ color: "#e8e8f0" }}>{c.name}</span>
                    <span style={{ color: "#8888aa" }}>{c.pct}%</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Bar chart */}
          <div
            className="rounded-2xl p-5"
            style={{ background: "#1a1a24", border: "1px solid #2e2e3e" }}
          >
            <SectionHeading>Spend by Day of Week</SectionHeading>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={dowData} margin={{ top: 0, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2e2e3e" vertical={false} />
                <XAxis dataKey="day" tick={{ fill: "#8888aa", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis
                  tick={{ fill: "#8888aa", fontSize: 10 }}
                  axisLine={false} tickLine={false}
                  tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  formatter={(v) => [typeof v === "number" ? fmt(v) : v, "Spent"]}
                  contentStyle={{ background: "#22222e", border: "1px solid #2e2e3e", borderRadius: 12, color: "#e8e8f0", fontSize: 12 }}
                  cursor={{ fill: "#22222e" }}
                />
                <Bar dataKey="amount" fill="#7c6af7" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Report */}
        {result.llm_report && <AiReport report={result.llm_report} />}

        {/* Merchant Knowledge Graph */}
        {result.graph?.nlp_ready && result.graph.nodes.length > 0 && (
          <MerchantGraph graph={result.graph} />
        )}

        {/* Transactions */}
        <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid #2e2e3e" }}>
          <div
            className="px-5 py-4 flex items-center justify-between gap-3 flex-wrap"
            style={{ background: "#1a1a24", borderBottom: "1px solid #2e2e3e" }}
          >
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-sm" style={{ color: "#e8e8f0" }}>
                Transactions
              </h2>
              {activeCategory && (
                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{ background: "#7c6af730", color: "#a59bff" }}
                >
                  {activeCategory}
                  <button onClick={() => setActiveCategory(null)} className="ml-1 opacity-70 hover:opacity-100">×</button>
                </span>
              )}
              {/* View toggle */}
              <div
                className="flex rounded-lg overflow-hidden ml-2"
                style={{ border: "1px solid #2e2e3e" }}
              >
                {(["List", "Timeline"] as const).map((v) => (
                  <button
                    key={v}
                    onClick={() => setTimelineView(v === "Timeline")}
                    className="px-2.5 py-1 text-xs font-medium transition-colors"
                    style={{
                      background: (v === "Timeline") === timelineView ? "#2e2e3e" : "transparent",
                      color: (v === "Timeline") === timelineView ? "#e8e8f0" : "#8888aa",
                    }}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search merchant or category…"
              className="rounded-lg px-3 py-1.5 text-xs outline-none"
              style={{ background: "#22222e", border: "1px solid #2e2e3e", color: "#e8e8f0", width: 220 }}
            />
          </div>
          <div style={{ background: "#0f0f13" }}>
            {filteredTxns.length === 0 ? (
              <p className="text-sm text-center py-10" style={{ color: "#8888aa" }}>
                No transactions found.
              </p>
            ) : timelineView ? (
              // ── Timeline view ──────────────────────────────────────
              (() => {
                const byDate = filteredTxns.reduce<Record<string, Transaction[]>>((acc, t) => {
                  (acc[t.date] = acc[t.date] ?? []).push(t);
                  return acc;
                }, {});
                return Object.keys(byDate)
                  .sort((a, b) => b.localeCompare(a))
                  .map((date) => (
                    <div key={date}>
                      <div
                        className="px-5 py-2 text-xs font-semibold sticky top-0"
                        style={{ background: "#131318", color: "#8888aa", borderBottom: "1px solid #1a1a24" }}
                      >
                        {fmtDate(date)}
                        <span className="ml-2 font-normal">
                          {fmt(byDate[date].filter(t => t.type === "debit").reduce((s, t) => s + t.amount, 0))} spent
                        </span>
                      </div>
                      {byDate[date].map((t, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between px-5 py-3"
                          style={{ borderBottom: "1px solid #1a1a24" }}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div
                              className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold"
                              style={{ background: "#1a1a24", color: t.type === "credit" ? "#4ade80" : "#e8e8f0" }}
                            >
                              {t.merchant.charAt(0).toUpperCase()}
                            </div>
                            <div className="min-w-0">
                              <p className="text-sm font-medium truncate" style={{ color: "#e8e8f0" }}>{t.merchant}</p>
                              <p className="text-xs" style={{ color: "#8888aa" }}>{t.category}</p>
                            </div>
                          </div>
                          <p className="text-sm font-semibold flex-shrink-0 ml-4"
                            style={{ color: t.type === "credit" ? "#4ade80" : "#f87171" }}>
                            {t.type === "credit" ? "+" : "−"}{fmt(t.amount)}
                          </p>
                        </div>
                      ))}
                    </div>
                  ));
              })()
            ) : (
              // ── List view ──────────────────────────────────────────
              filteredTxns.map((t, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between px-5 py-3.5"
                  style={{ borderBottom: i < filteredTxns.length - 1 ? "1px solid #1a1a24" : "none" }}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold"
                      style={{ background: "#1a1a24", color: t.type === "credit" ? "#4ade80" : "#e8e8f0" }}
                    >
                      {t.merchant.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate" style={{ color: "#e8e8f0" }}>{t.merchant}</p>
                      <p className="text-xs" style={{ color: "#8888aa" }}>{t.category} · {fmtDate(t.date)}</p>
                    </div>
                  </div>
                  <p className="text-sm font-semibold flex-shrink-0 ml-4"
                    style={{ color: t.type === "credit" ? "#4ade80" : "#f87171" }}>
                    {t.type === "credit" ? "+" : "−"}{fmt(t.amount)}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
