import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { api } from "@/lib/api";
import { Card, DemoBanner, Input, Label } from "@/components/ui";
import { fmtMoney, fmtPct } from "@/lib/utils";

export default function CostAnalysis() {
  const [fp, setFp] = useState(25);
  const [fn, setFn] = useState(250);
  const [avg, setAvg] = useState(120);
  const [threshold, setThreshold] = useState(0.5);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const q = new URLSearchParams({
      cost_false_positive: String(fp),
      cost_false_negative: String(fn),
      average_transaction_value: String(avg),
      threshold: String(threshold),
    });
    api.cost(q.toString()).then(setData);
  }, [fp, fn, avg, threshold]);

  if (!data) return <Card>Loading cost analysis…</Card>;
  const s = data.selected;

  return (
    <div>
      <h1 className="text-3xl font-semibold">Business Cost Analysis</h1>
      <p className="mt-2 max-w-3xl text-slate-400">
        False positives can incorrectly flag legitimate customers. Move the threshold to see how precision, recall, and expected cost change on the held-out test set.
      </p>
      <DemoBanner show={data.is_demo} />

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <Card>
          <Label>Cost of false positive</Label>
          <Input type="number" min={0} value={fp} onChange={(e) => setFp(Number(e.target.value))} />
        </Card>
        <Card>
          <Label>Cost of false negative</Label>
          <Input type="number" min={0} value={fn} onChange={(e) => setFn(Number(e.target.value))} />
        </Card>
        <Card>
          <Label>Average transaction value</Label>
          <Input type="number" min={0} value={avg} onChange={(e) => setAvg(Number(e.target.value))} />
        </Card>
      </div>

      <Card className="mt-6">
        <Label>Risk threshold ({threshold.toFixed(2)})</Label>
        <input
          type="range"
          min={0.05}
          max={0.95}
          step={0.025}
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
          className="w-full accent-cyan-400"
        />
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <CostTile label="Estimated False-Positive Cost" value={fmtMoney(s.fp_cost)} />
          <CostTile label="Estimated False-Negative Cost" value={fmtMoney(s.fn_cost)} />
          <CostTile label="Total Expected Risk Cost" value={fmtMoney(s.total_cost)} accent />
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm text-slate-400 md:grid-cols-4">
          <div>Precision <span className="block font-mono text-slate-100">{fmtPct(s.precision)}</span></div>
          <div>Recall <span className="block font-mono text-slate-100">{fmtPct(s.recall)}</span></div>
          <div>False positives <span className="block font-mono text-slate-100">{s.false_positives}</span></div>
          <div>False negatives <span className="block font-mono text-slate-100">{s.false_negatives}</span></div>
        </div>
      </Card>

      <Card className="mt-6">
        <h2 className="mb-4 text-lg font-semibold">Risk Threshold vs Expected Cost</h2>
        <div className="h-80">
          <ResponsiveContainer>
            <LineChart data={data.curve}>
              <CartesianGrid stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey="threshold" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip contentStyle={{ background: "#0c1222", border: "1px solid #1f2937" }} />
              <Line type="monotone" dataKey="total_cost" stroke="#22d3ee" dot={false} />
              <Line type="monotone" dataKey="fp_cost" stroke="#fbbf24" dot={false} />
              <Line type="monotone" dataKey="fn_cost" stroke="#fb7185" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        {data.recommended && (
          <p className="mt-3 text-sm text-slate-400">
            Lowest-cost threshold on this test set: {data.recommended.threshold} ({fmtMoney(data.recommended.total_cost)}).
            This is a simulated policy suggestion, not an automatic block.
          </p>
        )}
      </Card>
    </div>
  );
}

function CostTile({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`rounded-xl p-4 ${accent ? "bg-cyan-400/10" : "bg-white/5"}`}>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 font-mono text-2xl">{value}</div>
    </div>
  );
}
