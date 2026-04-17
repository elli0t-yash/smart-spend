"use client";

import { useEffect, useState } from "react";
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

interface LlmReport {
  narrative: string;
  fun_facts: string[];
}

interface Result {
  total_spent: number;
  total_received: number;
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
}

/* ─── Helpers ────────────────────────────────────────────── */
const COLORS = [
  "#7c6af7", "#a59bff", "#4ade80", "#fbbf24",
  "#f87171", "#60a5fa", "#34d399", "#fb923c",
];

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

/* ─── Stat card ──────────────────────────────────────────── */
function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
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
      {sub && (
        <p className="text-xs" style={{ color: "#8888aa" }}>
          {sub}
        </p>
      )}
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
        <h2
          className="text-sm font-semibold uppercase tracking-wider"
          style={{ color: "#8888aa" }}
        >
          AI Analysis
        </h2>
        <span
          className="ml-auto text-xs px-2 py-0.5 rounded-full"
          style={{ background: "#7c6af720", color: "#a59bff", border: "1px solid #7c6af740" }}
        >
          Claude
        </span>
      </div>

      <p className="text-sm leading-relaxed mb-5" style={{ color: "#c8c8e0" }}>
        {report.narrative}
      </p>

      {report.fun_facts.length > 0 && (
        <div>
          <p
            className="text-xs font-semibold uppercase tracking-wider mb-3"
            style={{ color: "#8888aa" }}
          >
            Interesting Facts
          </p>
          <ul className="flex flex-col gap-2">
            {report.fun_facts.map((fact, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold"
                  style={{ background: "#7c6af730", color: "#a59bff" }}>
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

/* ─── Insight card ───────────────────────────────────────── */
function InsightCardUI({ card }: { card: InsightCard }) {
  return (
    <div
      className="rounded-2xl p-5"
      style={{ background: "#1a1a24", border: "1px solid #2e2e3e" }}
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl">{card.icon}</span>
        <div>
          <p className="font-semibold text-sm mb-1" style={{ color: "#e8e8f0" }}>
            {card.title}
          </p>
          <p className="text-sm leading-relaxed" style={{ color: "#8888aa" }}>
            {card.body}
          </p>
        </div>
      </div>
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

/* ─── Page ───────────────────────────────────────────────── */
export default function ResultsPage() {
  const [result, setResult] = useState<Result | null>(null);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const raw = sessionStorage.getItem("smart-spend-result");
    if (!raw) {
      router.replace("/");
      return;
    }
    setResult(JSON.parse(raw));
  }, [router]);

  if (!result) {
    return (
      <div
        className="flex-1 flex items-center justify-center"
        style={{ background: "#0f0f13", color: "#8888aa" }}
      >
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

  const dowData = result.spend_by_dow.map((d) => ({
    day: d.day.slice(0, 3),
    amount: d.amount,
  }));

  return (
    <main
      className="flex-1 min-h-screen px-4 py-10"
      style={{ background: "#0f0f13" }}
    >
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: "#e8e8f0" }}>
              Your Spending Insights
            </h1>
            <p className="text-sm mt-0.5" style={{ color: "#8888aa" }}>
              {result.transactions.length} transactions analysed
            </p>
          </div>
          <button
            onClick={() => router.push("/")}
            className="rounded-xl px-4 py-2 text-sm font-medium transition-colors"
            style={{
              background: "#1a1a24",
              border: "1px solid #2e2e3e",
              color: "#8888aa",
            }}
          >
            ← New upload
          </button>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          <StatCard
            label="Total Spent"
            value={fmt(result.total_spent)}
            sub={`${result.debit_count} transactions`}
            accent="#f87171"
          />
          <StatCard
            label="Total Received"
            value={fmt(result.total_received)}
            sub={`${result.credit_count} transactions`}
            accent="#4ade80"
          />
          <StatCard
            label="Top Merchant"
            value={result.top_merchant.name}
            sub={fmt(result.top_merchant.amount)}
          />
          <StatCard
            label="Biggest Day"
            value={fmt(result.biggest_spending_day.amount)}
            sub={fmtDate(result.biggest_spending_day.date)}
            accent="#fbbf24"
          />
        </div>

        {/* Charts + Insights row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {/* Pie chart */}
          <div
            className="rounded-2xl p-5"
            style={{ background: "#1a1a24", border: "1px solid #2e2e3e" }}
          >
            <h2
              className="text-sm font-semibold uppercase tracking-wider mb-4"
              style={{ color: "#8888aa" }}
            >
              Spending by Category
            </h2>
            <div className="flex gap-4 items-center">
              <ResponsiveContainer width={160} height={160}>
                <PieChart>
                  <Pie
                    data={result.categories}
                    dataKey="amount"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={75}
                    paddingAngle={2}
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
                    onClick={() =>
                      setActiveCategory(
                        activeCategory === c.name ? null : c.name
                      )
                    }
                    className="flex items-center gap-2 text-xs w-full text-left rounded-lg px-2 py-1 transition-colors"
                    style={{
                      background:
                        activeCategory === c.name ? "#22222e" : "transparent",
                    }}
                  >
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ background: COLORS[i % COLORS.length] }}
                    />
                    <span
                      className="truncate flex-1"
                      style={{ color: "#e8e8f0" }}
                    >
                      {c.name}
                    </span>
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
            <h2
              className="text-sm font-semibold uppercase tracking-wider mb-4"
              style={{ color: "#8888aa" }}
            >
              Spend by Day of Week
            </h2>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={dowData} margin={{ top: 0, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#2e2e3e"
                  vertical={false}
                />
                <XAxis
                  dataKey="day"
                  tick={{ fill: "#8888aa", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#8888aa", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  formatter={(v) => [typeof v === "number" ? fmt(v) : v, "Spent"]}
                  contentStyle={{
                    background: "#22222e",
                    border: "1px solid #2e2e3e",
                    borderRadius: 12,
                    color: "#e8e8f0",
                    fontSize: 12,
                  }}
                  cursor={{ fill: "#22222e" }}
                />
                <Bar dataKey="amount" fill="#7c6af7" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Report */}
        {result.llm_report && <AiReport report={result.llm_report} />}

        {/* Insight cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-8">
          {result.insights.map((card, i) => (
            <InsightCardUI key={i} card={card} />
          ))}
        </div>

        {/* Transactions */}
        <div
          className="rounded-2xl overflow-hidden"
          style={{ border: "1px solid #2e2e3e" }}
        >
          <div
            className="px-5 py-4 flex items-center justify-between"
            style={{ background: "#1a1a24", borderBottom: "1px solid #2e2e3e" }}
          >
            <h2 className="font-semibold text-sm" style={{ color: "#e8e8f0" }}>
              Transactions
              {activeCategory && (
                <span
                  className="ml-2 text-xs px-2 py-0.5 rounded-full"
                  style={{ background: "#7c6af730", color: "#a59bff" }}
                >
                  {activeCategory}
                  <button
                    onClick={() => setActiveCategory(null)}
                    className="ml-1 opacity-70 hover:opacity-100"
                  >
                    ×
                  </button>
                </span>
              )}
            </h2>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search merchant or category…"
              className="rounded-lg px-3 py-1.5 text-xs outline-none"
              style={{
                background: "#22222e",
                border: "1px solid #2e2e3e",
                color: "#e8e8f0",
                width: 220,
              }}
            />
          </div>
          <div style={{ background: "#0f0f13" }}>
            {filteredTxns.length === 0 ? (
              <p
                className="text-sm text-center py-10"
                style={{ color: "#8888aa" }}
              >
                No transactions found.
              </p>
            ) : (
              filteredTxns.map((t, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between px-5 py-3.5 transition-colors"
                  style={{
                    borderBottom:
                      i < filteredTxns.length - 1
                        ? "1px solid #1a1a24"
                        : "none",
                  }}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold"
                      style={{
                        background: "#1a1a24",
                        color: t.type === "credit" ? "#4ade80" : "#e8e8f0",
                      }}
                    >
                      {t.merchant.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p
                        className="text-sm font-medium truncate"
                        style={{ color: "#e8e8f0" }}
                      >
                        {t.merchant}
                      </p>
                      <p className="text-xs" style={{ color: "#8888aa" }}>
                        {t.category} · {fmtDate(t.date)}
                      </p>
                    </div>
                  </div>
                  <p
                    className="text-sm font-semibold flex-shrink-0 ml-4"
                    style={{ color: t.type === "credit" ? "#4ade80" : "#f87171" }}
                  >
                    {t.type === "credit" ? "+" : "−"}
                    {fmt(t.amount)}
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
