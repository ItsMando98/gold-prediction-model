// Server-side base URL (inside the Docker network, "http://api:8000").
const API_URL = process.env.API_URL ?? "http://localhost:8000";

export interface PredictionDriver {
  name: string;
  category: string;
  contribution: number;
  description: string | null;
}

export interface Prediction {
  id: string;
  created_at: string;
  target_time: string;
  horizon: string;
  symbol: string;
  regime: string;
  probabilities: Record<string, number>;
  risk_score: number;
  bias: string;
  confidence: number;
  confirmations: string[];
  contradictions: string[];
  key_levels: { support?: number[]; resistance?: number[] };
  event_risks: unknown[];
  invalidation: string[];
  model_versions: Record<string, unknown>;
  narrative: string | null;
  ml_score: number | null;
  drivers: PredictionDriver[];
}

export interface ProviderHealth {
  source: string;
  symbol: string | null;
  checked_at: string;
  status: string;
  latency_ms: number | null;
  message: string | null;
}

async function apiFetch<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export function getCurrentPrediction(symbol = "XAUUSD") {
  return apiFetch<Prediction>(`/prediction/current?symbol=${symbol}`);
}

export function getDataHealth() {
  return apiFetch<ProviderHealth[]>("/data/health");
}
