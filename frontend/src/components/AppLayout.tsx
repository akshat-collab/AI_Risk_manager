import { NavLink, Outlet, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Gauge,
  LayoutDashboard,
  Search,
  Settings,
  Shield,
  Table2,
  Wallet,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { fmtTime } from "@/lib/utils";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/analyzer", label: "Transaction Analyzer", icon: Search },
  { to: "/transactions", label: "Transactions", icon: Table2 },
  { to: "/intelligence", label: "Risk Intelligence", icon: BarChart3 },
  { to: "/performance", label: "Model Performance", icon: Gauge },
  { to: "/cost", label: "Cost Analysis", icon: Wallet },
  { to: "/alerts", label: "Alerts", icon: AlertTriangle },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function AppLayout() {
  const location = useLocation();
  const [health, setHealth] = useState<{ model_online: boolean; last_trained: string | null; is_demo: boolean } | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ model_online: false, last_trained: null, is_demo: true }));
  }, [location.pathname]);

  return (
    <div className="bg-app min-h-screen">
      <div className="bg-grid min-h-screen">
        <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 flex-col border-r border-white/10 bg-black/40 px-5 py-6 backdrop-blur-xl lg:flex">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-400/15 text-cyan-300 ring-1 ring-cyan-400/30">
              <Shield size={22} />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-wide">AI Risk Manager</div>
              <div className="text-[11px] text-slate-400">Defense-first intelligence</div>
            </div>
          </div>
          <nav className="flex-1 space-y-1">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                    isActive
                      ? "bg-cyan-400/10 text-cyan-200 ring-1 ring-cyan-400/20"
                      : "text-slate-400 hover:bg-white/5 hover:text-slate-100"
                  }`
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
              <span>Model Status</span>
              <span className="flex items-center gap-1.5 text-emerald-300">
                <span className={`h-2 w-2 rounded-full ${health?.model_online ? "bg-emerald-400 shadow-[0_0_10px_#34d399]" : "bg-rose-400"}`} />
                {health?.model_online ? "ONLINE" : "OFFLINE"}
              </span>
            </div>
            <div className="text-[11px] text-slate-500">Last Updated</div>
            <div className="font-mono text-xs text-slate-300">{fmtTime(health?.last_trained)}</div>
          </div>
        </aside>

        <div className="lg:pl-72">
          <header className="sticky top-0 z-20 flex items-center justify-between border-b border-white/10 bg-black/30 px-4 py-3 backdrop-blur-xl lg:px-8">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Activity size={14} className="text-cyan-300" />
              <span>DEFENSE-FIRST • AI RISK INTELLIGENCE</span>
            </div>
            <div className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[11px] font-semibold tracking-wide text-cyan-200">
              Stop revenue leakage before it happens.
            </div>
          </header>
          <main className="px-4 py-6 lg:px-8">
            <motion.div key={location.pathname} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
              <Outlet />
            </motion.div>
          </main>
        </div>
      </div>
    </div>
  );
}
