import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import Dashboard from "@/pages/Dashboard";
import Analyzer from "@/pages/Analyzer";
import Transactions from "@/pages/Transactions";
import Intelligence from "@/pages/Intelligence";
import Performance from "@/pages/Performance";
import CostAnalysis from "@/pages/CostAnalysis";
import Alerts from "@/pages/Alerts";
import Settings from "@/pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/analyzer" element={<Analyzer />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/intelligence" element={<Intelligence />} />
        <Route path="/performance" element={<Performance />} />
        <Route path="/cost" element={<CostAnalysis />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
