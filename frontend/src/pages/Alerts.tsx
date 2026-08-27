import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, DemoBanner } from "@/components/ui";
import { fmtPct, fmtTime } from "@/lib/utils";

const tone: Record<string, string> = {
  red: "border-rose-400/30 bg-rose-400/10",
  orange: "border-orange-400/30 bg-orange-400/10",
  yellow: "border-amber-400/30 bg-amber-400/10",
  blue: "border-cyan-400/30 bg-cyan-400/10",
};

export default function Alerts() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api.alerts().then(setData);
  }, []);
  if (!data) return <Card>Loading alerts…</Card>;

  return (
    <div>
      <h1 className="text-3xl font-semibold">Risk Alerts</h1>
      <p className="mt-2 text-slate-400">Defensive notifications only. This module reports suspicious activity; it does not exploit payment systems.</p>
      <DemoBanner show={data.is_demo} />

      {data.spike && (
        <Card className={`mt-5 ${data.spike.detected ? "border-rose-400/40" : ""}`}>
          <div className="text-xs uppercase tracking-wide text-slate-400">Fraud Spike Sentinel</div>
          <h2 className="mt-1 text-2xl font-semibold">{data.spike.detected ? "⚠ RISK SPIKE DETECTED" : data.spike.title}</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5 text-sm">
            <div>Time<div className="font-mono text-slate-100">{fmtTime(data.spike.detection_time)}</div></div>
            <div>Current rate<div className="font-mono text-slate-100">{fmtPct(data.spike.current_risk_rate)}</div></div>
            <div>Baseline<div className="font-mono text-slate-100">{fmtPct(data.spike.expected_baseline)}</div></div>
            <div>Deviation<div className="font-mono text-slate-100">{data.spike.deviation_z}</div></div>
            <div>Affected<div className="font-mono text-slate-100">{data.spike.affected_transactions}</div></div>
          </div>
        </Card>
      )}

      <div className="mt-6 space-y-3">
        {data.items.map((a: any) => (
          <Card key={a.id} className={tone[a.color] || ""}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-semibold">{a.title}</div>
              <div className="text-xs text-slate-400">{a.severity} · {fmtTime(a.timestamp)}</div>
            </div>
            <p className="mt-2 text-sm text-slate-200">{a.description}</p>
            <p className="mt-2 text-sm text-cyan-200">Recommended action: {a.recommended_action}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
