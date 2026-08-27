import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button, Card, DemoBanner, Input, Label } from "@/components/ui";
import { fmtNum, fmtPct } from "@/lib/utils";

export default function Settings() {
  const [overview, setOverview] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => api.overview().then(setOverview).catch((e) => toast.error(e.message));
  useEffect(() => { refresh(); }, []);

  async function onUpload(file: File) {
    setBusy(true);
    try {
      await api.upload(file);
      toast.success("Dataset uploaded and model retrained.");
      await refresh();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function retrainDemo() {
    setBusy(true);
    try {
      await api.train(true);
      toast.success("Demo model retrained.");
      await refresh();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  }

  const h = overview?.dataset_health;

  return (
    <div>
      <h1 className="text-3xl font-semibold">Settings</h1>
      <p className="mt-2 text-slate-400">Upload a transaction CSV, inspect dataset health, and retrain. No payment credentials are collected.</p>
      <DemoBanner show={overview?.is_demo} />

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Card>
          <h2 className="text-lg font-semibold">Data Upload</h2>
          <p className="mt-1 text-sm text-slate-400">CSV or XLSX, max 10 MB. Required features plus <code>is_fraud</code>.</p>
          <Label>File</Label>
          <Input
            type="file"
            accept=".csv,.xlsx"
            disabled={busy}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUpload(file);
            }}
          />
          <p className="mt-3 text-xs text-slate-500">
            Columns: amount, hour, customer_age, account_age_days, num_transactions, previous_chargebacks,
            previous_returns, device_type, payment_method, location, transaction_frequency, failed_payment_attempts,
            is_new_device, days_since_last_transaction, avg_transaction_amount, merchant_category, is_fraud.
          </p>
          <Button className="mt-4" variant="ghost" disabled={busy} onClick={retrainDemo}>
            Reload DEMO DATASET
          </Button>
        </Card>
        <Card>
          <h2 className="text-lg font-semibold">Dataset Health</h2>
          {h ? (
            <div className="mt-4 grid grid-cols-2 gap-4">
              <Health label="Rows" value={fmtNum(h.rows)} />
              <Health label="Columns" value={fmtNum(h.columns)} />
              <Health label="Missing values" value={fmtNum(h.missing_values)} />
              <Health label="Fraud cases" value={fmtNum(h.fraud_cases)} />
              <Health label="Fraud rate" value={fmtPct(h.fraud_rate)} />
              <Health label="Source" value={overview.dataset_name} />
            </div>
          ) : (
            <p className="mt-3 text-slate-500">No dataset loaded.</p>
          )}
        </Card>
      </div>
    </div>
  );
}

function Health({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white/5 p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 font-mono">{value}</div>
    </div>
  );
}
