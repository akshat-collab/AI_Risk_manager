import { useEffect, useState } from "react";
import { api, type Prediction } from "@/lib/api";
import { Button, Card, DemoBanner, Input, Label, RiskBadge, Select } from "@/components/ui";
import { fmtPct } from "@/lib/utils";

const defaultForm = {
  amount: 420,
  hour: 14,
  customer_age: 34,
  account_age_days: 420,
  num_transactions: 28,
  previous_chargebacks: 0,
  previous_returns: 1,
  device_type: "mobile",
  payment_method: "credit_card",
  location: "US-CA",
  transaction_frequency: 3.2,
  failed_payment_attempts: 0,
  is_new_device: false,
  days_since_last_transaction: 4,
  avg_transaction_amount: 95,
  merchant_category: "electronics",
};

export default function Analyzer() {
  const [form, setForm] = useState(defaultForm);
  const [options, setOptions] = useState<{ device_types: string[]; payment_methods: string[]; locations: string[]; merchant_categories: string[] } | null>(null);
  const [result, setResult] = useState<Prediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.options().then(setOptions).catch(() => null);
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.predict(form);
      setResult(res);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const set = (key: string, value: string | number | boolean) => setForm((f) => ({ ...f, [key]: value }));

  return (
    <div>
      <h1 className="text-3xl font-semibold">Transaction Risk Analyzer</h1>
      <p className="mt-2 text-slate-400">Score a single transaction with the currently deployed model. This is decision support — not an automatic block.</p>
      {result && <DemoBanner show={result.is_demo} />}

      <div className="mt-6 grid gap-6 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <form onSubmit={onSubmit} className="grid gap-4 md:grid-cols-2">
            <Field label="Transaction amount">
              <Input type="number" min={0} max={1_000_000_000} value={form.amount} onChange={(e) => set("amount", Number(e.target.value))} />
            </Field>
            <Field label="Transaction hour (0-23)">
              <Input type="number" min={0} max={23} value={form.hour} onChange={(e) => set("hour", Number(e.target.value))} />
            </Field>
            <Field label="Customer age">
              <Input type="number" min={18} value={form.customer_age} onChange={(e) => set("customer_age", Number(e.target.value))} />
            </Field>
            <Field label="Account age (days)">
              <Input type="number" min={0} value={form.account_age_days} onChange={(e) => set("account_age_days", Number(e.target.value))} />
            </Field>
            <Field label="Number of transactions">
              <Input type="number" min={0} value={form.num_transactions} onChange={(e) => set("num_transactions", Number(e.target.value))} />
            </Field>
            <Field label="Previous chargebacks">
              <Input type="number" min={0} value={form.previous_chargebacks} onChange={(e) => set("previous_chargebacks", Number(e.target.value))} />
            </Field>
            <Field label="Previous returns">
              <Input type="number" min={0} value={form.previous_returns} onChange={(e) => set("previous_returns", Number(e.target.value))} />
            </Field>
            <Field label="Transaction frequency">
              <Input type="number" step="0.1" min={0} value={form.transaction_frequency} onChange={(e) => set("transaction_frequency", Number(e.target.value))} />
            </Field>
            <Field label="Failed payment attempts">
              <Input type="number" min={0} value={form.failed_payment_attempts} onChange={(e) => set("failed_payment_attempts", Number(e.target.value))} />
            </Field>
            <Field label="Days since last transaction">
              <Input type="number" min={0} value={form.days_since_last_transaction} onChange={(e) => set("days_since_last_transaction", Number(e.target.value))} />
            </Field>
            <Field label="Avg transaction amount">
              <Input type="number" min={0} value={form.avg_transaction_amount} onChange={(e) => set("avg_transaction_amount", Number(e.target.value))} />
            </Field>
            <Field label="Device type">
              <Select value={form.device_type} onChange={(e) => set("device_type", e.target.value)}>
                {(options?.device_types || ["mobile", "desktop", "tablet"]).map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </Select>
            </Field>
            <Field label="Payment method">
              <Select value={form.payment_method} onChange={(e) => set("payment_method", e.target.value)}>
                {(options?.payment_methods || ["credit_card"]).map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </Select>
            </Field>
            <Field label="Location">
              <Select value={form.location} onChange={(e) => set("location", e.target.value)}>
                {(options?.locations || ["US-CA"]).map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </Select>
            </Field>
            <Field label="Merchant category">
              <Select value={form.merchant_category} onChange={(e) => set("merchant_category", e.target.value)}>
                {(options?.merchant_categories || ["electronics"]).map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </Select>
            </Field>
            <label className="mt-6 flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={form.is_new_device} onChange={(e) => set("is_new_device", e.target.checked)} />
              New device
            </label>
            <div className="md:col-span-2 mt-2">
              <Button type="submit" className="w-full py-3 text-base" disabled={loading}>
                {loading ? "Analyzing…" : "ANALYZE RISK"}
              </Button>
            </div>
          </form>
          {error && <p className="mt-3 text-sm text-rose-300">{error}</p>}
        </Card>

        <div className="xl:col-span-2 space-y-4">
          <Card className="text-center">
            <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Risk Score</div>
            <div className="mt-2 font-mono text-6xl font-semibold text-cyan-200">
              {result ? result.risk_score.toFixed(0) : "—"}
              <span className="text-2xl text-slate-500"> / 100</span>
            </div>
            <div className="mt-3">{result ? <RiskBadge level={result.risk_level} /> : <span className="text-slate-500">Awaiting analysis</span>}</div>
            <p className="mt-3 text-sm text-slate-300">{result?.recommendation || "Submit a transaction to receive a defensive recommendation."}</p>
            {result && (
              <p className="mt-2 text-xs text-slate-500">
                Probability {fmtPct(result.probability)} · threshold {fmtPct(result.threshold)} · {result.model}
              </p>
            )}
          </Card>
          <Card>
            <h2 className="text-lg font-semibold">Why was this transaction flagged?</h2>
            <p className="mt-1 text-xs text-slate-500">Model-derived indicators, not absolute proof of fraud.</p>
            <div className="mt-4 space-y-3">
              {!result && <p className="text-sm text-slate-500">Explanations appear after a prediction.</p>}
              {result?.explanations.map((ex) => (
                <div key={ex.feature} className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-medium">{ex.title}</div>
                    <span className={ex.direction === "increases_risk" ? "text-rose-300 text-xs" : "text-emerald-300 text-xs"}>
                      {ex.direction === "increases_risk" ? "↑ risk" : "↓ risk"}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-400">{ex.detail}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <Label>{label}</Label>
      {children}
    </div>
  );
}
