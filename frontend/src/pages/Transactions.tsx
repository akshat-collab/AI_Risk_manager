import { useEffect, useState } from "react";
import { api, type Prediction, type TransactionRow } from "@/lib/api";
import { Button, Card, DemoBanner, Input, RiskBadge, Select } from "@/components/ui";
import { fmtMoney, fmtNum } from "@/lib/utils";

export default function Transactions() {
  const [q, setQ] = useState("");
  const [risk, setRisk] = useState("ALL");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("timestamp");
  const [order, setOrder] = useState("desc");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<TransactionRow[]>([]);
  const [demo, setDemo] = useState(false);
  const [selected, setSelected] = useState<Prediction | null>(null);

  useEffect(() => {
    const params = new URLSearchParams({ q, risk_level: risk, page: String(page), page_size: "12", sort, order });
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    api.transactions(params.toString()).then((res) => {
      setItems(res.items);
      setTotal(res.total);
      setDemo(res.is_demo);
    });
  }, [q, risk, page, sort, order, dateFrom, dateTo]);

  const pages = Math.max(1, Math.ceil(total / 12));

  return (
    <div>
      <h1 className="text-3xl font-semibold">Transactions</h1>
      <p className="mt-2 text-slate-400">Search, filter, and inspect scored activity. Click a row for an explanation panel.</p>
      <DemoBanner show={demo} />

      <Card className="mt-5">
        <div className="mb-4 grid gap-3 md:grid-cols-4">
          <Input placeholder="Search ID, signal, location" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} />
          <Select value={risk} onChange={(e) => { setPage(1); setRisk(e.target.value); }}>
            {["ALL", "LOW", "MEDIUM", "HIGH", "CRITICAL"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </Select>
          <Input type="date" title="From date" value={dateFrom} onChange={(e) => { setPage(1); setDateFrom(e.target.value); }} />
          <Input type="date" title="To date" value={dateTo} onChange={(e) => { setPage(1); setDateTo(e.target.value); }} />
          <Select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="timestamp">Sort: time</option>
            <option value="amount">Sort: amount</option>
            <option value="risk_score">Sort: risk</option>
          </Select>
          <Select value={order} onChange={(e) => setOrder(e.target.value)}>
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </Select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="pb-3">Transaction ID</th>
                <th className="pb-3 text-right">Amount</th>
                <th className="pb-3 text-right">Risk Score</th>
                <th className="pb-3">Risk Level</th>
                <th className="pb-3">Key Signal</th>
                <th className="pb-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-slate-500">No transactions match these filters.</td>
                </tr>
              )}
              {items.map((row) => (
                <tr
                  key={row.transaction_id}
                  className="cursor-pointer border-t border-white/5 hover:bg-white/5"
                  onClick={() => api.transaction(row.transaction_id).then(setSelected)}
                >
                  <td className="py-3 font-mono text-cyan-200">{row.transaction_id}</td>
                  <td className="py-3 text-right">{fmtMoney(row.amount)}</td>
                  <td className="py-3 text-right font-mono">{row.risk_score.toFixed(1)}</td>
                  <td className="py-3"><RiskBadge level={row.risk_level} /></td>
                  <td className="py-3 text-slate-300">{row.key_signal}</td>
                  <td className="py-3 text-slate-400">{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex items-center justify-between text-sm text-slate-400">
          <span>{fmtNum(total)} results</span>
          <div className="flex gap-2">
            <Button variant="ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</Button>
            <span className="px-2 py-2">Page {page} / {pages}</span>
            <Button variant="ghost" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        </div>
      </Card>

      {selected && (
        <Card className="mt-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">Risk detail</h2>
              <p className="text-sm text-slate-400">{String(selected.transaction?.transaction_id || "")}</p>
            </div>
            <RiskBadge level={selected.risk_level} />
          </div>
          <p className="mt-3 text-slate-300">{selected.recommendation}</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {selected.explanations.map((ex) => (
              <div key={ex.feature} className="rounded-xl border border-white/10 bg-white/5 p-3">
                <div className="font-medium">{ex.title}</div>
                <div className="text-sm text-slate-400">{ex.detail}</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
