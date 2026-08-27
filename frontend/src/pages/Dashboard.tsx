import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowUpRight,
  BadgeCheck,
  CircleDollarSign,
  Gauge,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Bar, BarChart, XAxis, YAxis, Tooltip } from "recharts";
import { api, type Overview } from "@/lib/api";
import { Button, Card, DemoBanner, RiskBadge, Skeleton } from "@/components/ui";
import { fmtMoney, fmtNum, fmtPct, RISK_COLORS } from "@/lib/utils";

const kpiMeta = [
  { key: "transactions_analyzed", label: "Transactions Analyzed", icon: BadgeCheck, money: false, pct: false },
  { key: "high_risk_transactions", label: "High-Risk Transactions", icon: ShieldAlert, money: false, pct: false },
  { key: "fraud_prevented", label: "Fraud Prevented", icon: AlertTriangle, money: false, pct: false },
  { key: "estimated_loss_avoided", label: "Estimated Loss Avoided", icon: CircleDollarSign, money: true, pct: false },
  { key: "model_precision", label: "Model Precision", icon: Gauge, money: false, pct: true },
  { key: "model_recall", label: "Model Recall", icon: TrendingUp, money: false, pct: true },
] as const;

export default function Dashboard() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.overview().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) {
    return <Card className="text-rose-300">Unable to load dashboard. Is the backend running on port 8000? {error}</Card>;
  }
  if (!data) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    );
  }

  const hero = data.hero;
  const dist = data.risk_distribution?.items || [];

  return (
    <div>
      <DemoBanner show={data.is_demo} />
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] tracking-wide text-slate-300">
            <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_10px_#34d399]" />
            MODEL ONLINE
          </div>
          <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">AI-Powered Risk Intelligence</h1>
          <p className="mt-2 max-w-2xl text-slate-400">Detect suspicious financial activity before it becomes a loss.</p>
        </div>
        <div className="flex gap-3">
          <Link to="/analyzer">
            <Button>Analyze Transaction</Button>
          </Link>
          <Link to="/performance">
            <Button variant="ghost">View Model Performance</Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {kpiMeta.map((k, i) => {
          const raw = (data.kpis as any)?.[k.key];
          const value = k.pct ? fmtPct(raw) : k.money ? fmtMoney(raw) : fmtNum(raw);
          const trend = data.kpis.trends?.[k.key] ?? 0;
          const Icon = k.icon;
          return (
            <motion.div key={k.key} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
              <Card className="group hover:border-cyan-400/20">
                <div className="flex items-start justify-between">
                  <div className="rounded-xl bg-cyan-400/10 p-2 text-cyan-300">
                    <Icon size={18} />
                  </div>
                  <span className={`flex items-center text-xs ${trend >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                    <ArrowUpRight size={14} className={trend < 0 ? "rotate-180" : ""} />
                    {Math.abs(trend).toFixed(1)}%
                  </span>
                </div>
                <div className="mt-4 font-mono text-3xl font-semibold">{value}</div>
                <div className="mt-1 text-sm text-slate-400">{k.label}</div>
              </Card>
            </motion.div>
          );
        })}
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-1 flex flex-col items-center justify-center text-center">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Risk Score</div>
          <div className="mt-3 font-mono text-7xl font-semibold text-cyan-200">
            {data.kpis.average_risk_score?.toFixed(0) ?? "—"}
          </div>
          <div className="mt-2">
            <RiskBadge
              level={
                (data.kpis.average_risk_score ?? 0) >= 75
                  ? "CRITICAL"
                  : (data.kpis.average_risk_score ?? 0) >= 50
                    ? "HIGH"
                    : (data.kpis.average_risk_score ?? 0) >= 25
                      ? "MEDIUM"
                      : "LOW"
              }
            />
          </div>
          <p className="mt-3 text-sm text-slate-400">
            {data.spike?.detected
              ? "Risk spike detected — manual review recommended"
              : (data.kpis.average_risk_score ?? 0) >= 50
                ? "Manual review recommended for elevated clusters"
                : "Portfolio currently within modeled operating range"}
          </p>
          <div className="mt-5 grid w-full grid-cols-3 gap-2 text-xs text-slate-400">
            <div>Precision<br /><span className="font-mono text-slate-100">{fmtPct(hero?.precision)}</span></div>
            <div>Recall<br /><span className="font-mono text-slate-100">{fmtPct(hero?.recall)}</span></div>
            <div>F1<br /><span className="font-mono text-slate-100">{fmtPct(hero?.f1)}</span></div>
          </div>
        </Card>

        <Card className="xl:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Risk Overview</h2>
            <span className="text-xs text-slate-500">{fmtNum(data.risk_distribution.n)} scored transactions</span>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="h-64">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={dist} dataKey="count" nameKey="level" innerRadius={62} outerRadius={90} paddingAngle={3}>
                    {dist.map((d) => (
                      <Cell key={d.level} fill={RISK_COLORS[d.level]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#0c1222", border: "1px solid #1f2937" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={dist}>
                  <XAxis dataKey="level" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} />
                  <Tooltip contentStyle={{ background: "#0c1222", border: "1px solid #1f2937" }} />
                  <Bar dataKey="pct" radius={[8, 8, 0, 0]}>
                    {dist.map((d) => (
                      <Cell key={d.level} fill={RISK_COLORS[d.level]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-4 gap-2 text-center text-xs">
            {dist.map((d) => (
              <div key={d.level} className="rounded-xl bg-white/5 py-2">
                <div className="text-slate-400">{d.level}</div>
                <div className="font-mono text-slate-100">{d.pct.toFixed(1)}%</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {data.spike && (
        <Card className={`mt-6 ${data.spike.detected ? "border-rose-400/30" : "border-white/10"}`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-400">Fraud Spike Sentinel</div>
              <h3 className={`text-xl font-semibold ${data.spike.detected ? "text-rose-300" : "text-slate-100"}`}>
                {data.spike.detected ? "⚠ RISK SPIKE DETECTED" : "No abnormal spike in the latest window"}
              </h3>
            </div>
            <Link to="/alerts"><Button variant="ghost">Open Alerts</Button></Link>
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5 text-sm">
            <Stat label="Detection time" value={new Date(data.spike.detection_time).toLocaleString()} />
            <Stat label="Current risk rate" value={fmtPct(data.spike.current_risk_rate)} />
            <Stat label="Expected baseline" value={fmtPct(data.spike.expected_baseline)} />
            <Stat label="Deviation (z)" value={data.spike.deviation_z.toFixed(2)} />
            <Stat label="Affected txns" value={fmtNum(data.spike.affected_transactions)} />
          </div>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="font-mono text-slate-100">{value}</div>
    </div>
  );
}
