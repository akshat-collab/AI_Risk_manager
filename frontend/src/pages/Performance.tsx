import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { api } from "@/lib/api";
import { Card, DemoBanner } from "@/components/ui";
import { fmtPct } from "@/lib/utils";

export default function Performance() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api.performance().then(setData);
  }, []);
  if (!data) return <Card>Loading held-out evaluation…</Card>;

  const best = data.models[data.best_model];
  const test = best.test;
  const cm = test.confusion_matrix;
  const roc = data.curves.roc.fpr.map((fpr: number, i: number) => ({ fpr, tpr: data.curves.roc.tpr[i] }));
  const pr = data.curves.pr.recall.map((recall: number, i: number) => ({ recall, precision: data.curves.pr.precision[i] }));

  return (
    <div>
      <h1 className="text-3xl font-semibold">Model Performance</h1>
      <p className="mt-2 text-slate-400">
        Best model is selected on validation F1 / PR-AUC, then reported on a completely held-out test set. Numbers are calculated, not hard-coded.
      </p>
      <DemoBanner show={data.is_demo} />

      <div className="mt-4 text-sm text-slate-400">
        Selected model: <span className="text-cyan-200">{data.best_model}</span> · threshold {fmtPct(data.threshold)} ·
        train {data.split.train} / val {data.split.validation} / test {data.split.test}
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Accuracy" value={fmtPct(test.accuracy)} />
        <Metric label="Precision" value={fmtPct(test.precision)} />
        <Metric label="Recall" value={fmtPct(test.recall)} />
        <Metric label="F1 Score" value={fmtPct(test.f1)} />
        <Metric label="ROC-AUC" value={fmtPct(test.roc_auc)} />
        <Metric label="PR-AUC" value={fmtPct(test.pr_auc)} />
        <Metric label="Specificity" value={fmtPct(test.specificity)} />
        <Metric label="False Positive Rate" value={fmtPct(test.false_positive_rate)} />
        <Metric label="False Negative Rate" value={fmtPct(test.false_negative_rate)} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Card>
          <h2 className="mb-4 text-lg font-semibold">Confusion Matrix (test)</h2>
          <div className="grid grid-cols-2 gap-3">
            <CmCell label="True Negative" value={cm.true_negative} tone="ok" />
            <CmCell label="False Positive" value={cm.false_positive} tone="warn" />
            <CmCell label="False Negative" value={cm.false_negative} tone="bad" />
            <CmCell label="True Positive" value={cm.true_positive} tone="ok" />
          </div>
        </Card>
        <Card>
          <h2 className="mb-4 text-lg font-semibold">Split honesty</h2>
          <ul className="space-y-2 text-sm text-slate-300">
            <li>Training F1: {fmtPct(best.train.f1)}</li>
            <li>Validation F1: {fmtPct(best.validation.f1)}</li>
            <li>Test F1: {fmtPct(best.test.f1)}</li>
            <li>Training fraud rate: {fmtPct(Number(data.split.train_fraud_rate))}</li>
            <li>Test fraud rate: {fmtPct(Number(data.split.test_fraud_rate))}</li>
            <li className="text-slate-500">{data.split.strategy}</li>
          </ul>
        </Card>
        <Card>
          <h2 className="mb-4 text-lg font-semibold">ROC Curve</h2>
          <div className="h-64">
            <ResponsiveContainer>
              <LineChart data={roc}>
                <CartesianGrid stroke="rgba(148,163,184,0.08)" />
                <XAxis dataKey="fpr" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip contentStyle={{ background: "#0c1222", border: "1px solid #1f2937" }} />
                <Line type="monotone" dataKey="tpr" stroke="#22d3ee" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <h2 className="mb-4 text-lg font-semibold">Precision-Recall Curve</h2>
          <div className="h-64">
            <ResponsiveContainer>
              <LineChart data={pr}>
                <CartesianGrid stroke="rgba(148,163,184,0.08)" />
                <XAxis dataKey="recall" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip contentStyle={{ background: "#0c1222", border: "1px solid #1f2937" }} />
                <Line type="monotone" dataKey="precision" stroke="#34d399" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card className="mt-6">
        <h2 className="mb-4 text-lg font-semibold">Model Comparison (held-out test)</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="pb-3 text-left">Model</th>
                <th className="pb-3">Precision</th>
                <th className="pb-3">Recall</th>
                <th className="pb-3">F1</th>
                <th className="pb-3">ROC-AUC</th>
                <th className="pb-3">PR-AUC</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.models).map(([name, m]: any) => (
                <tr key={name} className="border-t border-white/5">
                  <td className="py-3">{name}{name === data.best_model ? " ★" : ""}</td>
                  <td className="text-center">{fmtPct(m.test.precision)}</td>
                  <td className="text-center">{fmtPct(m.test.recall)}</td>
                  <td className="text-center">{fmtPct(m.test.f1)}</td>
                  <td className="text-center">{fmtPct(m.test.roc_auc)}</td>
                  <td className="text-center">{fmtPct(m.test.pr_auc)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 font-mono text-2xl">{value}</div>
    </Card>
  );
}

function CmCell({ label, value, tone }: { label: string; value: number; tone: "ok" | "warn" | "bad" }) {
  const color = tone === "ok" ? "text-emerald-300" : tone === "warn" ? "text-amber-300" : "text-rose-300";
  return (
    <div className="rounded-xl bg-white/5 p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`mt-1 font-mono text-3xl ${color}`}>{value}</div>
    </div>
  );
}
