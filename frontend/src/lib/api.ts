export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type Overview = {
  model_online: boolean;
  is_demo: boolean;
  dataset_name: string;
  last_trained: string | null;
  best_model: string | null;
  threshold: number;
  dataset_health: {
    rows: number;
    columns: number;
    missing_values: number;
    fraud_cases: number | null;
    fraud_rate: number | null;
  };
  kpis: {
    transactions_analyzed: number;
    high_risk_transactions: number;
    fraud_prevented: number;
    estimated_loss_avoided: number;
    average_risk_score: number;
    model_precision: number | null;
    model_recall: number | null;
    trends: Record<string, number>;
  };
  risk_distribution: {
    n: number;
    items: { level: RiskLevel; count: number; pct: number }[];
  };
  split_counts: Record<string, number | string>;
  hero: MetricsBlock | null;
  spike: Spike | null;
};

export type MetricsBlock = {
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number | null;
  pr_auc: number | null;
  specificity: number;
  false_positive_rate: number;
  false_negative_rate: number;
  confusion_matrix: {
    true_negative: number;
    false_positive: number;
    false_negative: number;
    true_positive: number;
  };
  threshold: number;
};

export type Spike = {
  detected: boolean;
  title: string;
  detection_time: string;
  window_date: string;
  current_risk_rate: number;
  expected_baseline: number;
  deviation_z: number;
  affected_transactions: number;
  high_risk_in_window: number;
  method: string;
};

export type Prediction = {
  risk_score: number;
  probability: number;
  risk_level: RiskLevel;
  recommendation: string;
  threshold: number;
  predicted_fraud: boolean;
  model: string;
  is_demo: boolean;
  explanations: {
    feature: string;
    title: string;
    detail: string;
    contribution: number;
    direction: string;
    value: string | number | null;
    disclaimer: string;
  }[];
  disclaimer: string;
  transaction?: Record<string, unknown>;
};

export type TransactionRow = {
  transaction_id: string;
  timestamp: string | null;
  amount: number;
  risk_score: number;
  risk_level: RiskLevel;
  key_signal: string;
  status: string;
  payment_method: string;
  device_type: string;
  location: string;
};

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const loc = Array.isArray((item as { loc?: unknown }).loc)
            ? (item as { loc: unknown[] }).loc.filter((part) => part !== "body").join(".")
            : "";
          const msg = (item as { msg?: string }).msg || JSON.stringify(item);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(item);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return String(detail ?? "Request failed");
}

async function parseError(res: Response) {
  try {
    const data = await res.json();
    if (data?.detail !== undefined) return formatDetail(data.detail);
    return JSON.stringify(data);
  } catch {
    return res.statusText;
  }
}

export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function postFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(path, { method: "POST", body: form });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export const api = {
  health: () => getJson<{ model_online: boolean; last_trained: string | null; is_demo: boolean; best_model: string | null }>("/api/health"),
  overview: () => getJson<Overview>("/api/overview"),
  options: () => getJson<{ device_types: string[]; payment_methods: string[]; locations: string[]; merchant_categories: string[] }>("/api/options"),
  predict: (body: unknown) => postJson<Prediction>("/api/analyze", body),
  transactions: (params: string) =>
    getJson<{ total: number; page: number; page_size: number; items: TransactionRow[]; is_demo: boolean }>(`/api/transactions?${params}`),
  transaction: (id: string) => getJson<Prediction>(`/api/transactions/${id}`),
  performance: () => getJson<any>("/api/model-performance"),
  trends: () => getJson<any>("/api/trends"),
  alerts: () => getJson<{ is_demo: boolean; spike: Spike | null; items: any[] }>("/api/alerts"),
  cost: (q: string) => getJson<any>(`/api/cost-analysis?${q}`),
  train: (useDemo = false) => postJson<any>("/api/train", { use_demo: useDemo }),
  upload: (file: File) => postFile<any>("/api/upload", file),
};
