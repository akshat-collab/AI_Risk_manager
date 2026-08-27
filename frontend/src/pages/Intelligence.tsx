import { useEffect, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { Card, DemoBanner } from "@/components/ui";

export default function Intelligence() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api.trends().then(setData);
  }, []);
  if (!data) return <Card>Loading risk intelligence…</Card>;

  return (
    <div>
      <h1 className="text-3xl font-semibold">Risk Intelligence</h1>
      <p className="mt-2 text-slate-400">Trends computed from the currently loaded dataset — not fabricated dashboard numbers.</p>
      <DemoBanner show={data.is_demo} />

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <ChartCard title="Fraud-risk trend over time">
          <Line data={data.daily} x="date" y="avg_risk" />
        </ChartCard>
        <ChartCard title="High-risk transaction volume">
          <Line data={data.daily} x="date" y="high_risk" />
        </ChartCard>
        <ChartCard title="Average transaction value">
          <Line data={data.daily} x="date" y="avg_amount" />
        </ChartCard>
        <ChartCard title="Chargeback trend">
          <Line data={data.daily} x="date" y="chargebacks" />
        </ChartCard>
        <ChartCard title="Return-risk trend">
          <Line data={data.daily} x="date" y="returns" />
        </ChartCard>
        <ChartCard title="Risk by payment method">
          <Bars data={data.by_payment_method} />
        </ChartCard>
        <ChartCard title="Risk by device type">
          <Bars data={data.by_device_type} />
        </ChartCard>
        <ChartCard title="Risk by geographic region">
          <Bars data={data.by_location} />
        </ChartCard>
      </div>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <h2 className="mb-4 text-lg font-semibold">{title}</h2>
      <div className="h-64">{children}</div>
    </Card>
  );
}

function Line({ data, x, y }: { data: any[]; x: string; y: string }) {
  return (
    <ResponsiveContainer>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgba(148,163,184,0.08)" />
        <XAxis dataKey={x} hide />
        <YAxis stroke="#64748b" fontSize={11} />
        <Tooltip contentStyle={{ background: "#0c1222", border: "1px solid #1f2937" }} />
        <Area type="monotone" dataKey={y} stroke="#22d3ee" fill="url(#fill)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function Bars({ data }: { data: { name: string; avg_risk: number }[] }) {
  return (
    <ResponsiveContainer>
      <BarChart data={data}>
        <CartesianGrid stroke="rgba(148,163,184,0.08)" />
        <XAxis dataKey="name" stroke="#64748b" fontSize={11} interval={0} angle={-20} height={50} />
        <YAxis stroke="#64748b" fontSize={11} />
        <Tooltip contentStyle={{ background: "#0c1222", border: "1px solid #1f2937" }} />
        <Bar dataKey="avg_risk" fill="#34d399" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
